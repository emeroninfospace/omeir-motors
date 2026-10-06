# Copyright (c) 2026, Balaji B and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days


class SubcontractWorkOrder(Document):
    def on_submit(self):
        self.db_set("status", "To Receive and Bill")

    def before_submit(self):
        if not self.supplier:
            frappe.throw("Please Select Supplier")



@frappe.whitelist()
def create_subcontract_invoice(docname):
    doc = frappe.get_doc("Subcontract Work Order", docname)
    
    existing = frappe.db.exists("Subcontract Invoice", {
        "subcontract_work_order": doc.name,
        "docstatus": ["!=", 2] 
    })

    if existing:
        frappe.throw(f"Subcontract Invoice already exists: {existing}")

    invoice = frappe.new_doc("Subcontract Invoice")
    invoice.supplier = doc.supplier
    invoice.company = doc.company
    # invoice.bill_of_quantity = doc.bill_of_quantity
    invoice.transaction_date = doc.transaction_date
    invoice.project = doc.project
    invoice.cost_center = doc.cost_center
    invoice.supplier_invoice_no = doc.supplier_invoice_no
    invoice.supplier_invoice_date = doc.supplier_invoice_date
    invoice.subcontract_work_order = doc.name
    invoice.custom_supplier_details = doc.custom_supplier_details

    total_qty = 0
    total_amt = 0

    for item in doc.items:
        row = invoice.append("items", {})
        row.item_code = item.item_code
        row.item_name = item.item_name
        row.description = item.description
        row.quantity = item.quantity
        row.rate = item.rate
        row.amount = item.amount
        row.job_order = item.job_order

        total_qty += item.quantity or 0
        total_amt += item.amount or 0

    invoice.total_quantity = total_qty
    invoice.total_amount = total_amt

    for tax in doc.purchase_taxes_and_charges:
        tax_row = invoice.append("purchase_taxes_and_charges", {})
        tax_row.charge_type = tax.charge_type
        tax_row.account_head = tax.account_head
        tax_row.description = tax.description
        tax_row.rate = tax.rate
        tax_row.tax_amount = tax.tax_amount
        tax_row.total = tax.total
        tax_row.add_deduct_tax = tax.add_deduct_tax

    invoice.taxes_and_charges_added = doc.taxes_and_charges_added
    invoice.taxes_and_charges_deducted = doc.taxes_and_charges_deducted
    invoice.total_taxes_and_charges = doc.total_taxes_and_charges
    invoice.grand_total = doc.grand_total

    invoice.insert(ignore_permissions=True)
    doc.db_set("status", "To Bill")
    return invoice.name


@frappe.whitelist()
def create_purchase_order(docname):
    doc = frappe.get_doc("Subcontract Work Order", docname)

    po = frappe.new_doc("Purchase Order")
    po.supplier = doc.supplier
    po.company = doc.company
    po.transaction_date = getdate(doc.transaction_date)

    for item in doc.items:
        row = po.append("items", {})
        row.item_code = item.item_code
        row.qty = item.quantity
        row.rate = item.rate
        row.amount = item.amount

        row.schedule_date = getdate(doc.transaction_date)  # or any logic

    po.insert(ignore_permissions=True)

    return po.name


@frappe.whitelist()
def make_subcontract_work_order_from_job_order(source_name, target_doc=None, args=None):
    from frappe.model.mapper import get_mapped_doc

    def set_missing_values(source, target):
        target.company = source.company

    def update_item(source, target, source_parent):
        target.item_code = source.item_code
        target.item_name = source.item_name
        target.uom = source.uom
        target.description = source.description
        target.quantity = source.quantity
        target.rate = source.rate
        target.amount = source.amount

    doc = get_mapped_doc(
        "Job Order",
        source_name,
        {
            "Job Order": {
                "doctype": "Subcontract Work Order",
                "validation": {
                    "docstatus": ["in", [0,1]]
                }
            },
            "Sublet Items": {
                "doctype": "Subcontract Work Item",
                "postprocess": update_item
            }
        },
        target_doc,
        set_missing_values
    )

    return doc