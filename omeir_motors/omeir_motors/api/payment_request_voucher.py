import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate
from frappe.utils.pdf import get_pdf

PRINT_FORMAT = "Payment Request Voucher"
PDF_OPTIONS = {
	"page-size": "A4",
	"margin-top": "12mm",
	"margin-bottom": "15mm",
	"margin-left": "12mm",
	"margin-right": "12mm",
}


@frappe.whitelist()
def download_payment_request_voucher(invoices, paid_from=None, mode_of_payment=None):
	"""Print the Payment Request Voucher for Purchase Invoices picked in the Accounts Payable report.

	`invoices` is a list of {"invoice": <Purchase Invoice>, "amount": <amount requested>}.
	Nothing is saved; the voucher is rendered from the invoices as they stand now.
	"""
	if isinstance(invoices, str):
		invoices = json.loads(invoices)

	doc = get_voucher_doc(invoices, paid_from, mode_of_payment)
	template = frappe.db.get_value("Print Format", PRINT_FORMAT, "html")
	if not template:
		frappe.throw(_("Print Format {0} not found").format(frappe.bold(PRINT_FORMAT)))

	html = frappe.render_template(template, {"doc": doc})
	html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{doc.name}</title></head>
<body><div class="print-format">{html}</div></body></html>"""

	frappe.local.response.filename = f"Payment Request Voucher {doc.name}.pdf"
	frappe.local.response.filecontent = get_pdf(html, dict(PDF_OPTIONS))
	frappe.local.response.type = "pdf"


def get_voucher_doc(invoices, paid_from=None, mode_of_payment=None):
	"""Shape the picked invoices like a draft Payment Entry so the print format can render them."""
	if not invoices:
		frappe.throw(_("Select at least one Purchase Invoice"))

	references = []
	first = None
	for row in invoices:
		pi = frappe.get_doc("Purchase Invoice", row.get("invoice"))
		pi.check_permission("read")

		if pi.docstatus != 1 or flt(pi.outstanding_amount) <= 0:
			frappe.throw(_("Purchase Invoice {0} has no outstanding amount").format(frappe.bold(pi.name)))

		if first and pi.supplier != first.supplier:
			frappe.throw(_("All invoices in a Payment Request Voucher must be for the same supplier"))
		first = first or pi

		amount = flt(row.get("amount"), pi.precision("outstanding_amount"))
		if amount <= 0 or amount > flt(pi.outstanding_amount):
			frappe.throw(
				_("Payment Amount for {0} must be more than 0 and not more than its outstanding {1}").format(
					frappe.bold(pi.name), frappe.bold(frappe.format_value(pi.outstanding_amount, currency=pi.currency))
				)
			)

		references.append(
			frappe._dict(
				reference_doctype="Purchase Invoice",
				reference_name=pi.name,
				bill_no=pi.bill_no,
				due_date=pi.due_date,
				total_amount=pi.grand_total,
				outstanding_amount=pi.outstanding_amount,
				allocated_amount=amount,
			)
		)

	return frappe._dict(
		name=first.name,
		docstatus=0,
		posting_date=nowdate(),
		company=first.company,
		party_type="Supplier",
		party=first.supplier,
		party_name=first.supplier_name,
		mode_of_payment=mode_of_payment,
		paid_from=paid_from or frappe.get_cached_value("Company", first.company, "default_bank_account"),
		paid_from_account_currency=first.party_account_currency or first.currency,
		bank_account=None,
		references=references,
	)
