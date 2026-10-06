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
            "fieldname": "name",
            "label": _("Expense Entry"),
            "fieldtype": "Link",
            "options": "Expense Entry",
            "width": 180
        },
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "account_from",
            "label": _("Account From"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "fieldname": "account",
            "label": _("Account To"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "fieldname": "supplier_name",
            "label": _("Supplier Name"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "narration",
            "label": _("Narration"),
            "fieldtype": "Data",
            "width": 240
        },
        {
            "fieldname": "amount",
            "label": _("Amount"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "vat_percentage",
            "label": _("VAT %"),
            "fieldtype": "Percent",
            "width": 80
        },
        {
            "fieldname": "vat_amount",
            "label": _("VAT Amount"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "total_amount",
            "label": _("Total Amount"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "spend_by_name",
            "label": _("Spend By"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "journal_entry",
            "label": _("Journal Entry"),
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 180
        }
    ]


def get_data(filters=None):
    if not filters:
        filters = {}

    conditions = ["ee.docstatus = 1"]
    values = {}

    if filters.get("company"):
        conditions.append("ee.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("from_date"):
        conditions.append("ee.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("ee.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("status"):
        conditions.append("ee.status = %(status)s")
        values["status"] = filters["status"]

    if filters.get("supplier_name"):
        conditions.append("eei.supplier_name LIKE %(supplier_name)s")
        values["supplier_name"] = f"%{filters['supplier_name']}%"

    if filters.get("spend_by"):
        conditions.append("eei.spend_by = %(spend_by)s")
        values["spend_by"] = filters["spend_by"]

    if filters.get("account_from"):
        conditions.append("eei.account_from = %(account_from)s")
        values["account_from"] = filters["account_from"]

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            ee.name,
            ee.posting_date,
            ee.status,
            ee.journal_entry,
            eei.account_from,
            eei.account,
            eei.supplier_name,
            eei.voucher_no,
            eei.narration,
            eei.amount,
            eei.vat_percentage,
            eei.vat_amount,
            eei.total_amount,
            eei.spend_by,
            emp.employee_name as spend_by_name
        FROM `tabExpense Entry` ee
        JOIN `tabExpense Entry Item` eei ON eei.parent = ee.name
        LEFT JOIN `tabEmployee` emp ON emp.name = eei.spend_by
        WHERE {where_clause}
        ORDER BY ee.posting_date DESC, ee.name DESC
    """, values, as_dict=True)

    return data
