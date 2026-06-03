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
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier_name",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		}
		
	]


def get_data(filters):
	conditions_expense = get_expense_conditions(filters)
	conditions_pi = get_pi_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			'Expense' as voucher_type,
			eei.parent as voucher_no,
			ee.posting_date,
			eei.supplier_name,
			eei.total_amount as amount,
			CASE ee.docstatus WHEN 0 THEN 'Draft' WHEN 1 THEN 'Submitted' WHEN 2 THEN 'Cancelled' END as docstatus,
			ee.status,
			'Expense Entry Item' as remarks
		FROM
			`tabExpense Entry` ee
		INNER JOIN
			`tabExpense Entry Item` eei ON eei.parent = ee.name
		WHERE
			ee.docstatus = 1
			{conditions_expense}

		UNION ALL

		SELECT
			'Purchase' as voucher_type,
			pi.name as voucher_no,
			pi.posting_date,
			pi.supplier as supplier_name,
			pi.grand_total as amount,
			CASE pi.docstatus WHEN 0 THEN 'Draft' WHEN 1 THEN 'Submitted' WHEN 2 THEN 'Cancelled' END as docstatus,
			pi.status,
			'Purchase Invoice' as remarks
		FROM
			`tabPurchase Invoice` pi
		WHERE
			pi.docstatus = 1
			{conditions_pi}

		ORDER BY
			posting_date DESC, voucher_no ASC
	""".format(
			conditions_expense=conditions_expense,
			conditions_pi=conditions_pi
		),
		filters,
		as_dict=1,
	)

	return data


def get_expense_conditions(filters):
	conditions = ""

	if filters.get("expense_entry"):
		conditions += " AND eei.parent = %(expense_entry)s"

	if filters.get("supplier_name"):
		conditions += " AND eei.supplier_name = %(supplier_name)s"

	if filters.get("from_date"):
		conditions += " AND ee.posting_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND ee.posting_date <= %(to_date)s"

	return conditions


def get_pi_conditions(filters):
	conditions = ""

	if filters.get("supplier_name"):
		conditions += " AND pi.supplier = %(supplier_name)s"

	if filters.get("from_date"):
		conditions += " AND pi.posting_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND pi.posting_date <= %(to_date)s"

	return conditions
