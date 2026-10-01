"""Pure, deterministic allocation rules shared by migration and runtime."""

import unicodedata
from decimal import Decimal
from html.parser import HTMLParser


class MappingError(ValueError):
	pass


def resolve_sublet(item_code, explicit, sublets, other_items=(), *, details=None, require_details=False):
	# Frappe child Documents support get(), but are not subscriptable like dict rows.
	if explicit:
		matches = [r for r in sublets if r.get("name") == explicit and r.get("item_code") == item_code]
	else:
		matches = [r for r in sublets if r.get("item_code") == item_code]
		if item_code in other_items:
			raise MappingError("Item also appears outside the sublet table; select the exact sublet row.")
		if len(matches) > 1 or require_details:
			if not details or not normalize_description(details.get("description")):
				raise MappingError("Repeated service item needs a description or an explicit sublet row.")
			matches = [r for r in matches if matches_details(r, details)]
	if len(matches) != 1:
		raise MappingError("Expected one matching Job Order sublet row; select the exact row explicitly.")
	return matches[0]


class _DescriptionText(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.parts = []

	def handle_data(self, data):
		self.parts.append(data)

	def handle_starttag(self, tag, attrs):
		if tag in {"p", "div", "br", "li", "tr"}:
			self.parts.append(" ")

	def handle_endtag(self, tag):
		if tag in {"p", "div", "li", "tr"}:
			self.parts.append(" ")


def normalize_description(value):
	parser = _DescriptionText()
	parser.feed(value or "")
	return " ".join(unicodedata.normalize("NFKC", "".join(parser.parts)).casefold().split())


def same_number(left, right):
	# Missing values are not zero; zero-valued service rates are valid.
	if left is None or right is None:
		return False
	left, right = Decimal(str(left)), Decimal(str(right))
	return left.is_finite() and right.is_finite() and abs(left - right) <= Decimal("0.000001")


def matches_details(sublet, details):
	return (
		normalize_description(sublet.get("description")) == normalize_description(details.get("description"))
		and same_number(sublet.get("quantity"), details.get("quantity"))
		and same_number(sublet.get(details["rate_field"]), details.get("rate"))
		and (details.get("uom") is None or sublet.get("uom") == details["uom"])
	)


def same_sale_details(left, right):
	return (
		normalize_description(left.get("description")) == normalize_description(right.get("description"))
		and same_number(left.get("qty"), right.get("qty"))
		and same_number(left.get("base_rate"), right.get("base_rate"))
		and left.get("uom") == right.get("uom")
	)


def allocated_cost(total_cost, job_stock_qty, invoice_stock_qty):
	cost, planned, sold = (Decimal(str(v)) for v in (total_cost, job_stock_qty, invoice_stock_qty))
	if not all(v.is_finite() for v in (cost, planned, sold)) or planned <= 0 or cost < 0:
		raise MappingError("Subcontract cost must be non-negative and job stock quantity must be positive.")
	return float(cost * sold / planned)
