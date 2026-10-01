"""Extend the standard v15 calculation before its grouping/return processing.

The standard report's execute function gets a private globals dictionary, so no
process-wide monkey-patching leaks between requests or sites. ERPNext owns all
columns, filters, grouping, return adjustments and final margin calculations.
"""

from types import FunctionType

import frappe
from erpnext.accounts.report.gross_profit import gross_profit as standard
from frappe.utils import flt

from omeir_motors.profitability.allocation import MappingError, allocated_cost
from omeir_motors.profitability.mapping import SOURCE_FIELD, job_context, stock_quantity
from omeir_motors.profitability.setup import SALES_FIELD


class SubcontractGrossProfitGenerator(standard.GrossProfitGenerator):
	def load_invoice_items(self):
		super().load_invoice_items()
		self.subcontract_rates = {}
		invoice_docs = {}
		for row in self.si_list:
			if not row.item_row or row.parenttype != "Sales Invoice":
				continue
			if row.parent not in invoice_docs:
				invoice_docs[row.parent] = frappe.get_doc("Sales Invoice", row.parent)
			invoice = invoice_docs[row.parent]
			if not invoice.get("custom_job_order"):
				continue
			item = next((i for i in invoice.items if i.name == row.item_row), None)
			if not item or frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
				continue
			target = item.get(SALES_FIELD)
			if not target:
				job = job_context(invoice.custom_job_order, invoice.company)
				if any(r.item_code == item.item_code for r in job.sublet_details):
					frappe.throw(
						f"{invoice.name}, row {item.idx}: missing sublet cost link. Run the backfill and resolve review rows."
					)
				continue
			try:
				if item.get("delivered_by_supplier") or frappe.db.exists("Product Bundle", item.item_code):
					raise MappingError("Subcontract links do not support drop shipping or Product Bundles.")
				job = job_context(invoice.custom_job_order, invoice.company)
				sublet = next(
					(r for r in job.sublet_details if r.name == target and r.item_code == item.item_code),
					None,
				)
				if not sublet:
					raise MappingError("Sublet link does not match the invoice Job Order and item.")
				if target not in self.subcontract_rates:
					self.subcontract_rates[target] = self.cost_rate(job, sublet)
				row.omeir_subcontract_rate = self.subcontract_rates[target]
			except MappingError as exc:
				frappe.throw(f"{invoice.name}, row {item.idx}: {exc}")

	def cost_rate(self, job, sublet):
		planned = stock_quantity(sublet)
		rows = frappe.db.sql(
			"""
            SELECT sci.name, sci.amount, sci.job_order_sublet_row, sc.name AS invoice
            FROM `tabSubcontract Invoice Item` sci
            JOIN `tabSubcontract Invoice` sc ON sc.name=sci.parent
            WHERE sc.docstatus=1 AND sc.company=%s AND sci.job_order=%s
              AND sci.item_code=%s AND sc.transaction_date<=%s
        """,
			(job.company, job.name, sublet.item_code, self.filters.to_date),
			as_dict=True,
		)
		valid_targets = {r.name for r in job.sublet_details if r.item_code == sublet.item_code}
		for source in rows:
			if source.get(SOURCE_FIELD) not in valid_targets:
				raise MappingError(
					f"Subcontract Invoice {source.invoice}, row {source.name}: unresolved cost link."
				)
			if flt(source.amount) < 0:
				raise MappingError(f"Subcontract Invoice {source.invoice}: negative cost needs review.")
		cost = sum(flt(r.amount) for r in rows if r.get(SOURCE_FIELD) == sublet.name)
		# Detect historical duplicate/full billing as well as the live submit check.
		used = frappe.db.sql(
			"""
            SELECT COALESCE(SUM(sii.stock_qty), 0)
            FROM `tabSales Invoice Item` sii JOIN `tabSales Invoice` si ON si.name=sii.parent
            WHERE si.docstatus=1 AND sii.custom_job_order_sublet_row=%s
        """,
			sublet.name,
		)[0][0]
		if flt(used) > planned + 0.000001 or flt(used) < -0.000001:
			raise MappingError(
				"Total invoiced quantity for the sublet row is outside the Job Order quantity; review the allocation."
			)
		return allocated_cost(cost, planned, 1)

	def update_return_invoices(self, row, sales_invoice_item):
		super().update_return_invoices(row, sales_invoice_item)
		if row.get("omeir_subcontract_rate") is not None:
			# Preserve full allocation precision; standard buying_rate is display-rounded.
			row.buying_amount = flt(flt(row.qty) * row.omeir_subcontract_rate, self.currency_precision)

	def get_buying_amount(self, row, item_code):
		if row.get("omeir_subcontract_rate") is not None and item_code == row.item_code:
			return flt(row.qty) * row.omeir_subcontract_rate
		return super().get_buying_amount(row, item_code)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company") or not filters.get("to_date"):
		frappe.throw("Company and To Date are required for subcontract profitability.")
	report_globals = dict(standard.execute.__globals__)
	report_globals["GrossProfitGenerator"] = SubcontractGrossProfitGenerator
	execute_standard = FunctionType(
		standard.execute.__code__,
		report_globals,
		standard.execute.__name__,
		standard.execute.__defaults__,
		standard.execute.__closure__,
	)
	return execute_standard(filters)
