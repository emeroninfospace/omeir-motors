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
            "label": _("Job Order"),
            "fieldname": "job_order",
            "fieldtype": "Link",
            "options": "Job Order",
            "width": 140,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("Job Type"),
            "fieldname": "job_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180,
        },
        {
            "label": _("Vehicle"),
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "options": "Vehicle",
            "width": 120,
        },
        {
            "label": _("Make"),
            "fieldname": "make",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Model"),
            "fieldname": "model",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Year"),
            "fieldname": "year",
            "fieldtype": "Data",
            "width": 70,
        },
        {
            "label": _("Chassis No"),
            "fieldname": "chasis_number",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Service Description"),
            "fieldname": "complaint_details",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Service Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Service Amount"),
            "fieldname": "total_amount_service",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Parts Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Sublet Amount"),
            "fieldname": "total_am_sub",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 160,
        },
        {
            "label": _("Invoice Type"),
            "fieldname": "custom_invoice_type",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Payment Type"),
            "fieldname": "custom_payment_type",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Invoice Status"),
            "fieldname": "invoice_status",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Invoice Amount"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Outstanding Amount"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(filters=None):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        """
        SELECT
            jo.name                         AS job_order,
            jo.status,
            jo.job_type,
            jo.expected_completion_date     AS posting_date,
            jo.customer,
            jo.vehicle,
            jo.make,
            jo.model,
            jo.year,
            jo.chasis_number,
            jo.complaint_details,
            jo.total_amount_service,
            jo.total_amount,
            jo.total_am_sub,
            si.employee,
            emp.employee_name,
            si.item_code,
            sinv.name                       AS sales_invoice,
            sinv.custom_invoice_type,
            sinv.custom_payment_type,
            sinv.status                     AS invoice_status,
            sinv.grand_total,
            sinv.outstanding_amount
        FROM
            `tabJob Order` jo
        LEFT JOIN
            `tabService Item` si ON si.parent = jo.name
        LEFT JOIN
            `tabEmployee` emp ON emp.name = si.employee
        LEFT JOIN
            `tabSales Invoice` sinv ON sinv.custom_job_order = jo.name
                AND sinv.docstatus = 1
        WHERE
            jo.docstatus != 2
            {conditions}
        ORDER BY
            jo.expected_completion_date DESC,
            jo.name,
            si.idx
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    return data


def get_conditions(filters):
    if not filters:
        return ""

    conditions = []

    if filters.get("from_date"):
        conditions.append("AND jo.expected_completion_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("AND jo.expected_completion_date <= %(to_date)s")

    if filters.get("customer"):
        conditions.append("AND jo.customer = %(customer)s")

    if filters.get("vehicle"):
        conditions.append("AND jo.vehicle = %(vehicle)s")

    if filters.get("job_type"):
        conditions.append("AND jo.job_type = %(job_type)s")

    if filters.get("status"):
        conditions.append("AND jo.status = %(status)s")

    if filters.get("employee"):
        conditions.append("AND si.employee = %(employee)s")

    if filters.get("make"):
        conditions.append("AND jo.make = %(make)s")

    return " ".join(conditions)