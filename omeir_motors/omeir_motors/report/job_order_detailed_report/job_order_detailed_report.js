// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Job Order Detailed Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle",
		},
		{
			fieldname: "job_type",
			label: __("Job Type"),
			fieldtype: "Select",
			options: "\nNew\nRoutine Service\nWarranty\nInsurance Claim\nOther",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nPending\nCompleted",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "make",
			label: __("Make"),
			fieldtype: "Data",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data) {
			var color = {
				Completed: "green",
				Pending: "orange",
				Draft: "gray",
			}[data.status] || "gray";
			value = `<span style="color:var(--${color}-500);font-weight:600">${data.status || ""}</span>`;
		}

		if (column.fieldname === "invoice_status" && data && data.invoice_status) {
			var icolor = {
				Paid: "green",
				Unpaid: "orange",
				Overdue: "red",
				"Return": "gray",
			}[data.invoice_status] || "gray";
			value = `<span style="color:var(--${icolor}-500);font-weight:600">${data.invoice_status}</span>`;
		}

		if (column.fieldname === "outstanding_amount" && data && data.outstanding_amount > 0) {
			value = `<span style="color:var(--red-500);font-weight:600">${value}</span>`;
		}

		return value;
	},
};