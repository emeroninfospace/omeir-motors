import frappe
from frappe import _
from frappe.utils import get_link_to_form



def validate_duplicate_receipt_ref(doc, method=None):
	existing_po = get_duplicate_purchase_receipt(
		doc.custom_invoice_no,
		doc.supplier,
		doc.name,
	)
	if existing_po:
		frappe.throw(
			_(
				"Supplier invoice reference {0} already exists on Purchase Receipt {1} for supplier {2}. "
				"Duplicate invoice entries are not allowed."
			).format(
				frappe.bold((doc.custom_invoice_no or "").strip()),
				get_link_to_form("Purchase Receipt", existing_po),
				frappe.bold(doc.supplier),
			),
			title=_("Duplicate Invoice Alert"),
		)


@frappe.whitelist()
def check_duplicate_receipt_ref(invoice_ref, supplier=None, name=None):
	invoice_ref = (invoice_ref or "").strip()
	if not invoice_ref:
		return {"duplicate": False}

	existing_po = get_duplicate_purchase_receipt(invoice_ref, supplier, name)
	if not existing_po:
		return {"duplicate": False}

	return {
		"duplicate": True,
		"existing_po": existing_po,
		"message": _(
			"Supplier invoice reference <b>{0}</b> already exists on Purchase Receipt <b>{1}</b>."
		).format(frappe.bold(invoice_ref), frappe.bold(existing_po)),
	}


def get_duplicate_purchase_receipt(invoice_ref, supplier=None, name=None):
	invoice_ref = (invoice_ref or "").strip()
	if not invoice_ref or not supplier:
		return None

	filters = {
		"custom_invoice_no": invoice_ref,
		"supplier": supplier,
		"docstatus": ("<", 2),
		"name": ("!=", name or ""),
	}

	return frappe.db.get_value("Purchase Receipt", filters, "name", order_by="creation desc")
