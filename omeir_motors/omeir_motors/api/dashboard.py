import frappe


@frappe.whitelist()
def get_workshop_dashboard_data():
    jobs = frappe.db.sql("""
        SELECT
            jo.name,
            jo.customer,
            jo.vehicle,
            jo.make,
            jo.model,
            jo.job_type,
            jo.status,
            jo.expected_completion_date,
            GREATEST(DATEDIFF(CURDATE(), jo.expected_completion_date), 0) AS age_days,
            IFNULL(jo.total_amount_service, 0) AS labour,
            IFNULL(jo.total_amount, 0)         AS parts,
            IFNULL(jo.total_am_sub, 0)         AS sublet
        FROM `tabJob Order` jo
        WHERE jo.status = 'Pending'
          AND jo.docstatus = 1
        ORDER BY age_days DESC
    """, as_dict=True)

    technicians = frappe.db.sql("""
        SELECT
            emp.name          AS employee,
            emp.employee_name,
            CASE
                WHEN active_si.employee IS NOT NULL THEN 'Active'
                ELSE 'Idle'
            END AS status,
            CASE
                WHEN active_si.employee IS NOT NULL
                    THEN CONCAT(active_si.parent, ' — ', IFNULL(active_si.description, ''))
                ELSE NULL
            END AS current_job,
            active_si.parent  AS assigned_job
        FROM `tabEmployee` emp
        LEFT JOIN (
            SELECT si.employee, si.parent, si.description
            FROM `tabService Item` si
            WHERE si.start_time IS NOT NULL
              AND si.end_time   IS NULL
              AND si.employee   IS NOT NULL
            GROUP BY si.employee
        ) active_si ON active_si.employee = emp.name
        WHERE emp.status = 'Active'
          AND emp.department IN ('SERVICE OPERATIONS - BOMC', 'SERVICE - BOMC')
        ORDER BY status ASC, emp.employee_name ASC
    """, as_dict=True)

    seen = set()
    unique_technicians = []
    for t in technicians:
        if t.employee not in seen:
            seen.add(t.employee)
            unique_technicians.append(t)

    return {
        "jobs": jobs,
        "technicians": unique_technicians,
    }