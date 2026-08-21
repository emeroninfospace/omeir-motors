import frappe
from frappe.model.document import Document
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils import getdate, flt


class SubcontractInvoice(Document):
    def validate(self):
        self.calculate_totals()
        self.calculate_taxes()

    def on_submit(self):
        self.make_gl_entries()
        self.db_set("status", "Unpaid", update_modified=False)

    def before_cancel(self):
        self._cancel_linked_journal_entries()

    def on_cancel(self):
        self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
        from erpnext.accounts.general_ledger import make_reverse_gl_entries
        make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
        self.db_set("status", "Cancelled", update_modified=False)

    def on_trash(self):
        self._delete_linked_journal_entries()
        frappe.db.sql("""
            DELETE FROM `tabGL Entry`
            WHERE voucher_type = 'Subcontract Invoice' AND voucher_no = %s
        """, self.name)
        frappe.db.sql("""
            DELETE FROM `tabPayment Ledger Entry`
            WHERE voucher_type = 'Subcontract Invoice' AND voucher_no = %s
        """, self.name)

    def _cancel_linked_journal_entries(self):
        linked_jes = frappe.db.sql_list("""
            SELECT DISTINCT voucher_no
            FROM `tabGL Entry`
            WHERE against_voucher_type = 'Subcontract Invoice'
              AND against_voucher = %s
              AND voucher_type = 'Journal Entry'
              AND is_cancelled = 0
        """, self.name)

        for je_name in linked_jes:
            je_doc = frappe.get_doc("Journal Entry", je_name)
            if je_doc.docstatus == 1:
                je_doc.cancel()

    def _delete_linked_journal_entries(self):
        linked_jes = frappe.db.sql_list("""
            SELECT DISTINCT voucher_no
            FROM `tabGL Entry`
            WHERE against_voucher_type = 'Subcontract Invoice'
              AND against_voucher = %s
              AND voucher_type = 'Journal Entry'
        """, self.name)

        for je_name in linked_jes:
            je_doc = frappe.get_doc("Journal Entry", je_name)
            if je_doc.docstatus == 1:
                je_doc.cancel()
            frappe.delete_doc("Journal Entry", je_name, ignore_permissions=True, force=True)

    def update_payment_status(self):
        paid = flt(self.paid_amount, 2)
        grand = flt(self.grand_total, 2)

        if paid <= 0:
            status = "Unpaid"
        elif paid >= grand:
            status = "Paid"
        else:
            status = "Partially Paid"

        self.db_set("status", status, update_modified=False)

    def make_gl_entries(self):
        company = frappe.get_doc("Company", self.company)

        payable_account = company.default_payable_account
        expense_account = company.custom_subcontract_account

        if not payable_account or not expense_account:
            frappe.throw("Set Default Payable Account and Subcontract Account in Company")

        if not self.cost_center:
            self.cost_center = frappe.db.get_value("Company", self.company, "cost_center")

        posting_date = getdate(self.transaction_date)

        gl_entries = []

        gl_entries.append(frappe._dict({
            "account": expense_account,
            "debit": self.total_amount,
            "debit_in_account_currency": self.total_amount,
            "against": payable_account,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "company": self.company,
            "posting_date": posting_date,
            "cost_center": self.cost_center,
            "project": self.project
        }))

        for tax in self.purchase_taxes_and_charges:
            if tax.tax_amount:
                gl_entries.append(frappe._dict({
                    "account": tax.account_head,
                    "debit": tax.tax_amount,
                    "debit_in_account_currency": tax.tax_amount,
                    "against": payable_account,
                    "voucher_type": self.doctype,
                    "voucher_no": self.name,
                    "company": self.company,
                    "posting_date": posting_date,
                    "cost_center": self.cost_center,
                    "project": self.project
                }))

        gl_entries.append(frappe._dict({
            "account": payable_account,
            "credit": self.grand_total,
            "credit_in_account_currency": self.grand_total,
            "against": expense_account,
            "party_type": "Supplier",
            "party": self.supplier,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "against_voucher_type": self.doctype,
            "against_voucher": self.name,
            "company": self.company,
            "posting_date": posting_date,
            "cost_center": self.cost_center,
            "project": self.project
        }))

        make_gl_entries(gl_entries)

    def calculate_totals(self):
        self.total_quantity = 0
        self.total_amount = 0

        for item in self.items:
            item.amount = (item.rate or 0) * (item.quantity or 0)
            self.total_quantity += item.quantity or 0
            self.total_amount += item.amount or 0

    def calculate_taxes(self):
        added = 0
        deducted = 0

        for tax in self.purchase_taxes_and_charges:
            if tax.charge_type == "On Net Total":
                tax.tax_amount = flt((self.total_amount * (tax.rate or 0)) / 100, 2)

            if tax.add_deduct_tax == "Add":
                added += flt(tax.tax_amount or 0, 2)
            elif tax.add_deduct_tax == "Deduct":
                deducted += flt(tax.tax_amount or 0, 2)

        self.taxes_and_charges_added = flt(added, 2)
        self.taxes_and_charges_deducted = flt(deducted, 2)
        self.total_taxes_and_charges = flt(added - deducted, 2)
        self.grand_total = flt((self.total_amount or 0) + self.total_taxes_and_charges, 2)


