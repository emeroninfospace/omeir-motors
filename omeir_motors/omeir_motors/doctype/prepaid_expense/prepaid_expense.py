# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months
from frappe import _


class PrepaidExpense(Document):
    def validate(self):
        self.validate_fields()
        self.calculate_monthly_amount()

    def validate_fields(self):
        if not self.type:
            frappe.throw("Please select Type (Expense or Rent)")
        if self.type == "Expense" and not self.employee:
            frappe.throw("Employee is required for Expense type")
        if not self.prepaid_account:
            frappe.throw("Please select Prepaid Account")
        if not self.expense_account:
            frappe.throw(_("Please select Expense Account"))
        if self.type == "Expense" and not self.payable_account:
            frappe.throw(_("Please select Payable Account"))
        if not self.number_of_months or self.number_of_months <= 0:
            frappe.throw("Number of Months must be greater than 0")
        if not self.start_date:
            frappe.throw("Please select Start Date")
        if not self.total_amount or self.total_amount <= 0:
            frappe.throw("Total Amount must be greater than 0")

    def calculate_monthly_amount(self):
        if self.total_amount and self.number_of_months:
            self.monthly_amount = flt(self.total_amount / self.number_of_months, 2)
            self.remaining_amount = flt(self.total_amount, 2)

    def on_submit(self):
        self.create_amortization_schedule()
        if self.type == "Expense":
            self.make_initial_gl_entry()
        self.db_set("status", "Active", update_modified=False)

    def on_cancel(self):
        self.cancel_pending_entries()
        self.db_set("status", "Draft", update_modified=False)

    def create_amortization_schedule(self):
        self.set("prepaid_expense_schedule", [])

        total_allocated = flt(0, 2)
        start = getdate(self.start_date)

        for i in range(self.number_of_months):
            schedule_date = add_months(start, i + 1)

            if i == self.number_of_months - 1:
                amount = flt(self.total_amount - total_allocated, 2)
            else:
                amount = flt(self.monthly_amount, 2)

            total_allocated = flt(total_allocated + amount, 2)

            self.append("prepaid_expense_schedule", {
                "schedule_date": schedule_date,
                "amount": amount,
                "status": "Pending",
                "journal_entry": None
            })

        self.save()

    def make_initial_gl_entry(self):
        cost_center = frappe.db.get_value("Company", self.company, "cost_center")
        posting_date = getdate(self.start_date)
        payable_account_type = frappe.db.get_value("Account", self.payable_account, "account_type")

        if self.type == "Expense":
            party_label = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
        else:
            party_label = self.expense_type or "Rent"

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = posting_date
        je.cheque_no = self.name
        je.cheque_date = posting_date
        je.remark = f"Prepaid {self.type} initial entry - {party_label}"

        debit_entry = {
            "account": self.payable_account,
            "debit_in_account_currency": flt(self.total_amount, 2),
            "cost_center": cost_center,
            "user_remark": f"Prepaid {self.type} - {party_label}"
        }

        if payable_account_type in ("Receivable", "Payable") and self.type == "Expense" and self.employee:
            debit_entry.update({
                "party_type": "Employee",
                "party": self.employee
            })

        je.append("accounts", debit_entry)

        je.append("accounts", {
            "account": self.prepaid_account,
            "credit_in_account_currency": flt(self.total_amount, 2),
            "cost_center": cost_center,
            "user_remark": f"Prepaid {self.type} - {party_label}"
        })

        je.insert(ignore_permissions=True)
        je.submit()

        self.db_set("initial_journal_entry", je.name, update_modified=False)

    def cancel_pending_entries(self):
        if self.type == "Expense" and self.initial_journal_entry:
            je = frappe.get_doc("Journal Entry", self.initial_journal_entry)
            if je.docstatus == 1:
                je.cancel()

        for row in self.prepaid_expense_schedule:
            if row.status == "Pending":
                frappe.db.set_value("Prepaid Expense Schedule", row.name, "status", "Cancelled")


