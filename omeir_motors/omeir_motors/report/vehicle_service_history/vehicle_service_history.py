# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 150},
        {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 150},
        {"label": "Odometer", "fieldname": "odometer", "fieldtype": "Int", "width": 120},
        {"label": "Service Item", "fieldname": "service_item", "fieldtype": "Data", "width": 180},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 120},
        {"label": "Frequency", "fieldname": "frequency", "fieldtype": "Data", "width": 120},
        {"label": "Expense", "fieldname": "expense_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Next Service Date", "fieldname": "next_service_date", "fieldtype": "Date", "width": 140},
        {
			"label": "Next Service KM",
			"fieldname": "next_service_km",
			"fieldtype": "Int",
			"width": 140
		}
    ]


def get_data(filters):
    conditions = ""

    if filters.get("vehicle"):
        conditions += " AND vl.license_plate = %(vehicle)s"

    if filters.get("from_date"):
        conditions += " AND vl.date >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND vl.date <= %(to_date)s"

    data = frappe.db.sql(f"""
        SELECT
            vl.date,
            vl.license_plate as vehicle,
            vl.odometer,
            vs.service_item,
            vs.type,
            vs.frequency,
            vs.custom_service_interval_km,
            vs.expense_amount
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE vl.docstatus = 1
        {conditions}
        ORDER BY vl.date DESC
    """, filters, as_dict=1)

    for row in data:
        next_date, next_km = get_next_service_details(row)
        row["next_service_date"] = next_date
        row["next_service_km"] = next_km

    return data


def get_next_service_details(row):
    from frappe.utils import add_months

    next_date = None
    next_km = None

    if row["frequency"] == "Monthly":
        next_date = add_months(row["date"], 1)

    elif row["frequency"] == "Quarterly":
        next_date = add_months(row["date"], 3)

    elif row["frequency"] == "Half Yearly":
        next_date = add_months(row["date"], 6)

    elif row["frequency"] == "Yearly":
        next_date = add_months(row["date"], 12)

    elif row["frequency"] == "Mileage":
        if row.get("custom_service_interval_km"):
            next_km = row["odometer"] + row["custom_service_interval_km"]

    return next_date, next_km