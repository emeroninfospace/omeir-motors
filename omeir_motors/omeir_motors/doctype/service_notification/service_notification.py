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

        cost_center = frappe.db.get_value("Company", source.company, "cost_center")
        target.set("items", [])

        item_list = []
        for item in source.get("service_items") or []:
            item_list.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "uom": item.uom,
                "quantity": item.quantity,
                "rate": item.rate,
            })

        for item_data in item_list:
            item_code = item_data["item_code"]

            income_account = frappe.db.get_value(
                "Item Default",
                {"parent": item_code, "company": source.company},
                "income_account"
            ) or frappe.db.get_value("Company", source.company, "default_income_account")

            if not item_data.get("item_name"):
                item_details = frappe.db.get_value(
                    "Item",
                    item_code,
                    ["item_name", "stock_uom", "description"],
                    as_dict=1
                )
                if item_details:
                    item_data["item_name"] = item_details.item_name
                    item_data["description"] = item_details.description
                    item_data["uom"] = item_data.get("uom") or item_details.stock_uom

            target.append("items", {
                "item_code": item_code,
                "item_name": item_data.get("item_name"),
                "description": item_data.get("description"),
                "uom": item_data.get("uom"),
                "stock_uom": item_data.get("uom"),
                "conversion_factor": 1,
                "qty": item_data.get("quantity", 0),
                "price_list_rate": item_data.get("rate", 0),
                "rate": item_data.get("rate", 0),
                "amount": flt(item_data.get("quantity", 0)) * flt(item_data.get("rate", 0)),
                "income_account": income_account,
                "cost_center": cost_center
            })

        if target.get("items"):
            total_qty = sum([flt(item.qty) for item in target.items])
            target.total_qty = total_qty
            target.total = source.total_amount or 0
            target.grand_total = source.total_amount or 0
            target.outstanding_amount = source.total_amount or 0

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
                    "transaction_date": "posting_date",
                    "total_amount": "total",
                    "currency": "currency",
                    "conversion_rate": "conversion_rate"
                }
            }
        },
        target_doc,
        set_missing_values
    )

    return doc
