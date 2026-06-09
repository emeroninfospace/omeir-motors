from frappe import _

def get_data(data=None):
    return {
        "fieldname": "custom_service_notification",

        "non_standard_fieldnames": {
            "Sales Invoice": "custom_service_notification"
        },

        "internal_links": {},

        "transactions": [
           
            {
                "label": _("Sales"),
                "items": ["Sales Invoice"]
            }
        ]
    }



