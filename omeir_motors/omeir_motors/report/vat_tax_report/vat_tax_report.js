// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt


frappe.query_reports["Vat Tax Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "transaction_type",
            "label": __("Transaction Type"),
            "fieldtype": "Select",
            "options": ["All", "Sales Invoice", "Purchase Invoice", "Expense Claim", "Subcontract Invoice", "Expense Entry"],
            "default": "All",
            "reqd": 1
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "depends_on": "eval:doc.transaction_type == 'Sales Invoice' || doc.transaction_type == 'All' || doc.transaction_type == 'Expense Entry'"
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "depends_on": "eval:doc.transaction_type == 'Purchase Invoice' || doc.transaction_type == 'All' || doc.transaction_type == 'Expense Entry' || doc.transaction_type == 'Subcontract Invoice'"
        },
    ]
};