"""Retry previously unresolved repeated-item rows with exact descriptive evidence."""

import frappe

from omeir_motors.profitability.audit import verified_backfill


def execute():
	result = verified_backfill(dry_run=False)
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "subcontract-profitability-description-backfill.json",
			"is_private": 1,
			"content": frappe.as_json(result),
		}
	).insert(ignore_permissions=True)
	print(
		f"Subcontract description backfill: linked {len(result['linked'])}; review {len(result['review'])} rows."
	)
