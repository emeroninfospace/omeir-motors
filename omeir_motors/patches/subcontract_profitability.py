import frappe

from omeir_motors.profitability.audit import verified_backfill
from omeir_motors.profitability.setup import ensure_fields


def execute():
	ensure_fields()
	result = verified_backfill(dry_run=False)
	# Persist the complete audit on the site, including unresolved rows, without touching invoices.
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "subcontract-profitability-backfill.json",
			"is_private": 1,
			"content": frappe.as_json(result),
		}
	).insert(ignore_permissions=True)
	print(
		f"Subcontract profitability: linked {len(result['linked'])}; review {len(result['review'])} rows. See private backfill JSON in File list."
	)
