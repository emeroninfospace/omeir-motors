from frappe import _

def get_data():
    return {
        "fieldname": "subcontract_work_order",
        "transactions": [
            {
                "label": "Invoices",
                "items": ["Subcontract Invoice"]
            }
        ]
    }