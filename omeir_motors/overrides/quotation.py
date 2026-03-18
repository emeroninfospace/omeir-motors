import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

@frappe.whitelist()
def create_job_order(source_name, target_doc=None):    
    def set_missing_values(source, target):
        target.job_type = "New"  
        target.priority = "Medium"  
        target.expected_completion_date = None
        target.posting_date = source.transaction_date or nowdate()
        
        if target.get("job_order_items"):
            total_qty = sum([flt(item.quantity) for item in target.job_order_items])
            target.total_quantity = total_qty
            target.total_amount = source.total or 0

    def update_item(source, target, source_parent):
        target.item_code = source.item_code
        target.item_name = source.item_name
        target.description = source.description
        target.quantity = source.qty
        target.rate = source.rate
        target.amount = source.amount
        target.uom = source.uom

    doc = get_mapped_doc(
        "Quotation",
        source_name,
        {
            "Quotation": {
                "doctype": "Job Order",
                "field_map": {
                    "customer": "customer",
                    "customer_name": "customer_name",
                    "transaction_date": "posting_date",
                    "party_name": "customer",
                    "currency": "currency",
                    "conversion_rate": "conversion_rate",
                    "selling_price_list": "selling_price_list",
                    "price_list_currency": "price_list_currency",
                    "plc_conversion_rate": "plc_conversion_rate"
                },
                "validation": {
                    "docstatus": ["=", 1]  
                }
            },
            "Quotation Item": {
                "doctype": "Job Order Item",
                "field_map": {
                    "name": "quotation_item",
                    "parent": "quotation",
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "description": "description",
                    "qty": "quantity",
                    "rate": "rate",
                    "amount": "amount",
                    "uom": "uom"
                },
                "postprocess": update_item
            }
        },
        target_doc,
        set_missing_values
    )

    return doc