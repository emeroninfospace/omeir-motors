from collections import defaultdict

import frappe
from frappe.utils import add_months, cint, date_diff, nowdate


def _vehicle_log_conditions(license_plate=None, from_date=None, to_date=None):
    conditions = ["vl.docstatus = 1"]
    values = {}
    if license_plate:
        conditions.append("vl.license_plate = %(license_plate)s")
        values["license_plate"] = license_plate
    if from_date:
        conditions.append("vl.date >= %(from_date)s")
        values["from_date"] = from_date
    if to_date:
        conditions.append("vl.date <= %(to_date)s")
        values["to_date"] = to_date
    return " AND ".join(conditions), values


@frappe.whitelist()
def get_vehicle_service_dashboard_data():
    """Everything the Vehicle Service Dashboard needs in one request: vehicles, their submitted
    Vehicle Logs (newest first) and the service items of those logs, keyed by log name."""
    vehicles = frappe.get_list(
        "Vehicle",
        fields=["name", "license_plate", "make", "model", "last_odometer", "fuel_type"],
        limit_page_length=0,
    )
    if not vehicles:
        return {"vehicles": [], "logs": [], "service_items": {}}

    logs = frappe.get_list(
        "Vehicle Log",
        fields=["name", "license_plate", "date", "odometer", "custom_job_order", "custom_custom_model"],
        filters={"docstatus": 1, "license_plate": ["in", [v.name for v in vehicles]]},
        order_by="date desc",
        limit_page_length=0,
    )

    service_items = defaultdict(list)
    if logs:
        for row in frappe.get_all(
            "Service Item",
            filters={"parenttype": "Vehicle Log", "parent": ["in", [log.name for log in logs]]},
            fields=["*"],
            order_by="parent, idx",
        ):
            service_items[row.parent].append(row)

    return {"vehicles": vehicles, "logs": logs, "service_items": service_items}


@frappe.whitelist()
def get_dashboard_stats(from_date=None, to_date=None):
    conditions, values = _vehicle_log_conditions(from_date=from_date, to_date=to_date)

    # Latest log per vehicle in one pass instead of one query per vehicle
    latest_logs = {}
    for log in frappe.db.sql(
        f"""
        SELECT vl.name, vl.license_plate, vl.date, vl.odometer
        FROM `tabVehicle Log` vl
        WHERE {conditions}
        ORDER BY vl.date DESC, vl.odometer DESC
        """,
        values,
        as_dict=True,
    ):
        latest_logs.setdefault(log.license_plate, log)

    first_service_item = _get_first_service_items([log.name for log in latest_logs.values()])

    counts = {"Overdue": 0, "Due Soon": 0, "OK": 0}
    upcoming_services = []
    for license_plate, log in latest_logs.items():
        status, next_service = _get_status_from_log(license_plate, log, first_service_item.get(log.name))
        if status in counts:
            counts[status] += 1
        upcoming_services.append(next_service)

    monthly_expense = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(vl.date, '%%Y-%%m') as month,
            SUM(vsi.amount) as total_expense
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions} AND vsi.amount > 0
        GROUP BY DATE_FORMAT(vl.date, '%%Y-%%m')
        ORDER BY month DESC
        LIMIT 6
        """,
        values,
        as_dict=True,
    )

    top_services = frappe.db.sql(
        """
        SELECT
            vsi.item_name as service_item,
            COUNT(*) as service_count,
            SUM(vsi.amount) as total_expense
        FROM `tabVehicle Service Item` vsi
        WHERE vsi.parenttype = 'Vehicle Log'
        GROUP BY vsi.item_name
        ORDER BY service_count DESC
        LIMIT 5
        """,
        as_dict=True,
    )

    return {
        "stats": {
            "total_vehicles": len(latest_logs),
            "overdue": counts["Overdue"],
            "due_soon": counts["Due Soon"],
            "healthy": counts["OK"],
        },
        "monthly_expense": monthly_expense,
        "top_services": top_services,
        "upcoming_services": sorted(upcoming_services, key=lambda x: x.get("days_remaining", 999))[:5],
    }


def _get_first_service_items(log_names):
    if not log_names:
        return {}

    first = {}
    for row in frappe.db.sql(
        """
        SELECT parent, item_name
        FROM `tabVehicle Service Item`
        WHERE parent IN %(logs)s
        ORDER BY parent, idx
        """,
        {"logs": log_names},
        as_dict=True,
    ):
        first.setdefault(row.parent, row.item_name)
    return first


def _get_status_from_log(license_plate, log, service_item):
    next_date = add_months(log.date, 1)
    days_remaining = date_diff(next_date, nowdate())

    if days_remaining <= 0:
        status = "Overdue"
    elif days_remaining <= 7:
        status = "Due Soon"
    else:
        status = "OK"

    return status, {
        "vehicle": license_plate,
        "next_date": next_date,
        "days_remaining": days_remaining,
        "service_item": service_item,
        "status": status,
    }


@frappe.whitelist()
def get_vehicle_status(license_plate, from_date=None, to_date=None):
    conditions, values = _vehicle_log_conditions(license_plate, from_date, to_date)

    last_log = frappe.db.sql(
        f"""
        SELECT vl.name, vl.date, vl.odometer
        FROM `tabVehicle Log` vl
        WHERE {conditions}
        ORDER BY vl.date DESC, vl.odometer DESC
        LIMIT 1
        """,
        values,
        as_dict=True,
    )

    if not last_log:
        return "No Service", None

    log = last_log[0]
    return _get_status_from_log(license_plate, log, _get_first_service_items([log.name]).get(log.name))


@frappe.whitelist()
def get_service_history(license_plate=None, limit=10, from_date=None, to_date=None):
    conditions, values = _vehicle_log_conditions(license_plate, from_date, to_date)
    values["limit"] = cint(limit) or 10

    return frappe.db.sql(
        f"""
        SELECT
            vl.date,
            vl.license_plate as vehicle,
            vl.odometer,
            vl.custom_custom_model,
            vsi.item_name as service_item,
            vsi.quantity,
            vsi.rate,
            vsi.amount,
            DATE_ADD(vl.date, INTERVAL 1 MONTH) as next_service_date
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions}
        ORDER BY vl.date DESC
        LIMIT %(limit)s
        """,
        values,
        as_dict=True,
    )


@frappe.whitelist()
def get_expense_chart_data(from_date=None, to_date=None):
    conditions, values = _vehicle_log_conditions(from_date=from_date, to_date=to_date)
    conditions += " AND vsi.amount > 0"

    monthly = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(vl.date, '%%Y-%%m') as month,
            SUM(vsi.amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions}
        GROUP BY DATE_FORMAT(vl.date, '%%Y-%%m')
        ORDER BY month
        LIMIT 12
        """,
        values,
        as_dict=True,
    )

    by_vehicle = frappe.db.sql(
        f"""
        SELECT
            vl.license_plate as vehicle,
            SUM(vsi.amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions}
        GROUP BY vl.license_plate
        ORDER BY total DESC
        LIMIT 5
        """,
        values,
        as_dict=True,
    )

    return {"monthly": monthly, "by_vehicle": by_vehicle}
