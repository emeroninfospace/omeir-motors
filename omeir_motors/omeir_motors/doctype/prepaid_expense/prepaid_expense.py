# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months, get_first_day


class PrepaidExpense(Document):
    def validate(self):
        self.validate_fields()
        self.calculate_monthly_amount()

    def validate_fields(self):
        if not self.prepaid_account:
            frappe.throw("Please select Prepaid Account")
        if not self.expense_account:
            frappe.throw("Please select Expense Account")
        if not self.payable_account:
            frappe.throw("Please select Payable Account")
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
            schedule_date = get_first_day(add_months(start, i))

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
        from erpnext.accounts.general_ledger import make_gl_entries

        cost_center = frappe.db.get_value("Company", self.company, "cost_center")
        employee_name = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
        posting_date = getdate(self.start_date)
        remarks = f"Prepaid expense for {self.expense_type or ''} - {employee_name}"

        payable_account_type = frappe.db.get_value("Account", self.payable_account, "account_type")
        prepaid_account_type = frappe.db.get_value("Account", self.prepaid_account, "account_type")

        gl_entries = []

        debit_entry = frappe._dict({
            "account": self.prepaid_account,
            "debit": flt(self.total_amount, 2),
            "debit_in_account_currency": flt(self.total_amount, 2),
            "against": self.payable_account,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "company": self.company,
            "posting_date": posting_date,
            "cost_center": cost_center,
            "remarks": remarks
        })

        if prepaid_account_type in ("Receivable", "Payable"):
            debit_entry.update({
                "party_type": "Employee",
                "party": self.employee
            })

        gl_entries.append(debit_entry)

        credit_entry = frappe._dict({
            "account": self.payable_account,
            "credit": flt(self.total_amount, 2),
            "credit_in_account_currency": flt(self.total_amount, 2),
            "against": self.prepaid_account,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "company": self.company,
            "posting_date": posting_date,
            "cost_center": cost_center,
            "remarks": remarks
        })

        if payable_account_type in ("Receivable", "Payable"):
            credit_entry.update({
                "party_type": "Employee",
                "party": self.employee
            })

        gl_entries.append(credit_entry)
        make_gl_entries(gl_entries)

    def cancel_pending_entries(self):
        from erpnext.accounts.general_ledger import make_reverse_gl_entries
        make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

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
    employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name") or doc.employee

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    je.posting_date = frappe.utils.today()
    je.cheque_no = doc.name
    je.cheque_date = frappe.utils.today()
    je.remark = f"Closing prepaid expense for {doc.expense_type or ''} - {employee_name}"

    prepaid_account_type = frappe.db.get_value("Account", doc.prepaid_account, "account_type")

    debit_entry = {
        "account": doc.expense_account,
        "debit_in_account_currency": remaining,
        "cost_center": cost_center,
        "user_remark": f"Write-off remaining prepaid: {doc.expense_type or ''} - {employee_name}"
    }
    je.append("accounts", debit_entry)

    credit_entry = {
        "account": doc.prepaid_account,
        "credit_in_account_currency": remaining,
        "cost_center": cost_center,
        "user_remark": f"Write-off remaining prepaid: {doc.expense_type or ''} - {employee_name}"
    }

    if prepaid_account_type in ("Receivable", "Payable"):
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
        "status": "Completed"
    })

    return je.name


@frappe.whitelist()
def post_monthly_amortization():
    today = getdate(frappe.utils.today())

    pending_rows = frappe.db.sql("""
        SELECT
            pes.name as schedule_name,
            pes.schedule_date,
            pes.amount,
            pe.name as parent,
            pe.employee,
            pe.expense_type,
            pe.prepaid_account,
            pe.expense_account,
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
            employee_name = frappe.db.get_value("Employee", row.employee, "employee_name") or row.employee
            cost_center = frappe.db.get_value("Company", row.company, "cost_center")
            prepaid_account_type = frappe.db.get_value("Account", row.prepaid_account, "account_type")

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company = row.company
            je.posting_date = row.schedule_date
            je.cheque_no = row.parent
            je.cheque_date = row.schedule_date
            je.remark = f"Monthly amortization for {row.expense_type or ''} - {employee_name}"

            je.append("accounts", {
                "account": row.expense_account,
                "debit_in_account_currency": flt(row.amount, 2),
                "cost_center": cost_center,
                "user_remark": f"{row.expense_type or ''} - {employee_name}"
            })

            credit_entry = {
                "account": row.prepaid_account,
                "credit_in_account_currency": flt(row.amount, 2),
                "cost_center": cost_center,
                "user_remark": f"{row.expense_type or ''} - {employee_name}"
            }

            if prepaid_account_type in ("Receivable", "Payable"):
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