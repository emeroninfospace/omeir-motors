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
            item.amount = flt(item.amount, item.precision("amount"))
            item.vat_amount = flt(
                item.amount * flt(item.vat_percentage) / 100, item.precision("vat_amount")
            )
            item.total_amount = flt(item.amount + item.vat_amount, item.precision("total_amount"))

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

    def validate_can_make_payment(self):
        if self.docstatus != 1:
            frappe.throw(_("Expense Entry {0} is not submitted.").format(self.name))

        if self.journal_entry:
            frappe.throw(_("Expense Entry {0} already has a Journal Entry.").format(self.name))

        if self.status == "Paid":
            frappe.throw(_("Expense Entry {0} is already Paid.").format(self.name))

        for row in self.items:
            missing = []
            if not row.account:
                missing.append(_("Account To"))
            if not row.account_from:
                missing.append(_("Account From"))
            if flt(row.vat_amount) > 0 and not row.tax_account:
                missing.append(_("Tax Account"))

            if missing:
                frappe.throw(
                    _("Row {0}: {1} is required to make the payment.").format(row.idx, ", ".join(missing))
                )

    @frappe.whitelist()
    def make_journal_entry(self):
        self.validate_can_make_payment()

        je = frappe.new_doc("Journal Entry")
        je.update(
            {
                "voucher_type": "Journal Entry",
                "company": self.company,
                "posting_date": self.posting_date,
                "user_remark": _("Journal Entry for Expense Entry {0}").format(self.name),
            }
        )

        for row in self.items:
            amount = flt(row.amount, 2)
            vat_amount = flt(row.vat_amount, 2)

            # Expense debit
            je.append(
                "accounts",
                {
                    "account": row.account,
                    "debit_in_account_currency": amount,
                    "user_remark": row.narration,
                    "voucher_no": row.voucher_no,
                    "trn": row.trn,
                    "custom_supplier_name": row.supplier_name,
                    "project": row.project,
                },
            )

            # VAT debit
            if vat_amount > 0:
                je.append(
                    "accounts",
                    {
                        "account": row.tax_account,
                        "debit_in_account_currency": vat_amount,
                        "project": row.project,
                    },
                )

            je.append(
                "accounts",
                {
                    "account": row.account_from,
                    "credit_in_account_currency": flt(amount + vat_amount, 2),
                },
            )

        je.flags.ignore_permissions = True
        je.insert()
        je.submit()

        self.db_set({"journal_entry": je.name, "status": "Paid"}, update_modified=False)
        return je.name


@frappe.whitelist()
def make_payment_for_expense_entry(name):
    doc = frappe.get_doc("Expense Entry", name)
    doc.check_permission("submit")
    return doc.make_journal_entry()


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