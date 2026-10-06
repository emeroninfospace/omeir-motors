# Copyright (c) 2026, emeron and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ExpenseEntry(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        self.total_amount = 0
        self.total_vat = 0

        for item in self.items:
            item.amount = flt(item.amount)

            if item.amount and item.vat_percentage:
                item.vat_amount = flt(item.amount * item.vat_percentage / 100)
            else:
                item.vat_amount = item.vat_amount

            item.total_amount = flt(item.amount) + flt(item.vat_amount)

            self.total_amount += item.amount
            self.total_vat += item.vat_amount

        self.total_amount = flt(self.total_amount, self.precision("total_amount"))
        self.total_vat = flt(self.total_vat, self.precision("total_vat"))
        self.grand_total = flt(self.total_amount + self.total_vat, self.precision("grand_total"))

    def before_submit(self):
        # Saved together with the submit, no extra DB write needed
        self.status = "Unpaid"

    def on_cancel(self):
        # Cancelling the Expense Entry also cancels its payment Journal Entry
        if self.journal_entry and frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            je.flags.ignore_permissions = True
            je.cancel()

        self.db_set({"status": "", "journal_entry": None}, update_modified=False)

    @frappe.whitelist()
    def make_journal_entry(self, payment_date=None, remark=None):
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = payment_date or self.posting_date
        je.remark = _combine_remark(f"Journal Entry for Expense Entry {self.name}", remark)

        total_debit = _build_journal_entry_lines(je, [self])
        _adjust_rounding(je, total_debit)

        je.insert(ignore_permissions=True)
        je.submit()

        self.db_set("journal_entry", je.name, update_modified=False)
        self.db_set("status", "Paid", update_modified=False)

        return je.name


def _combine_remark(base, remark):
    """Always keep the Expense Entry id(s) in the JV remark, appending any user-entered text."""
    return f"{base} - {remark}" if remark else base


def _validate_expense_entry_for_payment(entry):
    """Validate an Expense Entry (full doc or a dict/frappe._dict with the same fields)."""
    if entry.docstatus != 1:
        frappe.throw(_("Expense Entry {0} is not submitted.").format(entry.name))

    if entry.status == "Paid":
        frappe.throw(_("Expense Entry {0} is already Paid.").format(entry.name))

    if entry.journal_entry:
        frappe.throw(_("Expense Entry {0} already has a Journal Entry.").format(entry.name))


def _build_journal_entry_lines(je, docs):
    """Append expense/VAT debit lines and consolidated 'Paid From' credit lines to a Journal Entry.

    Walks each Expense Entry's items exactly once, appending debit rows as it goes while
    accumulating credit totals per Paid From account, then appends one credit row per account.
    Returns the total debit amount added.
    """
    total_debit = 0
    credit_by_account = {}

    for doc in docs:
        for row in doc.items:
            debit_amount = flt(row.amount, 2)
            vat_amount = flt(row.vat_amount or 0, 2)

            je.append("accounts", {
                "account": row.account,
                "debit_in_account_currency": debit_amount,
                "user_remark": row.narration,
                "voucher_no": row.voucher_no,
                "trn": row.trn,
                "custom_supplier_name": row.supplier_name,
                "project": row.project,
                "cost_center": row.cost_center
            })
            total_debit += debit_amount

            if vat_amount > 0:
                je.append("accounts", {
                    "account": "VAT 5% - BOMC",
                    "debit_in_account_currency": vat_amount
                })
                total_debit += vat_amount

            credit_by_account[row.account_from] = flt(
                credit_by_account.get(row.account_from, 0) + debit_amount + vat_amount, 2
            )

    for account_from, credit_amount in credit_by_account.items():
        je.append("accounts", {
            "account": account_from,
            "credit_in_account_currency": credit_amount
        })

    return flt(total_debit, 2)


def _adjust_rounding(je, total_debit):
    """Fix sub-cent rounding difference by adjusting the last credit row."""
    total_credit = flt(sum(flt(row.credit_in_account_currency) for row in je.accounts), 2)
    difference = flt(total_debit - total_credit, 2)

    if difference != 0:
        credit_rows = [row for row in je.accounts if row.credit_in_account_currency]
        if credit_rows:
            credit_rows[-1].credit_in_account_currency = flt(
                credit_rows[-1].credit_in_account_currency + difference, 2
            )


