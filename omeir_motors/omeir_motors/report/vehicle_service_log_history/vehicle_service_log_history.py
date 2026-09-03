# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Odometer (km/mi)"),
            "fieldname": "odometer",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Job Card No."),
            "fieldname": "job_card",
            "fieldtype": "Link",
            "options": "Job Order",
            "width": 140,
        },
        {
            "label": _("Service Type"),
            "fieldname": "service_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Work Description"),
            "fieldname": "work_description",
            "fieldtype": "Data",
            "width": 280,
        },
        {
            "label": _("Parts Replaced"),
            "fieldname": "parts_replaced",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": _("Technician"),
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Labor Charge"),
            "fieldname": "labor_charge",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": _("Parts Cost"),
            "fieldname": "parts_cost",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": _("Total Cost"),
            "fieldname": "total_cost",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
        },
    ]


def get_conditions(filters):
    conditions = ["jo.docstatus < 2"]

    if filters.get("vehicle"):
        conditions.append("jo.vehicle = %(vehicle)s")

    if filters.get("from_date"):
        conditions.append("jo.expected_completion_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("jo.expected_completion_date <= %(to_date)s")

    if filters.get("job_type"):
        conditions.append("jo.job_type = %(job_type)s")

    if filters.get("status"):
        conditions.append("jo.status = %(status)s")

    return " AND ".join(conditions)


def get_data(filters):
    if not filters.get("vehicle"):
        frappe.throw(_("Please select a Vehicle to view its service log history."))

    conditions = get_conditions(filters)

    rows = frappe.db.sql(
        """
        SELECT
            jo.name                                           AS job_card,
            jo.expected_completion_date                       AS posting_date,
            jo.odometer_value_last                            AS odometer,
            jo.job_type                                       AS service_type,
            jo.complaint_details                              AS work_description,
            jo.status,
            IFNULL(jo.total_amount_service, 0)                AS labor_charge,
            IFNULL(jo.total_amount, 0)                        AS parts_cost,
            (IFNULL(jo.total_amount_service, 0)
             + IFNULL(jo.total_amount, 0)
             + IFNULL(jo.total_am_sub, 0))                    AS total_cost,
            (
                SELECT GROUP_CONCAT(DISTINCT COALESCE(emp.employee_name, si.employee) SEPARATOR ', ')
                FROM `tabService Item` si
                LEFT JOIN `tabEmployee` emp ON emp.name = si.employee
                WHERE si.parent = jo.name
                  AND si.employee IS NOT NULL AND si.employee != ''
            )                                                 AS technician,
            (
                SELECT GROUP_CONCAT(DISTINCT COALESCE(joi.item_name, joi.item_code) SEPARATOR ', ')
                FROM `tabJob Order Item` joi
                WHERE joi.parent = jo.name
            )                                                 AS parts_replaced
        FROM `tabJob Order` jo
        WHERE {conditions}
        ORDER BY jo.expected_completion_date ASC, jo.name ASC
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    return rows


# ---------------------------------------------------------------------------
# Print layout ("Vehicle Service Log History" sheet, matches dealership form)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_print_html(vehicle, from_date=None, to_date=None, job_type=None, status=None):
    filters = frappe._dict(
        vehicle=vehicle,
        from_date=from_date or None,
        to_date=to_date or None,
        job_type=job_type or None,
        status=status or None,
    )

    rows = get_data(filters)
    vehicle_doc = frappe.get_doc("Vehicle", vehicle)

    # Latest job order for this vehicle carries the freshest customer / contact info
    latest = frappe.db.get_value(
        "Job Order",
        {"vehicle": vehicle, "docstatus": ("<", 2)},
        ["customer", "contact_no", "make", "model", "year", "fuel_type", "chasis_number"],
        order_by="expected_completion_date desc",
        as_dict=True,
    ) or frappe._dict()

    customer_name = None
    if latest.get("customer"):
        customer_name = frappe.db.get_value("Customer", latest.customer, "customer_name") or latest.customer
    elif vehicle_doc.get("custom_customer"):
        customer_name = frappe.db.get_value("Customer", vehicle_doc.custom_customer, "customer_name") or vehicle_doc.custom_customer

    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
        "Global Defaults", "default_company"
    )
    company_doc = frappe.get_doc("Company", company) if company else frappe._dict()

    context = {
        "company_name": company_doc.get("company_name") or "[ DEALERSHIP NAME ]",
        "customer_name": customer_name or "",
        "contact_no": latest.get("contact_no") or "",
        "current_odometer": vehicle_doc.get("last_odometer") or "",
        "vehicle_reg_no": vehicle_doc.get("license_plate") or vehicle_doc.name,
        "chassis_no": vehicle_doc.get("chassis_no") or latest.get("chasis_number") or "",
        "engine_no": vehicle_doc.get("custom_engine_no") or "",
        "make": vehicle_doc.get("make") or latest.get("make") or "",
        "model": vehicle_doc.get("custom_custom_model") or vehicle_doc.get("model") or latest.get("model") or "",
        "year": vehicle_doc.get("custom_year") or latest.get("year") or "",
        "fuel_type": vehicle_doc.get("fuel_type") or latest.get("fuel_type") or "",
        "rows": rows,
        "formatdate": formatdate,
        "flt": flt,
    }

    return frappe.render_template(PRINT_TEMPLATE, context)


PRINT_TEMPLATE = """
<style>
    @media print { @page { size: A4 landscape; margin: 10mm; } }
    .vslh { font-family: "Times New Roman", Georgia, serif; color: #1a1a1a; font-size: 11px; }
    .vslh h1 { text-align: center; font-size: 20px; margin: 0; letter-spacing: 1px; }
    .vslh .sub { text-align: center; color: #666; margin: 2px 0 10px; font-size: 11px; }
    .vslh h2 { text-align: center; font-size: 15px; margin: 8px 0; border-bottom: 2px solid #1a1a1a;
               border-top: 2px solid #1a1a1a; padding: 6px 0; }
    .vslh table { border-collapse: collapse; width: 100%; }
    .vslh .info td { border: 1px solid #1a1a1a; padding: 6px 8px; }
    .vslh .info .lbl { background: #e9eaed; font-weight: bold; width: 13%; }
    .vslh .log { margin-top: 14px; }
    .vslh .log th { background: #1f2a44; color: #fff; border: 1px solid #1f2a44; padding: 6px 5px;
                    font-size: 10px; text-align: center; }
    .vslh .log td { border: 1px solid #555; padding: 6px 5px; vertical-align: top; font-size: 10px; }
    .vslh .log td.num { text-align: right; white-space: nowrap; }
    .vslh .log td.c { text-align: center; }
    .vslh .tot td { font-weight: bold; background: #f2f2f2; }
</style>

<div class="vslh">
    <h1>{{ company_name }}</h1>
    <div class="sub">Address Line &bull; Phone &bull; Email &bull; Service Center</div>
    <h2>VEHICLE SERVICE LOG HISTORY</h2>

    <table class="info">
        <tr>
            <td class="lbl">Customer Name</td><td>{{ customer_name }}</td>
            <td class="lbl">Contact No.</td><td>{{ contact_no }}</td>
            <td class="lbl">Current Odometer</td><td>{{ current_odometer }}</td>
        </tr>
        <tr>
            <td class="lbl">Vehicle Reg. No.</td><td>{{ vehicle_reg_no }}</td>
            <td class="lbl">VIN / Chassis No.</td><td>{{ chassis_no }}</td>
            <td class="lbl">Engine No.</td><td>{{ engine_no }}</td>
        </tr>
        <tr>
            <td class="lbl">Make / Model</td><td>{{ make }} {{ model }}</td>
            <td class="lbl">Year</td><td>{{ year }}</td>
            <td class="lbl">Fuel Type</td><td>{{ fuel_type }}</td>
        </tr>
    </table>

    <table class="log">
        <thead>
            <tr>
                <th style="width:32px;">S.No</th>
                <th style="width:70px;">Date</th>
                <th style="width:70px;">Odometer<br>(km/mi)</th>
                <th style="width:80px;">Job Card No.</th>
                <th style="width:75px;">Service Type</th>
                <th>Work Description</th>
                <th style="width:150px;">Parts Replaced</th>
                <th style="width:70px;">Labor<br>Charge</th>
                <th style="width:70px;">Parts Cost</th>
                <th style="width:75px;">Total Cost</th>
                <th style="width:110px;">Technician</th>
            </tr>
        </thead>
        <tbody>
            {% set ns = namespace(labor=0, parts=0, total=0) %}
            {% for r in rows %}
            {% set ns.labor = ns.labor + flt(r.labor_charge) %}
            {% set ns.parts = ns.parts + flt(r.parts_cost) %}
            {% set ns.total = ns.total + flt(r.total_cost) %}
            <tr>
                <td class="c">{{ loop.index }}</td>
                <td class="c">{{ formatdate(r.posting_date, "dd-MM-yyyy") if r.posting_date else "" }}</td>
                <td class="num">{{ r.odometer or "" }}</td>
                <td>{{ r.job_card }}</td>
                <td>{{ r.service_type or "" }}</td>
                <td>{{ r.work_description or "" }}</td>
                <td>{{ r.parts_replaced or "" }}</td>
                <td class="num">{{ "%.2f"|format(flt(r.labor_charge)) }}</td>
                <td class="num">{{ "%.2f"|format(flt(r.parts_cost)) }}</td>
                <td class="num">{{ "%.2f"|format(flt(r.total_cost)) }}</td>
                <td>{{ r.technician or "" }}</td>
            </tr>
            {% endfor %}
            {% if rows %}
            <tr class="tot">
                <td class="c" colspan="7">TOTAL</td>
                <td class="num">{{ "%.2f"|format(ns.labor) }}</td>
                <td class="num">{{ "%.2f"|format(ns.parts) }}</td>
                <td class="num">{{ "%.2f"|format(ns.total) }}</td>
                <td></td>
            </tr>
            {% else %}
            <tr><td class="c" colspan="11">No job orders found for this vehicle.</td></tr>
            {% endif %}
        </tbody>
    </table>
</div>
"""
