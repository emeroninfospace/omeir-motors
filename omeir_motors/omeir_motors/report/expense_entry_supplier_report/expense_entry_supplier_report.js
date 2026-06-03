// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Expense Entry Supplier Report"] = {
	filters: [
		{
			fieldname: "expense_entry",
			label: __("Expense Entry"),
			fieldtype: "Link",
			options: "Expense Entry",
		},
		{
			fieldname: "supplier_name",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],
};

