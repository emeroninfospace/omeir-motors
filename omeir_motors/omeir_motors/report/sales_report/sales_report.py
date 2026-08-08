# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Owner"),
			"fieldname": "owner",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Job Card"),
			"fieldname": "custom_job_order",
			"fieldtype": "Link",
			"options": "Job Order",
			"width": 140,
		},
		{
			"label": _("Service Description"),
			"fieldname": "custom_service_description",
			"fieldtype": "Small Text",
			"width": 150,
		},
		{
			"label": _("Vehicle No"),
			"fieldname": "custom_vehicle_no",
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 120,
		},
		{
			"label": _("Vehicle In"),
			"fieldname": "custom_vehicle_in",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": _("Vehicle Out"),
			"fieldname": "custom_vehicle_out",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": _("Model"),
			"fieldname": "custom_model",
			"fieldtype": "Link",
			"options": "Model",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Outstanding Amount"),
			"fieldname": "outstanding_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Payment Type"),
			"fieldname": "custom_payment_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Invoice Type"),
			"fieldname": "custom_invoice_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Service Notification"),
			"fieldname": "custom_service_notification",
			"fieldtype": "Link",
			"options": "Service Notification",
			"width": 160,
		},
		{
			"label": _("Payment Due Date"),
			"fieldname": "due_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": _("Job Card Item Total Amount"),
			"fieldname": "job_card_item_total",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Sublet Total Amount"),
			"fieldname": "sublet_total",
			"fieldtype": "Currency",
			"width": 180,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			si.name,
			si.posting_date,
			si.customer_name,
			si.status,
			u.full_name AS owner,
			si.custom_job_order,
			si.custom_service_description,
			si.custom_vehicle_no,
			si.custom_vehicle_in,
			si.custom_vehicle_out,
			si.custom_model,
			si.grand_total,
			si.outstanding_amount,
			si.custom_payment_type,
			si.custom_invoice_type,
			si.custom_service_notification,
			si.due_date,
			jo.total_amount AS job_card_item_total,
			jo.total_am_sub AS sublet_total
		FROM
			`tabSales Invoice` si
		LEFT JOIN
			`tabUser` u ON u.name = si.owner
		LEFT JOIN
			`tabJob Order` jo ON jo.name = si.custom_job_order
		WHERE
			si.docstatus = 1
			{conditions}
		ORDER BY
			si.posting_date DESC, si.name DESC
	""".format(
			conditions=conditions
		),
		filters,
		as_dict=1,
	)

	return data


def get_conditions(filters):
	conditions = ""

	
	if filters.get("customer"):
		conditions += " AND si.customer = %(customer)s"

	if filters.get("status"):
		conditions += " AND si.status = %(status)s"

	if filters.get("from_date"):
		conditions += " AND si.posting_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND si.posting_date <= %(to_date)s"

	if filters.get("due_date"):
		conditions += " AND si.due_date = %(due_date)s"

	if filters.get("custom_payment_type"):
		conditions += " AND si.custom_payment_type = %(custom_payment_type)s"

	if filters.get("custom_invoice_type"):
		conditions += " AND si.custom_invoice_type = %(custom_invoice_type)s"

	if filters.get("custom_service_notification"):
		conditions += " AND si.custom_service_notification = %(custom_service_notification)s"

	return conditions