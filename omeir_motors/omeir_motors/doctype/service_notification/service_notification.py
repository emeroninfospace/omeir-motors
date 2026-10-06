# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate


class ServiceNotification(Document):
    def before_save(self):
        self.validate_rate_amount()

    def validate_rate_amount(self):
        items = self.get("service_items") or []

        self.total_amount = sum(flt(item.amount) for item in items)
        self.total_quantity = sum(flt(item.quantity) for item in items)

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):

    def set_missing_values(source, target):
        target.customer = source.customer
        target.posting_date = source.posting_date or nowdate()
        target.due_date = source.posting_date or nowdate()
        target.update_stock = 0
        target.ignore_pricing_rule = 1
        target.company = source.company or frappe.defaults.get_user_default("Company")

        target.custom_service_notification = source.name


        target.selling_price_list =  ""

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source_doc, target_doc, source_parent):
        target_doc.rate = flt(source_doc.rate)
        target_doc.price_list_rate = flt(source_doc.rate)
        target_doc.qty = flt(source_doc.quantity)
        target_doc.amount = flt(source_doc.amount)

    doc = get_mapped_doc(
        "Service Notification",
        source_name,
        {
            "Service Notification": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "name": "custom_service_notification",
                    "customer": "customer",
                    "posting_date": "posting_date",
                    "company": "company",
                }
            },
            "Service Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "description": "description",
                    "quantity": "qty",
                    "uom": "uom",
                    "rate": "rate",
                    "in_time": "custom_in_date",
                    "out_time": "custom_out_date",
                },
                "postprocess": update_item,
            }
        },
        target_doc,
        set_missing_values
    )

    return doc