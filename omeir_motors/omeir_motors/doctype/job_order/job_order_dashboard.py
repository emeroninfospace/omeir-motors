from frappe import _

def get_data():
    return {
        "fieldname": "custom_job_order", 
        "non_standard_fieldnames": {
            "Quotation": "custom_job_order"
        },
        "transactions": [
            {
                "label": _("Related"),
                "items": ["Quotation"]
            }
        ]
    }