import frappe
from frappe.utils import add_months, today, date_diff, nowdate
from frappe import _

@frappe.whitelist()
def get_dashboard_stats():
    
    vehicles_with_service = frappe.db.sql("""
        SELECT DISTINCT vl.license_plate
        FROM `tabVehicle Log` vl
        WHERE vl.docstatus = 1
    """, as_dict=True)
    
    total_vehicles = len(vehicles_with_service)
    
    overdue = 0
    due_soon = 0
    healthy = 0
    upcoming_services = []
    
    for v in vehicles_with_service:
        vehicle = v.license_plate
        status, next_service = get_vehicle_status(vehicle)
        
        if status == "Overdue":
            overdue += 1
        elif status == "Due Soon":
            due_soon += 1
        else:
            healthy += 1
            
        if next_service:
            upcoming_services.append(next_service)
    
    monthly_expense = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(vl.date, '%Y-%m') as month,
            SUM(vs.expense_amount) as total_expense
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE vl.docstatus = 1 AND vs.expense_amount > 0
        GROUP BY DATE_FORMAT(vl.date, '%Y-%m')
        ORDER BY month DESC
        LIMIT 6
    """, as_dict=True)
    
    top_services = frappe.db.sql("""
        SELECT 
            vs.service_item,
            COUNT(*) as service_count,
            SUM(vs.expense_amount) as total_expense
        FROM `tabVehicle Service` vs
        WHERE vs.parenttype = 'Vehicle Log'
        GROUP BY vs.service_item
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
def get_vehicle_status(license_plate):
    
    last_service = frappe.db.sql("""
        SELECT 
            vl.date,
            vl.odometer,
            vs.service_item,
            vs.type,
            vs.frequency,
            vs.custom_service_interval_km
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE vl.license_plate = %s AND vl.docstatus = 1
        ORDER BY vl.date DESC, vl.odometer DESC
        LIMIT 1
    """, license_plate, as_dict=True)
    
    if not last_service:
        return "No Service", None
    
    last = last_service[0]
    
    next_date = None
    next_km = None
    status = "Healthy"
    
    if last.frequency == "Monthly":
        next_date = add_months(last.date, 1)
    elif last.frequency == "Quarterly":
        next_date = add_months(last.date, 3)
    elif last.frequency == "Half Yearly":
        next_date = add_months(last.date, 6)
    elif last.frequency == "Yearly":
        next_date = add_months(last.date, 12)
    elif last.frequency == "Mileage" and last.custom_service_interval_km:
        next_km = last.odometer + last.custom_service_interval_km
    
    current_odometer = frappe.db.get_value("Vehicle", license_plate, "last_odometer") or 0
    
    days_remaining = 999
    km_remaining = 99999
    
    if next_date:
        days_remaining = date_diff(next_date, nowdate())
        if days_remaining <= 0:
            status = "Overdue"
        elif days_remaining <= 7:
            status = "Due Soon"
    
    if next_km:
        km_remaining = next_km - current_odometer
        if km_remaining <= 0:
            status = "Overdue"
        elif km_remaining <= 500:
            status = "Due Soon"
    
    next_service = {
        "vehicle": license_plate,
        "next_date": next_date,
        "next_km": next_km,
        "days_remaining": days_remaining,
        "km_remaining": km_remaining,
        "service_item": last.service_item,
        "status": status
    }
    
    return status, next_service

@frappe.whitelist()
def get_service_history(license_plate=None, limit=10):
    
    conditions = "vl.docstatus = 1"
    if license_plate:
        conditions += f" AND vl.license_plate = '{license_plate}'"
    
    history = frappe.db.sql(f"""
        SELECT 
            vl.date,
            vl.license_plate as vehicle,
            vl.odometer,
            vs.service_item,
            vs.type,
            vs.frequency,
            vs.expense_amount,
            CASE 
                WHEN vs.frequency = 'Monthly' THEN DATE_ADD(vl.date, INTERVAL 1 MONTH)
                WHEN vs.frequency = 'Quarterly' THEN DATE_ADD(vl.date, INTERVAL 3 MONTH)
                WHEN vs.frequency = 'Half Yearly' THEN DATE_ADD(vl.date, INTERVAL 6 MONTH)
                WHEN vs.frequency = 'Yearly' THEN DATE_ADD(vl.date, INTERVAL 12 MONTH)
                ELSE NULL
            END as next_service_date,
            CASE 
                WHEN vs.frequency = 'Mileage' AND vs.custom_service_interval_km 
                THEN vl.odometer + vs.custom_service_interval_km
                ELSE NULL
            END as next_service_km
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE {conditions}
        ORDER BY vl.date DESC
        LIMIT %s
    """, (limit), as_dict=True)
    
    return history

@frappe.whitelist()
def get_expense_chart_data():
    
    monthly = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(vl.date, '%Y-%m') as month,
            SUM(vs.expense_amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE vl.docstatus = 1 AND vs.expense_amount > 0
        GROUP BY DATE_FORMAT(vl.date, '%Y-%m')
        ORDER BY month
        LIMIT 12
    """, as_dict=True)
    
    by_vehicle = frappe.db.sql("""
        SELECT 
            vl.license_plate as vehicle,
            SUM(vs.expense_amount) as total
        FROM `tabVehicle Log` vl
        LEFT JOIN `tabVehicle Service` vs ON vs.parent = vl.name
        WHERE vl.docstatus = 1 AND vs.expense_amount > 0
        GROUP BY vl.license_plate
        ORDER BY total DESC
        LIMIT 5
    """, as_dict=True)
    
    return {
        "monthly": monthly,
        "by_vehicle": by_vehicle
    }