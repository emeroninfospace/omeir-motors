# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

class JobOrder(Document):
	pass



import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):    
    def set_missing_values(source, target):
        target.customer = source.customer
        target.posting_date = nowdate()
        target.set_posting_time = 1
        
        if source.company:
            target.company = source.company
            
        if target.get("items"):
            total_qty = sum([flt(item.qty) for item in target.items])
            target.total_qty = total_qty
            target.total = source.total_amount or 0
            target.grand_total = source.total_amount or 0
            target.outstanding_amount = source.total_amount or 0

    def update_item(source, target, source_parent):
        target.item_code = source.item_code
        target.item_name = source.item_name
        target.description = source.description
        target.qty = source.quantity
        target.rate = source.rate
        target.amount = source.amount
        target.uom = source.uom
        
        if not target.income_account:
            income_account = frappe.db.get_value("Item Default", 
                {"parent": source.item_code, "company": source_parent.company}, 
                "income_account")
            if not income_account:
                income_account = frappe.db.get_value("Company", 
                    source_parent.company, "default_income_account")
            target.income_account = income_account
      

    doc = get_mapped_doc(
        "Job Order",
        source_name,
        {
            "Job Order": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "customer": "customer",
                    "name": "custom_job_order", 
                    "posting_date": "posting_date",
                    "transaction_date": "posting_date",
                    "total_amount": "total",
                    "currency": "currency",
                    "conversion_rate": "conversion_rate"
                }
            },
            "Job Order Item": {   
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "uom": "uom",
                    "description": "description",
                    "quantity": "qty",   
                    "rate": "rate",
                    "amount": "amount"
                },
                "postprocess": update_item
            }
        },
        target_doc,
        set_missing_values
    )

    return doc