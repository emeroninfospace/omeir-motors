# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

# Overrides ERPNext's "Gross Profit" report (same report name, Omeir Motors module).
# Sublet items billed from a Job Order have no stock / purchase cost in ERPNext, so they
# showed 100% profit. Their buying amount is taken from the submitted Subcontract
# Invoices raised against the same Job Order; everything else is ERPNext's logic.

import frappe
from frappe.utils import flt

from erpnext.accounts.report.gross_profit import gross_profit as erpnext_gross_profit


def execute(filters=None):
    original_generator = erpnext_gross_profit.GrossProfitGenerator
    erpnext_gross_profit.GrossProfitGenerator = SubletGrossProfitGenerator
    try:
        return erpnext_gross_profit.execute(filters)
    finally:
        erpnext_gross_profit.GrossProfitGenerator = original_generator


class SubletGrossProfitGenerator(erpnext_gross_profit.GrossProfitGenerator):
    def load_invoice_items(self):
        super().load_invoice_items()
        self.load_sublet_rates()

    def load_sublet_rates(self):
        """{(sales_invoice, item_code): cost per unit} from Subcontract Invoices of the invoice's Job Order."""
        self.sublet_rates = {}
        invoices = list({row.parent for row in self.si_list if row.parent})
        if not invoices:
            return

        rows = frappe.db.sql("""
            SELECT si.name AS sales_invoice, sci.item_code,
                SUM(sci.amount) / SUM(sci.quantity) AS rate
            FROM `tabSales Invoice` si
            LEFT JOIN `tabSales Invoice` against_si ON against_si.name = si.return_against
            JOIN `tabSubcontract Invoice Item` sci
                ON sci.job_order = COALESCE(NULLIF(si.custom_job_order, ''), against_si.custom_job_order)
            JOIN `tabSubcontract Invoice` sc ON sc.name = sci.parent AND sc.docstatus = 1
            WHERE si.name IN %(invoices)s
            GROUP BY si.name, sci.item_code
            HAVING SUM(sci.quantity) != 0
        """, {"invoices": invoices}, as_dict=True)

        for row in rows:
            self.sublet_rates[(row.sales_invoice, row.item_code)] = flt(row.rate)

    def get_buying_amount(self, row, item_code):
        rate = self.sublet_rates.get((row.parent or row.get("invoice"), item_code))
        if rate is not None:
            return flt(row.qty) * rate

        return super().get_buying_amount(row, item_code)
