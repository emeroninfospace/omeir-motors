CREATE_FIELDS={
        "Quotation": [
            {
                "fieldname": "custom_job_order",
                "label": "Job Order",
                "fieldtype": "Link",
                "options": "Job Order",
                "read_only":1,
                "insert_after": "valid_till"
            },
        ],
        "Sales Invoice": [
            {
                "fieldname": "custom_job_order",
                "label": "Job Order",
                "fieldtype": "Link",
                "options": "Job Order",
                "read_only":1,
                "insert_after": "due_date"
            },
        ],
        "Item": [
            {
                "fieldname": "custom_section_break_onqti",
                "label": "",
                "fieldtype": "Section Break",
                "insert_after": "image"
            },
            {
                "fieldname": "custom_bus_details",
                "label": "Bus Details",
                "fieldtype": "Table",
                "options": "Bus Details",
                "insert_after": "custom_section_break_onqti"
            },
            {
                "fieldname": "custom_location",
                "label": "Location",
                "fieldtype": "Data",
                "insert_after": "stock_uom",
                "in_list_view":1
            }
        ],
}