@frappe.whitelist()
def close_prepaid_expense(name):
    doc = frappe.get_doc("Prepaid Expense", name)

    if doc.docstatus != 1:
        frappe.throw("Only submitted records can be closed")

    if doc.status == "Completed":
        frappe.throw("This record is already completed")

    remaining = flt(doc.remaining_amount, 2)

    if remaining <= 0:
        frappe.throw("No remaining amount to close")

    cost_center = frappe.db.get_value("Company", doc.company, "cost_center")

    if doc.type == "Expense":
        party_label = frappe.db.get_value("Employee", doc.employee, "employee_name") or doc.employee
    else:
        party_label = doc.expense_type or "Rent"

    payable_account_type = frappe.db.get_value("Account", doc.payable_account, "account_type")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    je.posting_date = frappe.utils.today()
    je.cheque_no = doc.name
    je.cheque_date = frappe.utils.today()
    je.remark = f"Closing prepaid {doc.type} - {party_label}"

    je.append("accounts", {
        "account": doc.expense_account,
        "debit_in_account_currency": remaining,
        "cost_center": cost_center,
        "user_remark": f"Write-off remaining: {doc.expense_type or ''} - {party_label}"
    })

    credit_entry = {
        "account": doc.payable_account,
        "credit_in_account_currency": remaining,
        "cost_center": cost_center,
        "user_remark": f"Write-off remaining: {doc.expense_type or ''} - {party_label}"
    }

    if payable_account_type in ("Receivable", "Payable") and doc.type == "Expense" and doc.employee:
        credit_entry.update({
            "party_type": "Employee",
            "party": doc.employee
        })

    je.append("accounts", credit_entry)
    je.insert(ignore_permissions=True)
    je.submit()

    for row in doc.prepaid_expense_schedule:
        if row.status == "Pending":
            frappe.db.set_value("Prepaid Expense Schedule", row.name, "status", "Cancelled")

    frappe.db.set_value("Prepaid Expense", name, {
        "remaining_amount": 0,
        "status": "Completed",
        "close_journal_entry": je.name
    })

    return je.name


@frappe.whitelist()
def post_scheduled_amortization():
    today = getdate(frappe.utils.today())

    pending_rows = frappe.db.sql("""
        SELECT
            pes.name as schedule_name,
            pes.schedule_date,
            pes.amount,
            pe.name as parent,
            pe.employee,
            pe.type,
            pe.expense_type,
            pe.prepaid_account,
            pe.expense_account,
            pe.payable_account,
            pe.company
        FROM `tabPrepaid Expense Schedule` pes
        JOIN `tabPrepaid Expense` pe ON pe.name = pes.parent
        WHERE pes.status = 'Pending'
        AND pes.schedule_date <= %s
        AND pe.docstatus = 1
        AND pe.status = 'Active'
    """, today, as_dict=True)

    if not pending_rows:
        return

    for row in pending_rows:
        try:
            cost_center = frappe.db.get_value("Company", row.company, "cost_center")
            payable_account_type = frappe.db.get_value("Account", row.payable_account, "account_type")

            if row.type == "Expense" and row.employee:
                party_label = frappe.db.get_value("Employee", row.employee, "employee_name") or row.employee
            else:
                party_label = row.expense_type or "Rent"

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company = row.company
            je.posting_date = row.schedule_date
            je.cheque_no = row.parent
            je.cheque_date = row.schedule_date
            je.remark = f"Monthly amortization for {row.expense_type or ''} - {party_label}"

            je.append("accounts", {
                "account": row.expense_account,
                "debit_in_account_currency": flt(row.amount, 2),
                "cost_center": cost_center,
                "user_remark": f"{row.expense_type or ''} - {party_label}"
            })

            if row.type == "Rent":
                credit_entry = {
                    "account": row.prepaid_account,
                    "credit_in_account_currency": flt(row.amount, 2),
                    "cost_center": cost_center,
                    "user_remark": f"{row.expense_type or ''} - {party_label}"
                }
            else:
                credit_entry = {
                    "account": row.payable_account,
                    "credit_in_account_currency": flt(row.amount, 2),
                    "cost_center": cost_center,
                    "user_remark": f"{row.expense_type or ''} - {party_label}"
                }
                if payable_account_type in ("Receivable", "Payable") and row.employee:
                    credit_entry.update({
                        "party_type": "Employee",
                        "party": row.employee
                    })

            je.append("accounts", credit_entry)
            je.insert(ignore_permissions=True)
            je.submit()

            frappe.db.set_value("Prepaid Expense Schedule", row.schedule_name, {
                "status": "Posted",
                "journal_entry": je.name
            })

            remaining = flt(frappe.db.get_value("Prepaid Expense", row.parent, "remaining_amount") or 0, 2)
            new_remaining = flt(remaining - row.amount, 2)
            frappe.db.set_value("Prepaid Expense", row.parent, "remaining_amount", new_remaining)

            if new_remaining <= 0:
                frappe.db.set_value("Prepaid Expense", row.parent, "status", "Completed")

            frappe.db.commit()

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Prepaid Expense Amortization Failed: {row.parent}")
            frappe.db.rollback()