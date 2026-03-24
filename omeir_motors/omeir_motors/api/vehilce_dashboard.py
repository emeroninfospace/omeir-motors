import frappe
from frappe.utils import add_months, today, date_diff, nowdate, getdate
from frappe import _

@frappe.whitelist()
def get_dashboard_stats(from_date=None, to_date=None):
    filters = "vl.docstatus = 1"
    if from_date:
        filters += f" AND vl.date >= '{from_date}'"
    if to_date:
        filters += f" AND vl.date <= '{to_date}'"
    
    vehicles_with_service = frappe.db.sql(f"""
        SELECT DISTINCT vl.license_plate
        FROM `tabVehicle Log` vl
        WHERE {filters}
    """, as_dict=True)
    
    total_vehicles = len(vehicles_with_service)
    
    overdue = 0
    due_soon = 0
    healthy = 0
    upcoming_services = []
    
    for v in vehicles_with_service:
        vehicle = v.license_plate
        status, next_service = get_vehicle_status(vehicle, from_date, to_date)
        
        if status == "Overdue":
            overdue += 1
        elif status == "Due Soon":
            due_soon += 1
        elif status == "OK":
            healthy += 1
            
        if next_service:
            upcoming_services.append(next_service)
    
    monthly_expense = frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(vl.date, '%Y-%m') as month,
            SUM(vsi.amount) as total_expense
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {filters} AND vsi.amount > 0
        GROUP BY DATE_FORMAT(vl.date, '%Y-%m')
        ORDER BY month DESC
        LIMIT 6
    """, as_dict=True)
    
    top_services = frappe.db.sql(f"""
        SELECT 
            vsi.item_name as service_item,
            COUNT(*) as service_count,
            SUM(vsi.amount) as total_expense
        FROM `tabVehicle Service Item` vsi
        WHERE vsi.parenttype = 'Vehicle Log'
        GROUP BY vsi.item_name
        ORDER BY service_count DESC
        LIMIT 5
    """, as_dict=True)
    
    return {
        "stats": {
            "total_vehicles": total_vehicles,
            "overdue": overdue,
            "due_soon": due_soon,
            "healthy": healthy
        },
        "monthly_expense": monthly_expense,
        "top_services": top_services,
        "upcoming_services": sorted(upcoming_services, key=lambda x: x.get('days_remaining', 999))[:5]
    }

@frappe.whitelist()
def get_vehicle_status(license_plate, from_date=None, to_date=None):
    filters = f"vl.license_plate = '{license_plate}' AND vl.docstatus = 1"
    if from_date:
        filters += f" AND vl.date >= '{from_date}'"
    if to_date:
        filters += f" AND vl.date <= '{to_date}'"
    
    last_service = frappe.db.sql(f"""
        SELECT 
            vl.date,
            vl.odometer,
            vsi.item_name as service_item,
            vsi.quantity,
            vsi.amount
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {filters}
        ORDER BY vl.date DESC, vl.odometer DESC
        LIMIT 1
    """, as_dict=True)
    
    if not last_service:
        return "No Service", None
    
    last = last_service[0]
    
    current_odometer = frappe.db.get_value("Vehicle", license_plate, "last_odometer") or 0
    
    next_date = add_months(last.date, 1)
    days_remaining = date_diff(next_date, nowdate())
    
    if days_remaining <= 0:
        status = "Overdue"
    elif days_remaining <= 7:
        status = "Due Soon"
    else:
        status = "OK"
    
    next_service = {
        "vehicle": license_plate,
        "next_date": next_date,
        "days_remaining": days_remaining,
        "service_item": last.service_item,
        "status": status
    }
    
    return status, next_service

@frappe.whitelist()
def get_service_history(license_plate=None, limit=10, from_date=None, to_date=None):
    conditions = "vl.docstatus = 1"
    if license_plate:
        conditions += f" AND vl.license_plate = '{license_plate}'"
    if from_date:
        conditions += f" AND vl.date >= '{from_date}'"
    if to_date:
        conditions += f" AND vl.date <= '{to_date}'"
    
    history = frappe.db.sql(f"""
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
        LIMIT %s
    """, (limit), as_dict=True)
    
    return history

@frappe.whitelist()
def get_expense_chart_data(from_date=None, to_date=None):
    conditions = "vl.docstatus = 1 AND vsi.amount > 0"
    if from_date:
        conditions += f" AND vl.date >= '{from_date}'"
    if to_date:
        conditions += f" AND vl.date <= '{to_date}'"
    
    monthly = frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(vl.date, '%Y-%m') as month,
            SUM(vsi.amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions}
        GROUP BY DATE_FORMAT(vl.date, '%Y-%m')
        ORDER BY month
        LIMIT 12
    """, as_dict=True)
    
    by_vehicle = frappe.db.sql(f"""
        SELECT 
            vl.license_plate as vehicle,
            SUM(vsi.amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service Item` vsi ON vsi.parent = vl.name
        WHERE {conditions}
        GROUP BY vl.license_plate
        ORDER BY total DESC
        LIMIT 5
    """, as_dict=True)
    
    return {
        "monthly": monthly,
        "by_vehicle": by_vehicle
    }