from frappe import _


def get_data(data=None):
    return {
        "fieldname": "cheque_no",
        "transactions": [
            {
                "label": _("Accounting"),
                "items": ["Journal Entry"]
            }
        ]
    }