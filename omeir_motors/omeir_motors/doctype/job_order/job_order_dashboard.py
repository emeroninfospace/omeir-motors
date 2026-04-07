from frappe import _

def get_data(data=None):
    return {
        "fieldname": "job_order",

        "non_standard_fieldnames": {
            "Vehicle Log": "custom_job_order",
            "Technician Allocation": "job_order",
            "Sales Invoice": "custom_job_order",
            "Quotation": "custom_job_order",
            "Material Request": "custom_job_order"
        },

        "internal_links": {},

        "transactions": [
            {
                "label": _("Vehicle"),
                "items": ["Vehicle Log"]
            },
            {
                "label": _("Sales"),
                "items": ["Sales Invoice", "Quotation"]
            },
            {
                "label": _("Operations"),
                "items": ["Technician Allocation"]
            },
            {
                "label": _("Stock"),
                "items": ["Material Request"]
            },
            {
                "label": _("Subcontract"),
                "items": ["Subcontract Work Order"]
            }
        ]
    }



import frappe

def get_dashboard_data(data):
    job_order = data.get("name")

    work_orders = frappe.db.sql("""
        SELECT COUNT(DISTINCT parent)
        FROM `tabSubcontract Work Item`
        WHERE job_order = %s
    """, job_order)[0][0]
    return {
        "transactions": {
            "Subcontract Work Order": work_orders
        }
    }