@frappe.whitelist()
def make_payment_for_expense_entry(name, payment_date=None, remark=None):
    doc = frappe.get_doc("Expense Entry", name)
    _validate_expense_entry_for_payment(doc)
    return doc.make_journal_entry(payment_date=payment_date, remark=remark)


@frappe.whitelist()
def make_payment_for_expense_entries(names, payment_date=None, remark=None):
    """Create a separate Journal Entry for each given Expense Entry in one request.

    Each entry is committed independently so one failure doesn't roll back the rest.
    Returns a list of {name, success, journal_entry} results for the caller to summarize.
    """
    if isinstance(names, str):
        names = frappe.parse_json(names)

    results = []
    for name in names:
        try:
            doc = frappe.get_doc("Expense Entry", name)
            _validate_expense_entry_for_payment(doc)
            je_name = doc.make_journal_entry(payment_date=payment_date, remark=remark)
            frappe.db.commit()
            results.append({"name": name, "success": True, "journal_entry": je_name})
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Make Payment failed for Expense Entry {name}")
            results.append({"name": name, "success": False})

    return results


@frappe.whitelist()
def make_consolidated_journal_entry(names, posting_date=None, remark=None):
    """Create a single Journal Entry covering multiple Expense Entries.

    All selected Expense Entries must share the same 'Paid From' account
    (account_from) on their line items, since they will be consolidated
    into a single credit line. Validation runs against lightweight queries
    first so a bad selection fails without loading every full document.
    """
    if isinstance(names, str):
        names = frappe.parse_json(names)

    if not names:
        frappe.throw(_("Please select at least one Expense Entry to consolidate."))

    entries = frappe.get_all(
        "Expense Entry",
        filters={"name": ["in", names]},
        fields=["name", "company", "status", "docstatus", "journal_entry"],
    )

    if len(entries) != len(names):
        frappe.throw(_("One or more selected Expense Entries could not be found."))

    for entry in entries:
        _validate_expense_entry_for_payment(entry)

    company_set = {entry.company for entry in entries}
    if len(company_set) > 1:
        frappe.throw(_("All selected Expense Entries must belong to the same Company to consolidate."))

    item_rows = frappe.get_all(
        "Expense Entry Item",
        filters={"parent": ["in", names]},
        fields=["parent", "account_from"],
    )

    for row in item_rows:
        if not row.account_from:
            frappe.throw(_("Expense Entry {0} has a row missing the 'Paid From' account.").format(row.parent))

    account_from_set = {row.account_from for row in item_rows}
    if len(account_from_set) > 1:
        frappe.throw(_(
            "Cannot consolidate: selected Expense Entries use different 'Paid From' accounts ({0}). "
            "All selected entries must use the same account to create a consolidated Journal Entry."
        ).format(", ".join(sorted(account_from_set))))

    docs = [frappe.get_doc("Expense Entry", entry.name) for entry in entries]

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = company_set.pop()
    je.posting_date = posting_date or nowdate()
    je.remark = _combine_remark(
        _("Consolidated Journal Entry for Expense Entries: {0}").format(", ".join(names)), remark
    )

    total_debit = _build_journal_entry_lines(je, docs)
    _adjust_rounding(je, total_debit)

    je.insert(ignore_permissions=True)
    je.submit()

    for doc in docs:
        doc.db_set("journal_entry", je.name, update_modified=False)
        doc.db_set("status", "Paid", update_modified=False)

    return je.name
  
  
def unlink_journal_entry(doc, method=None):
  
    expense_entries = frappe.get_all(
        "Expense Entry",
        filters={"journal_entry": doc.name, "docstatus": 1},
        pluck="name",
    )

    for name in expense_entries:
        frappe.db.set_value(
            "Expense Entry",
            name,
            {"journal_entry": None, "status": "Unpaid"},
            update_modified=False,
        )

    if expense_entries:
        frappe.msgprint(
            _("Unlinked from Expense Entry {0} and set it to Unpaid.").format(", ".join(expense_entries)),
            alert=True,
            indicator="orange",
        )
