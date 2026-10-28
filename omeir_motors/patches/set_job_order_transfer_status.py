import frappe


def execute():
    for name in frappe.get_all("Job Order", filters={"docstatus": 1}, pluck="name"):
        frappe.get_doc("Job Order", name).update_transfer_status()
