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
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 200,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Service Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Start Time"),
            "fieldname": "start_time",
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "label": _("End Time"),
            "fieldname": "end_time",
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "label": _("Actual Duration (hrs)"),
            "fieldname": "actual_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 140,
        },
        {
            "label": _("Estimated Time (hrs)"),
            "fieldname": "estimated_time",
            "fieldtype": "Float",
            "precision": 2,
            "width": 140,
        },
        {
            "label": _("Variance (hrs)"),
            "fieldname": "variance_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 120,
        },
        {
            "label": _("Total Duration (raw)"),
            "fieldname": "total_duration",
            "fieldtype": "Duration",
            "width": 130,
        },
        {
            "label": _("Job Card"),
            "fieldname": "job_order",
            "fieldtype": "Link",
            "options": "Job Order",
            "width": 130,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Job Type"),
            "fieldname": "job_type",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150,
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
    ]


def get_data(filters=None):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        """
        SELECT
            si.employee,
            emp.employee_name,
            si.item_code,
            si.description,
            si.start_time,
            si.end_time,
            si.total_duration,
            ROUND(IFNULL(si.total_duration, 0) / 3600, 2)          AS actual_hours,
            IFNULL(itm.custom_estimate_time, 0)                      AS estimated_time,
            ROUND(
                IFNULL(itm.custom_estimate_time, 0)
                - IFNULL(si.total_duration, 0) / 3600
            , 2)                                                     AS variance_hours,
            jo.name                                                  AS job_order,
            jo.expected_completion_date                              AS posting_date,
            jo.job_type,
            jo.status,
            jo.customer,
            jo.vehicle,
            jo.make,
            jo.model
        FROM
            `tabJob Order` jo
        INNER JOIN
            `tabService Item` si ON si.parent = jo.name
        LEFT JOIN
            `tabEmployee` emp ON emp.name = si.employee
        LEFT JOIN
            `tabItem` itm ON itm.name = si.item_code
        WHERE
            si.employee IS NOT NULL
            AND si.employee != ''
            {conditions}
        ORDER BY
            si.employee,
            jo.expected_completion_date DESC,
            jo.name,
            si.idx
        """.format(
            conditions=conditions
        ),
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

    if filters.get("employee"):
        conditions.append("AND si.employee = %(employee)s")

    if filters.get("job_type"):
        conditions.append("AND jo.job_type = %(job_type)s")

    if filters.get("status"):
        conditions.append("AND jo.status = %(status)s")

    return " ".join(conditions)