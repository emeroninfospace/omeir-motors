# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

# Overrides ERPNext's "Gross Profit" report (same report name, Omeir Motors module).
# Sublet items billed from a Job Order have no stock / purchase cost in ERPNext, so they
# showed 100% profit. Their buying amount is taken from the submitted Subcontract
# Invoices raised against the same Job Order, also shown in a separate "Subcontract Cost"
# column; everything else is ERPNext's logic.

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.gross_profit import gross_profit as erpnext_gross_profit


def execute(filters=None):
    generators = []

    def make_generator(*args, **kwargs):
        generators.append(SubletGrossProfitGenerator(*args, **kwargs))
        return generators[-1]

    original_generator = erpnext_gross_profit.GrossProfitGenerator
    erpnext_gross_profit.GrossProfitGenerator = make_generator
    try:
        columns, data = erpnext_gross_profit.execute(filters)
    finally:
        erpnext_gross_profit.GrossProfitGenerator = original_generator

    add_subcontract_cost_column(columns, data, generators[0])
    return columns, data


def add_subcontract_cost_column(columns, data, generator):
    fieldnames = [col.get("fieldname") for col in columns]
    if "buying_amount" not in fieldnames:
        return

    idx = fieldnames.index("buying_amount") + 1
    columns.insert(idx, {
        "label": _("Subcontract Cost"),
        "fieldname": "subcontract_cost",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 120,
    })

    if generator.filters.get("group_by") == "Invoice":
        # data = one dict per si_list row + a total row
        for src, row in zip(generator.si_list, data[:-1], strict=False):
            row["subcontract_cost"] = src.get("subcontract_cost")
        data[-1]["subcontract_cost"] = sum(
            flt(src.subcontract_cost) for src in generator.si_list if src.indent == 1
        )
    else:
        # data = one list per grouped_data row (same order as columns) + a total row
        for src, row in zip(generator.grouped_data, data[:-1], strict=False):
            row.insert(idx, src.get("subcontract_cost"))
        data[-1].insert(idx, sum(flt(src.get("subcontract_cost")) for src in generator.grouped_data))


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
            row.sublet_rate = rate
            return flt(row.qty) * rate

        return super().get_buying_amount(row, item_code)

    def get_average_rate_based_on_group_by(self):
        # runs after buying amounts / returns are settled on each row, before rows are aggregated
        self.subcontract_cost_totals = {}
        for rows in self.grouped.values():
            for row in rows:
                row.subcontract_cost = flt(flt(row.qty) * flt(row.get("sublet_rate")), self.currency_precision)

        group_by = self.filters.get("group_by")
        if group_by == "Invoice":
            header = None
            for row in self.si_list:
                if row.indent == 0:
                    header = row
                    header.subcontract_cost = 0.0
                elif row.indent == 1 and header:
                    header.subcontract_cost += row.subcontract_cost or 0.0
        elif group_by != "Payment Term":
            self.subcontract_cost_totals = {
                id(rows[0]): sum(row.subcontract_cost for row in rows) for rows in self.grouped.values()
            }

        super().get_average_rate_based_on_group_by()

    def set_average_rate(self, new_row):
        if id(new_row) in self.subcontract_cost_totals:
            new_row.subcontract_cost = flt(self.subcontract_cost_totals[id(new_row)], self.currency_precision)
        return super().set_average_rate(new_row)

    def set_average_based_on_payment_term_portion(self, new_row, row, invoice_portion, aggr=False):
        portion_cost = flt(row.get("subcontract_cost")) * invoice_portion / 100
        super().set_average_based_on_payment_term_portion(new_row, row, invoice_portion, aggr)
        new_row.subcontract_cost = (flt(new_row.get("subcontract_cost")) + portion_cost) if aggr else portion_cost
