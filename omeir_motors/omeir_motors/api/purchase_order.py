import frappe
from frappe import _
from frappe.utils import get_link_to_form

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
		if item.rate != standard_rate:
			frappe.throw(
				_(
					"You are not allowed to change the rate of item {0}. "
					"Expected standard buying rate: {1}, but got: {2}."
				).format(
					frappe.bold(item.item_code),
					frappe.bold(standard_rate),
					frappe.bold(item.rate),
				),
				title=_("Rate Change Not Permitted"),
			)


def validate_duplicate_invoice_ref(doc, method=None):
	existing_po = get_duplicate_purchase_order(
		doc.custom_invoice_ref,
		doc.supplier,
		doc.name,
	)
	if existing_po:
		frappe.throw(
			_(
				"Supplier invoice reference {0} already exists on Purchase Order {1} for supplier {2}. "
				"Duplicate invoice entries are not allowed."
			).format(
				frappe.bold((doc.custom_invoice_ref or "").strip()),
				get_link_to_form("Purchase Order", existing_po),
				frappe.bold(doc.supplier),
			),
			title=_("Duplicate Invoice Alert"),
		)


@frappe.whitelist()
def check_duplicate_invoice_ref(invoice_ref, supplier=None, name=None):
	invoice_ref = (invoice_ref or "").strip()
	if not invoice_ref:
		return {"duplicate": False}

	existing_po = get_duplicate_purchase_order(invoice_ref, supplier, name)
	if not existing_po:
		return {"duplicate": False}

	return {
		"duplicate": True,
		"existing_po": existing_po,
		"message": _(
			"Supplier invoice reference <b>{0}</b> already exists on Purchase Order <b>{1}</b>."
		).format(frappe.bold(invoice_ref), frappe.bold(existing_po)),
	}


def get_duplicate_purchase_order(invoice_ref, supplier=None, name=None):
	invoice_ref = (invoice_ref or "").strip()
	if not invoice_ref or not supplier:
		return None

	filters = {
		"custom_invoice_ref": invoice_ref,
		"supplier": supplier,
		"docstatus": ("<", 2),
		"name": ("!=", name or ""),
	}

	return frappe.db.get_value("Purchase Order", filters, "name", order_by="creation desc")


