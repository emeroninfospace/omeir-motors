import frappe
from frappe.utils import flt


def execute():
    
    job_orders = frappe.get_all("Job Order", fields=["name"])
    print(f"Found {len(job_orders)} Job Order(s) to patch...")

    for jo in job_orders:
        doc = frappe.get_doc("Job Order", jo.name)

        total_qty    = 0.0
        total_amount = 0.0

        for row in doc.get("sublet_details") or []:
            rate        = flt(row.rate)
            quantity    = flt(row.quantity)
            margin_rate = flt(rate + (rate * 5 / 100), 2)   # rate + 5%

            frappe.db.set_value(
                "Sublet Items",
                row.name,
                "margin_rate",
                margin_rate,
                update_modified=False,
            )

            total_qty    += quantity
            total_amount += flt(margin_rate * quantity, 2)

        frappe.db.set_value(
            "Job Order",
            jo.name,
            {
                "total_qty_sub": flt(total_qty, 3),
                "total_am_sub":  flt(total_amount, 2),
            },
            update_modified=False,
        )

    frappe.db.commit()
    print("✅ Patch completed — margin_rate, total_qty_sub, total_am_sub updated.")