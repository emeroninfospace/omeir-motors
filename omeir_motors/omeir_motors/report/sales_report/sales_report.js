// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Report"] = {
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
			fieldname: "due_date",
			label: __("Payment Due Date"),
			fieldtype: "Date",
		},
		
		{
			fieldname: "custom_payment_type",
			label: __("Payment Type"),
			fieldtype: "Select",
			options: "\nCREDIT\nCASH\nWARRANTY\nINSURANCE",
		},
		{
			fieldname: "custom_invoice_type",
			label: __("Invoice Type"),
			fieldtype: "Select",
			options: "\nJob Card Invoice\nNotification Invoice\nCounter Invoice",
		},
		{
			fieldname: "custom_service_notification",
			label: __("Service Notification"),
			fieldtype: "Link",
			options: "Service Notification",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nCancelled",
		}
	],
};
