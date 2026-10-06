// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Vat Tax Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "transaction_type",
            label: __("Transaction Type"),
            fieldtype: "Select",
            options: [
                "All",
                "Sales Invoice",
                "Purchase Invoice",
                "Subcontract Invoice",
                "Expense Entry",
                "Journal Entry",
            ],
            default: "All",
            reqd: 1,
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            depends_on:
                "eval:['All', 'Sales Invoice', 'Journal Entry'].includes(doc.transaction_type)",
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
            depends_on:
                "eval:['All', 'Purchase Invoice', 'Subcontract Invoice', 'Expense Entry', 'Journal Entry'].includes(doc.transaction_type)",
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "vat_type" && data) {
            const color = data.vat_type === "Output" ? "var(--red-600)" : "var(--green-600)";
            value = `<span style="color:${color};font-weight:600">${value}</span>`;
        }
        return value;
    },
};