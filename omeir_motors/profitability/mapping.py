"""Mapping validation. No save/submit or ledger calls in historical linking."""

import frappe
from frappe.utils import flt

from omeir_motors.profitability.allocation import MappingError, resolve_sublet
from omeir_motors.profitability.setup import SALES_FIELD

SOURCE_FIELD = "job_order_sublet_row"


def job_context(job_name, company):
	job = frappe.get_doc("Job Order", job_name)
	if job.company != company or job.docstatus == 2:
		raise MappingError("Job Order must be active and belong to the same company.")
	return job


def stock_quantity(job_row):
	from erpnext.stock.get_item_details import get_conversion_factor

	factor = get_conversion_factor(job_row.item_code, job_row.uom).get("conversion_factor")
	if not factor or flt(job_row.quantity) <= 0:
		raise MappingError("Job Order sublet row needs a positive quantity and a valid UOM conversion.")
	return flt(job_row.quantity) * flt(factor)


def resolve_source(doc, row):
	if not row.job_order:
		raise MappingError("Subcontract row needs a Job Order.")
	job = job_context(row.job_order, doc.company)
	target = resolve_sublet(row.item_code, row.get(SOURCE_FIELD), job.sublet_details)
	stock_quantity(target)
	if flt(row.quantity) <= 0 or flt(row.amount) < 0:
		raise MappingError("Subcontract row needs positive quantity and non-negative cost.")
	return target.name


def validate_source(doc, method=None):
	for row in doc.items:
		if frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			if row.get(SOURCE_FIELD):
				frappe.throw("Subcontract profitability links only support non-stock service items.")
			continue
		try:
			row.set(SOURCE_FIELD, resolve_source(doc, row))
		except MappingError as exc:
			frappe.throw(f"Row {row.idx}: {exc}")


def resolve_sale(doc, row):
	job_name = doc.get("custom_job_order")
	if not job_name:
		if row.get(SALES_FIELD):
			raise MappingError("Sales Invoice needs its Job Order before linking a sublet row.")
		return None
	job = job_context(job_name, doc.company)
	relevant = [r for r in job.sublet_details if r.item_code == row.item_code]
	if not relevant and not row.get(SALES_FIELD):
		return None
	if frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
		if row.get(SALES_FIELD):
			raise MappingError("Only non-stock service items support subcontract profitability links.")
		return None
	# Returned rows must reference the original invoice item, never item code alone.
	explicit = row.get(SALES_FIELD)
	if doc.get("is_return") and doc.get("return_against"):
		original_doc = frappe.get_doc("Sales Invoice", doc.return_against)
		original_row = next((r for r in original_doc.items if r.name == row.get("sales_invoice_item")), None)
		if (
			original_doc.docstatus != 1
			or original_doc.get("is_return")
			or original_doc.company != doc.company
			or original_doc.get("custom_job_order") != job_name
			or not original_row
			or original_row.item_code != row.item_code
		):
			raise MappingError(
				"Return needs the original submitted Sales Invoice Item in the same job/company."
			)
		original = resolve_sale(original_doc, original_row)
		if not original or (explicit and explicit != original):
			raise MappingError("Return needs the original Sales Invoice Item with its sublet link.")
		explicit = original
	if not explicit and sum(r.item_code == row.item_code for r in doc.items) != 1:
		raise MappingError("Repeated service item on invoice; select each exact sublet row.")
	others = [r.item_code for r in list(job.service_item or []) + list(job.job_order_items or [])]
	target = resolve_sublet(row.item_code, explicit, relevant, others)
	stock_quantity(target)
	if row.get("delivered_by_supplier") or frappe.db.exists("Product Bundle", row.item_code):
		raise MappingError("Subcontract links do not support drop shipping or Product Bundles.")
	return target.name


def validate_sales(doc, method=None):
	for row in doc.items:
		try:
			target = resolve_sale(doc, row)
			if target:
				row.set(SALES_FIELD, target)
		except MappingError as exc:
			frappe.throw(f"Row {row.idx}: {exc}")


def check_sales_capacity(doc, method=None):
	"""Serialize same-job submits to prevent allocating one job's cost twice."""
	validate_sales(doc)
	names = sorted({r.get(SALES_FIELD) for r in doc.items if r.get(SALES_FIELD)})
	for name in names:
		frappe.db.sql("SELECT name FROM `tabSublet Items` WHERE name=%s FOR UPDATE", name)
		existing = frappe.db.sql(
			"""
            SELECT COALESCE(SUM(sii.stock_qty), 0)
            FROM `tabSales Invoice Item` sii JOIN `tabSales Invoice` si ON si.name=sii.parent
            WHERE si.docstatus=1 AND sii.custom_job_order_sublet_row=%s AND si.name!=%s
        """,
			(name, doc.name),
		)[0][0]
		new_qty = sum(flt(r.stock_qty) for r in doc.items if r.get(SALES_FIELD) == name)
		planned = stock_quantity(frappe.get_doc("Sublet Items", name))
		if flt(existing) + new_qty > planned + 0.000001 or flt(existing) + new_qty < -0.000001:
			frappe.throw(
				f"Sublet row {name}: total invoiced stock quantity must remain between 0 and {planned}."
			)
