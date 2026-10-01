"""Idempotent, conservative historical link patch. Only two Data fields are written."""

import frappe
from frappe.utils import cint

from omeir_motors.profitability.allocation import MappingError
from omeir_motors.profitability.mapping import SOURCE_FIELD, resolve_sale, resolve_source
from omeir_motors.profitability.setup import SALES_FIELD


def run(dry_run=True):
	# CLI-only, intentionally not whitelisted. No internal commits: migration owns transaction.
	dry_run = bool(cint(dry_run))
	result = {"dry_run": dry_run, "linked": [], "unchanged": 0, "review": []}
	for doctype, field, resolver in (
		("Subcontract Invoice", SOURCE_FIELD, resolve_source),
		("Sales Invoice", SALES_FIELD, resolve_sale),
	):
		filters = {"docstatus": 1}
		if doctype == "Sales Invoice":
			filters["custom_job_order"] = ["is", "set"]
		for name in frappe.get_all(doctype, filters=filters, pluck="name", order_by="creation asc"):
			doc = frappe.get_doc(doctype, name)
			for row in doc.items:
				if frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
					continue
				try:
					target = resolver(doc, row)
				except MappingError as exc:
					result["review"].append(
						{"doctype": doctype, "document": name, "row": row.name, "reason": str(exc)}
					)
					continue
				if not target or row.get(field) == target:
					result["unchanged"] += 1
					continue
				# Never overwrite an existing link. Invalid links are review exceptions above.
				if row.get(field):
					result["review"].append(
						{
							"doctype": doctype,
							"document": name,
							"row": row.name,
							"reason": "Existing link differs.",
						}
					)
					continue
				result["linked"].append(
					{"doctype": row.doctype, "row": row.name, "field": field, "value": target}
				)
				if not dry_run:
					frappe.db.set_value(row.doctype, row.name, field, target, update_modified=False)
	return result
