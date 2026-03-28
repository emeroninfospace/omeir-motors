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

        "internal_links": {
            "Vehicle Log": [],
            "Technician Allocation": [],
            "Sales Invoice": [],
            "Quotation": [],          
            "Material Request": []    
        },

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
            }
        ]
    }