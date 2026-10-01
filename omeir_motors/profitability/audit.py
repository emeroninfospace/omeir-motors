"""Read-only fingerprints for before/after verification on the target site."""

import hashlib
import json

import frappe

# All business columns, including names, amounts and timestamps, are covered.
# Only the two new metadata fields are excluded from comparison.
TABLES = (
	"GL Entry",
	"Payment Ledger Entry",
	"Sales Invoice",
	"Sales Invoice Item",
	"Subcontract Invoice",
	"Subcontract Invoice Item",
	"Job Order",
	"Sublet Items",
)
METADATA = {"custom_job_order_sublet_row", "job_order_sublet_row"}


def snapshot():
	result = {}
	for table in TABLES:
		digest = hashlib.sha256()
		count = 0
		# Fixed application-controlled table names, never user input.
		for row in frappe.db.sql(f"SELECT * FROM `tab{table}` ORDER BY name", as_dict=True):
			business = {k: v for k, v in row.items() if k not in METADATA}
			digest.update(json.dumps(business, sort_keys=True, default=str).encode())
			digest.update(b"\n")
			count += 1
		result[table] = {"count": count, "sha256": digest.hexdigest()}
	return result


def verified_backfill(dry_run=True):
	from omeir_motors.profitability.backfill import run

	before = snapshot()
	result = run(dry_run=dry_run)
	after = snapshot()
	if before != after:
		frappe.throw(
			"Accounting/business data fingerprint changed. Roll back this transaction and investigate."
		)
	result["business_data_unchanged"] = True
	result["fingerprints"] = before
	return result
