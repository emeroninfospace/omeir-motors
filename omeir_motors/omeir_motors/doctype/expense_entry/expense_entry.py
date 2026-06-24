# Copyright (c) 2026, emeron and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


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

        self.grand_total = self.total_amount + self.total_vat

    def on_submit(self):
        # Set status to Unpaid when document is submitted
        self.db_set("status", "Unpaid", update_modified=False)

    def on_cancel(self):
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                
                je.cancel()
        
        # Reset status to Draft when cancelled
        self.db_set("status", "", update_modified=False)
        self.db_set("journal_entry", "", update_modified=False)

    from frappe.utils import flt

    @frappe.whitelist()
    def make_journal_entry(self, payment_date=None):
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = payment_date or self.posting_date
        je.remark = f"Journal Entry for Expense Entry {self.name}"

        total_debit = 0
        total_credit = 0

        for row in self.items:
            debit_amount = flt(row.amount, 2)
            vat_amount = flt(row.vat_amount or 0, 2)
            credit_amount = flt(debit_amount + vat_amount, 2)

            # Expense Debit
            je.append("accounts", {
                "account": row.account,
                "debit_in_account_currency": debit_amount,
                "user_remark": row.narration,
                "voucher_no": row.voucher_no,
                "trn": row.trn,
                "custom_supplier_name": row.supplier_name,
                "project": row.project
            })
            total_debit += debit_amount

            # VAT Debit
            if vat_amount > 0:
                je.append("accounts", {
                    "account": "VAT 5% - BOMC",
                    "debit_in_account_currency": vat_amount
                })
                total_debit += vat_amount

            # Credit Entry
            je.append("accounts", {
                "account": row.account_from,
                "credit_in_account_currency": credit_amount
            })
            total_credit += credit_amount

        # 🔥 FINAL ADJUSTMENT (fix 0.01 issue)
        difference = flt(total_debit - total_credit, 2)

        if difference != 0:
            # Adjust last credit row
            je.accounts[-1].credit_in_account_currency = flt(
                je.accounts[-1].credit_in_account_currency + difference, 2
            )

        je.insert(ignore_permissions=True)
        je.submit()

        self.db_set("journal_entry", je.name, update_modified=False)
        self.db_set("status", "Paid", update_modified=False)

        return je.name


@frappe.whitelist()
def make_payment_for_expense_entry(name, payment_date=None):
    doc = frappe.get_doc("Expense Entry", name)

    if doc.docstatus != 1:
        frappe.throw(_("Expense Entry {0} is not submitted.").format(name))

    if doc.status == "Paid":
        frappe.throw(_("Expense Entry {0} is already Paid.").format(name))

    if doc.journal_entry:
        frappe.throw(_("Expense Entry {0} already has a Journal Entry.").format(name))

    return doc.make_journal_entry(payment_date=payment_date)