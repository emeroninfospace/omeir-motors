from frappe import _


def get_data(data=None):
    return {
        "fieldname": "voucher_no",
        "transactions": [
            {
                "label": _("Accounting"),
                "items": ["GL Entry"]
            }
        ]
    }