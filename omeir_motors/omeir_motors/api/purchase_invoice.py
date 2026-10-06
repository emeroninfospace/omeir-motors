import frappe
from frappe import _

RATE_CHANGE_ALLOWED_ROLES = {"Accounts Manager", "Parts Manager", "Manager", "Administrator"}


def validate_item_rate(doc, method=None):
	if set(frappe.get_roles(frappe.session.user)) & RATE_CHANGE_ALLOWED_ROLES:
		return

	for item in doc.items:
		standard_rate = frappe.db.get_value(
			"Item Price",
			{"item_code": item.item_code, "price_list": "Standard Buying", "selling": 0},
			"price_list_rate",
		)
		if standard_rate is None:
			continue
		if item.rate > standard_rate:
			frappe.throw(
				_(
					"You are not allowed to increase the rate of item {0}. "
					"Standard buying rate is {1}, but got: {2}."
				).format(
					frappe.bold(item.item_code),
					frappe.bold(standard_rate),
					frappe.bold(item.rate),
				),
				title=_("Rate Increase Not Permitted"),
			)


def validate_bill_date(doc, method=None):
	if not doc.bill_date:
		return

	if doc.bill_date != doc.posting_date:
		frappe.throw(
			_(
				"Supplier Invoice Date ({0}) and Posting Date ({1}) must be the same."
			).format(
				frappe.bold(frappe.utils.formatdate(doc.bill_date)),
				frappe.bold(frappe.utils.formatdate(doc.posting_date)),
			),
			title=_("Date Mismatch"),
		)

