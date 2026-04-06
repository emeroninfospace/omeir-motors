# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils import getdate


class SubcontractInvoice(Document):

    def on_submit(self):
        self.make_gl_entries()

    def on_cancel(self):
        make_gl_entries([], cancel=1, voucher_type=self.doctype, voucher_no=self.name)

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

        gl_entries.append(frappe._dict({
		"account": payable_account,
		"credit": self.total_amount,
		"credit_in_account_currency": self.total_amount,
		"against": expense_account,
		"party_type": "Supplier",
		"party": self.supplier,
		"voucher_type": self.doctype,
		"voucher_no": self.name,
		"company": self.company,
		"posting_date": posting_date,
		"cost_center": self.cost_center,  
		"project": self.project
	}))

        make_gl_entries(gl_entries)
