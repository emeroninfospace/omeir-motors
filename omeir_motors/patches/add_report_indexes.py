import frappe

# Custom fields on standard doctypes that reports and dashboards join or filter on
INDEXED_CUSTOM_FIELDS = {
    "Sales Invoice": ["custom_job_order"],
}


def execute():
    for doctype, fieldnames in INDEXED_CUSTOM_FIELDS.items():
        for fieldname in fieldnames:
            custom_field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname})
            if custom_field:
                frappe.db.set_value("Custom Field", custom_field, "search_index", 1, update_modified=False)

        frappe.clear_cache(doctype=doctype)
        frappe.db.updatedb(doctype)
