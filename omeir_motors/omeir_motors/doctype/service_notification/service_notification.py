# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate



class ServiceNotification(Document):
	def validate_rate_amount(self):
		if self.service_items:
			self.total_amount = sum(item.amount for item in self.service_items)
			self.total_quantity = sum(item.quantity for item in self.service_items)


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):

    def set_missing_values(source, target):
        target.customer = source.customer
        target.posting_date = source.posting_date
        target.set_posting_time = 1
        target.update_stock = 0
        target.ignore_pricing_rule = 1
        target.selling_price_list = ""

        if source.company:
            target.company = source.company

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source_doc, target_doc, source_parent):
        """Set price_list_rate from Service Notification Item rate"""
        target_doc.rate = source_doc.rate
        target_doc.price_list_rate = source_doc.rate  # ✅ set service item rate as price list rate

    doc = get_mapped_doc(
        "Service Notification",
        source_name,
        {
            "Service Notification": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "customer": "customer",
                    "name": "custom_service_notification",
                    "posting_date": "posting_date",
                    "total_amount": "total",
                }
            },
            "Service Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "description": "description",
                    "qty": "qty",
                    "uom": "uom",
                    "rate": "rate",
                },
                "postprocess": update_item,  # ✅ override price_list_rate after mapping
            }
        },
        target_doc,
        set_missing_values
    )

    return doc