@frappe.whitelist()
def make_payment_entry(invoice, mode_of_payment, amount, posting_date=None):
    return _create_payment_journal_entry(
        [{"invoice": invoice, "amount": amount}], mode_of_payment, posting_date
    )


@frappe.whitelist()
def make_payment_entry_multi(invoices, mode_of_payment, posting_date=None):
    """
    invoices: list (or JSON string) of {"invoice": <name>, "amount": <float>}
    Pays several Subcontract Invoices in a single Journal Entry.
    """
    if isinstance(invoices, str):
        invoices = frappe.parse_json(invoices)

    return _create_payment_journal_entry(invoices, mode_of_payment, posting_date)


@frappe.whitelist()
def get_outstanding_invoices(supplier, company=None):
    filters = {
        "supplier": supplier,
        "docstatus": 1,
        "status": ["in", ["Unpaid", "Partially Paid"]]
    }
    if company:
        filters["company"] = company

    invoices = frappe.get_all(
        "Subcontract Invoice",
        filters=filters,
        fields=["name", "transaction_date", "company", "grand_total", "paid_amount", "project", "cost_center"],
        order_by="transaction_date asc"
    )

    for inv in invoices:
        inv["outstanding_amount"] = flt(flt(inv.grand_total, 2) - flt(inv.paid_amount, 2), 2)

    return invoices


def _create_payment_journal_entry(allocations, mode_of_payment, posting_date=None):
    if not allocations:
        frappe.throw("Select at least one invoice to pay")

    seen = set()
    invoice_docs = {}
    company = None

    for row in allocations:
        invoice_name = row["invoice"]

        if invoice_name in seen:
            frappe.throw(f"Invoice {invoice_name} is listed more than once")
        seen.add(invoice_name)

        invoice_doc = frappe.get_doc("Subcontract Invoice", invoice_name)

        if invoice_doc.docstatus != 1:
            frappe.throw(f"{invoice_name} is not a submitted invoice")

        if company is None:
            company = invoice_doc.company
        elif invoice_doc.company != company:
            frappe.throw("All invoices in a single payment must belong to the same company")

        invoice_docs[invoice_name] = invoice_doc

    mop = frappe.get_doc("Mode of Payment", mode_of_payment)

    default_account = None
    for acc in mop.accounts:
        if acc.company == company:
            default_account = acc.default_account
            break

    if not default_account:
        frappe.throw("No default account found for Mode of Payment")

    payable_account = frappe.get_value("Company", company, "default_payable_account")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = company
    je.posting_date = getdate(posting_date) if posting_date else frappe.utils.nowdate()

    total_amount = 0
    row_amounts = {}

    for row in allocations:
        invoice_doc = invoice_docs[row["invoice"]]
        amount = flt(row["amount"], 2)

        if amount <= 0:
            frappe.throw(f"Amount for {invoice_doc.name} must be greater than zero")

        paid_amount = flt(invoice_doc.paid_amount or 0, 2)
        grand_total = flt(invoice_doc.grand_total, 2)
        outstanding = flt(grand_total - paid_amount, 2)

        if outstanding <= 0:
            frappe.throw(f"{invoice_doc.name} is already fully paid")

        if amount > outstanding:
            frappe.throw(f"Amount for {invoice_doc.name} cannot exceed outstanding amount: {outstanding}")

        # reference_detail_no is a free-text field (no fixed options like reference_type),
        # used here purely as a unique marker to find this row's GL/Payment Ledger entries
        # afterwards without ambiguity when several invoices share the same supplier.
        je.append("accounts", {
            "account": payable_account,
            "debit_in_account_currency": amount,
            "party_type": "Supplier",
            "party": invoice_doc.supplier,
            "project": invoice_doc.project,
            "cost_center": invoice_doc.cost_center,
            "reference_detail_no": invoice_doc.name
        })

        total_amount += amount
        row_amounts[invoice_doc.name] = amount

    if len(row_amounts) == 1:
        only_invoice = invoice_docs[next(iter(row_amounts))]
        je.cheque_no = only_invoice.name
        je.cheque_date = only_invoice.transaction_date
    else:
        je.user_remark = "Payment against Subcontract Invoices: " + ", ".join(row_amounts.keys())

    je.append("accounts", {
        "account": default_account,
        "credit_in_account_currency": flt(total_amount, 2)
    })

    je.insert(ignore_permissions=True)
    je.submit()

    for invoice_name, amount in row_amounts.items():
        invoice_doc = invoice_docs[invoice_name]

        frappe.db.sql("""
            UPDATE `tabGL Entry`
            SET against_voucher_type = 'Subcontract Invoice',
                against_voucher = %s
            WHERE voucher_type = 'Journal Entry'
              AND voucher_no = %s
              AND voucher_detail_no = %s
        """, (invoice_name, je.name, invoice_name))

        frappe.db.sql("""
            UPDATE `tabPayment Ledger Entry`
            SET against_voucher_type = 'Subcontract Invoice',
                against_voucher_no = %s
            WHERE voucher_type = 'Journal Entry'
              AND voucher_no = %s
              AND voucher_detail_no = %s
        """, (invoice_name, je.name, invoice_name))

        paid_amount = flt(flt(invoice_doc.paid_amount or 0, 2) + amount, 2)

        frappe.db.set_value("Subcontract Invoice", invoice_name, "paid_amount", paid_amount)

        invoice_doc.reload()
        invoice_doc.update_payment_status()

        grand_total = flt(invoice_doc.grand_total, 2)

        if invoice_doc.subcontract_work_order:
            if paid_amount >= grand_total:
                frappe.db.set_value("Subcontract Work Order", invoice_doc.subcontract_work_order, "status", "Paid")
            else:
                frappe.db.set_value("Subcontract Work Order", invoice_doc.subcontract_work_order, "status", "Partially Billed")

    return je.name


