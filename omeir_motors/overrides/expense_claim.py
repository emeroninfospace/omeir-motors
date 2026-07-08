import frappe
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from frappe.utils import flt


class CustomExpenseClaim(ExpenseClaim):

    def calculate_total_amount(self):
        self.total_claimed_amount = 0
        self.total_sanctioned_amount = 0

        for d in self.get("expenses"):
            self.round_floats_in(d)

            d.custom_total_amount = flt(d.amount) + flt(d.custom_tax_amount)

            if self.approval_status == "Rejected":
                d.sanctioned_amount = 0.0
            else:
                d.sanctioned_amount = d.custom_total_amount

            self.total_claimed_amount += d.custom_total_amount
            self.total_sanctioned_amount += flt(d.sanctioned_amount)

        self.round_floats_in(self, ["total_claimed_amount", "total_sanctioned_amount"])

    def validate_sanctioned_amount(self):
        for d in self.get("expenses"):
            if flt(d.sanctioned_amount) > flt(d.custom_total_amount):
                frappe.throw(
                    frappe._("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx)
                )
