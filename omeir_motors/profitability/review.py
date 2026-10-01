"""CLI-only application of human-reviewed row mappings."""

import frappe
from frappe.utils import cint

from omeir_motors.profitability.audit import snapshot
from omeir_motors.profitability.mapping import SOURCE_FIELD, resolve_sale, resolve_source
from omeir_motors.profitability.setup import SALES_FIELD


def apply_links(links, dry_run=True):
	"""links: [{doctype, name, sublet_row}]; no accounting or invoice lifecycle calls."""
	if isinstance(links, str):
		links = frappe.parse_json(links)
	dry_run = bool(cint(dry_run))
	supported = {
		"Sales Invoice Item": ("Sales Invoice", SALES_FIELD, resolve_sale),
		"Subcontract Invoice Item": ("Subcontract Invoice", SOURCE_FIELD, resolve_source),
	}
	before = snapshot()
	changes = []
	seen = set()
	for entry in links:
		dt = entry["doctype"]
		if dt not in supported or (dt, entry["name"]) in seen:
			frappe.throw("Provide each supported invoice row only once.")
		seen.add((dt, entry["name"]))
		parent_type, field, resolver = supported[dt]
		parent = frappe.db.get_value(dt, entry["name"], "parent")
		doc = frappe.get_doc(parent_type, parent)
		if doc.docstatus != 1:
			frappe.throw("Reviewed linking is only for submitted invoices.")
		row = next(r for r in doc.items if r.name == entry["name"])
		if frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			frappe.throw("Reviewed linking only supports non-stock service items.")
		old = row.get(field)
		target = entry.get("sublet_row")
		if not target:
			frappe.throw("An explicit sublet row ID is required.")
		row.set(field, target)
		if resolver(doc, row) != target:
			frappe.throw("The reviewed link is inconsistent with the job/item.")
		changes.append({"doctype": dt, "name": row.name, "field": field, "before": old, "after": target})
		if not dry_run and old != target:
			frappe.db.set_value(dt, row.name, field, target, update_modified=False)
	if snapshot() != before:
		frappe.throw("Business data changed during reviewed linking. Roll back the transaction.")
	result = {"dry_run": dry_run, "changes": changes, "business_data_unchanged": True}
	if not dry_run:
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "subcontract-profitability-reviewed-links.json",
				"is_private": 1,
				"content": frappe.as_json(result),
			}
		).insert(ignore_permissions=True)
	return result