def on_journal_entry_cancel(doc, method=None):
    linked_invoices = frappe.db.sql_list("""
        SELECT DISTINCT against_voucher
        FROM `tabGL Entry`
        WHERE voucher_type = 'Journal Entry'
          AND voucher_no = %s
          AND against_voucher_type = 'Subcontract Invoice'
          AND against_voucher IS NOT NULL
          AND against_voucher != ''
    """, doc.name)

    for invoice_name in linked_invoices:
        _recalculate_paid_amount(invoice_name)


def _recalculate_paid_amount(invoice_name):
    paid_amount = flt(frappe.db.sql("""
        SELECT COALESCE(SUM(debit), 0)
        FROM `tabGL Entry`
        WHERE against_voucher_type = 'Subcontract Invoice'
          AND against_voucher = %s
          AND voucher_type = 'Journal Entry'
          AND is_cancelled = 0
          AND party_type = 'Supplier'
    """, invoice_name)[0][0], 2)

    grand_total = flt(frappe.db.get_value("Subcontract Invoice", invoice_name, "grand_total"), 2)

    if paid_amount <= 0:
        status = "Unpaid"
    elif paid_amount >= grand_total:
        status = "Paid"
    else:
        status = "Partially Paid"

    frappe.db.set_value("Subcontract Invoice", invoice_name, {
        "paid_amount": paid_amount,
        "status": status
    }, update_modified=False)

    work_order = frappe.db.get_value("Subcontract Invoice", invoice_name, "subcontract_work_order")
    if work_order:
        if paid_amount >= grand_total:
            wo_status = "Paid"
        elif paid_amount > 0:
            wo_status = "Partially Billed"
        else:
            wo_status = "Invoiced"
        frappe.db.set_value("Subcontract Work Order", work_order, "status", wo_status)


@frappe.whitelist()
def repost_date(invoice, new_date):
    invoice_doc = frappe.get_doc("Subcontract Invoice", invoice)

    if invoice_doc.docstatus != 1:
        frappe.throw("Can only repost date on submitted invoices")

    new_date = getdate(new_date)

    frappe.db.sql("""
        UPDATE `tabGL Entry`
        SET posting_date = %s
        WHERE voucher_type = 'Subcontract Invoice'
          AND voucher_no = %s
          AND is_cancelled = 0
    """, (new_date, invoice))

    frappe.db.set_value("Subcontract Invoice", invoice, "transaction_date", new_date, update_modified=False)

    frappe.db.commit()
    return str(new_date)