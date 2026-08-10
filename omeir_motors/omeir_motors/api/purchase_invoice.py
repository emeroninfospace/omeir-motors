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
