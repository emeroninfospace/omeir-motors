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

    total_job_cards = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabJob Order`
        WHERE docstatus = 1
    """)[0][0]

    pending_job_cards = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabJob Order`
        WHERE docstatus = 1 AND status = 'Pending'
    """)[0][0]

    draft_job_cards = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabJob Order`
        WHERE docstatus = 0
    """)[0][0]

    multi_invoice_jobs = frappe.db.sql("""
        SELECT
            jo.name,
            jo.customer,
            jo.make,
            jo.model,
            jo.status,
            jo.expected_completion_date,
            COUNT(sinv.name) AS invoice_count
        FROM `tabJob Order` jo
        INNER JOIN `tabSales Invoice` sinv
            ON sinv.custom_job_order = jo.name
            AND sinv.docstatus = 1
        WHERE jo.docstatus = 1
        GROUP BY jo.name
        HAVING COUNT(sinv.name) > 1
        ORDER BY invoice_count DESC
    """, as_dict=True)

    gate_pass_jobs = frappe.db.sql("""
        SELECT
            jo.name,
            jo.customer,
            jo.make,
            jo.model,
            jo.status,
            jo.expected_completion_date,
            jo.vehicle
        FROM `tabJob Order` jo
        WHERE jo.docstatus = 1
          AND jo.gate_pass_issued = 1
        ORDER BY jo.expected_completion_date DESC
    """, as_dict=True)

    completed_job_cards = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabJob Order`
        WHERE docstatus = 1 AND status = 'Completed'
    """)[0][0]

    return {
        "jobs": jobs,
        "technicians": unique_technicians,
        "total_job_cards": total_job_cards,
        "pending_job_cards": pending_job_cards,
        "draft_job_cards": draft_job_cards,
        "completed_job_cards": completed_job_cards,
        "multi_invoice_jobs": multi_invoice_jobs,
        "multi_invoice_count": len(multi_invoice_jobs),
        "gate_pass_jobs": gate_pass_jobs,
        "gate_pass_count": len(gate_pass_jobs),
    }