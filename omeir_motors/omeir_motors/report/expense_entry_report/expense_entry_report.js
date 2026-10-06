// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Expense Entry Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nPaid\nUnpaid"
        },
        {
            fieldname: "supplier_name",
            label: __("Supplier"),
            fieldtype: "Data"
        },
        {
            fieldname: "spend_by",
            label: __("Spend By"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "account_from",
            label: __("Account From"),
            fieldtype: "Link",
            options: "Account",
            get_query: function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company"),
                        is_group: 0
                    }
                };
            }
        }
    ]
};