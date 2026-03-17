# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class JobOrder(Document):
	pass



@frappe.whitelist()
def make_quotation(source_name, target_doc=None):

    def set_missing_values(source, target):
        target.quotation_to = "Customer"
        target.party_name = source.customer

    doc = get_mapped_doc(
        "Job Order",
        source_name,
        {
            "Job Order": {
                "doctype": "Quotation",
                "field_map": {
                    "customer": "party_name",
                    "name": "custom_job_order"
                }
            },
            "Job Order Item": {   
                "doctype": "Quotation Item",
                "field_map": {
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "uom": "uom",
                    "description": "description",
                    "quantity": "qty",   
                    "rate": "rate",
                    "amount": "amount"
                }
            }
        },
        target_doc,
        set_missing_values
    )

    return doc