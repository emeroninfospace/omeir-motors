import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SALES_FIELD = "custom_job_order_sublet_row"


def ensure_fields():
	create_custom_fields(
		{
			"Sales Invoice Item": [
				{
					"fieldname": SALES_FIELD,
					"label": "Job Order Sublet Row",
					"fieldtype": "Data",
					"insert_after": "item_code",
					"no_copy": 1,
					"description": "Exact Sublet Items row ID. Filled by Job Order mapping; used for subcontract profitability.",
				}
			],
		}
	)
	frappe.clear_cache(doctype="Sales Invoice Item")
