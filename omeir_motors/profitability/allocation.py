"""Pure, deterministic allocation rules shared by migration and runtime."""

from decimal import Decimal


class MappingError(ValueError):
	pass


def resolve_sublet(item_code, explicit, sublets, other_items=()):
	# Frappe child Documents support get(), but are not subscriptable like dict rows.
	if explicit:
		matches = [r for r in sublets if r.get("name") == explicit and r.get("item_code") == item_code]
	else:
		matches = [r for r in sublets if r.get("item_code") == item_code]
		if item_code in other_items:
			raise MappingError("Item also appears outside the sublet table; select the exact sublet row.")
	if len(matches) != 1:
		raise MappingError("Expected one matching Job Order sublet row; select the exact row explicitly.")
	return matches[0]


def allocated_cost(total_cost, job_stock_qty, invoice_stock_qty):
	cost, planned, sold = (Decimal(str(v)) for v in (total_cost, job_stock_qty, invoice_stock_qty))
	if not all(v.is_finite() for v in (cost, planned, sold)) or planned <= 0 or cost < 0:
		raise MappingError("Subcontract cost must be non-negative and job stock quantity must be positive.")
	return float(cost * sold / planned)
