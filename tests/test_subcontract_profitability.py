import copy
import unittest
from unittest.mock import Mock, patch

from support import Doc, Row, frappe, standard

from omeir_motors.profitability import audit, backfill, mapping
from omeir_motors.profitability.allocation import MappingError, allocated_cost, resolve_sublet
from omeir_motors.profitability.gross_profit import SubcontractGrossProfitGenerator


class AllocationTests(unittest.TestCase):
	def test_requested_example(self):
		cost = allocated_cost(1000, 1, 1)
		self.assertEqual(1500 - cost, 500)
		self.assertEqual(round((1500 - cost) / 1500 * 100, 2), 33.33)

	def test_different_jobs_same_item_and_partial_billing(self):
		self.assertEqual(allocated_cost(1000, 10, 4), 400)
		self.assertEqual(allocated_cost(1000, 10, 6), 600)
		self.assertEqual(allocated_cost(700, 10, 4), 280)
		self.assertEqual(allocated_cost(1000, 10, -4), -400)

	def test_invalid_values(self):
		for args in ((100, 0, 1), (-1, 1, 1), (float("nan"), 1, 1)):
			with self.assertRaises(MappingError):
				allocated_cost(*args)

	def test_ambiguous_item_needs_explicit_row(self):
		rows = [Row(name="A", item_code="S"), Row(name="B", item_code="S")]
		with self.assertRaises(MappingError):
			resolve_sublet("S", None, rows)
		self.assertEqual(resolve_sublet("S", "B", rows)["name"], "B")
		with self.assertRaises(MappingError):
			resolve_sublet("S", "WRONG", rows)

	def test_document_row_inferred_match(self):
		row = Doc(name="SUB1", item_code="SERVICE")
		self.assertIs(resolve_sublet("SERVICE", None, [row]), row)

	def test_document_row_explicit_match(self):
		rows = [Doc(name="SUB1", item_code="SERVICE"), Doc(name="SUB2", item_code="SERVICE")]
		self.assertIs(resolve_sublet("SERVICE", "SUB2", rows), rows[1])

	def test_document_rows_reject_ambiguous_or_mismatched_links(self):
		rows = [Doc(name="SUB1", item_code="SERVICE"), Doc(name="SUB2", item_code="SERVICE")]
		for item_code, explicit in (("SERVICE", None), ("SERVICE", "MISSING"), ("OTHER", "SUB1")):
			with self.subTest(item_code=item_code, explicit=explicit), self.assertRaises(MappingError):
				resolve_sublet(item_code, explicit, rows)

	def test_service_and_sublet_collision(self):
		with self.assertRaises(MappingError):
			resolve_sublet("S", None, [Row(name="A", item_code="S")], ["S"])


class MappingTests(unittest.TestCase):
	def setUp(self):
		frappe.db.reset_mock()
		frappe.db.exists.return_value = False
		frappe.get_cached_value.return_value = 0
		self.sublet = Doc(name="SUB1", item_code="SERVICE", quantity=1, uom="Nos")
		self.job = Doc(
			name="JOB1",
			company="C",
			docstatus=1,
			sublet_details=[self.sublet],
			service_item=[],
			job_order_items=[],
		)
		self.source = Doc(
			name="SCI1",
			doctype="Subcontract Invoice Item",
			idx=1,
			item_code="SERVICE",
			quantity=1,
			amount=1000,
			job_order="JOB1",
		)
		self.sale = Doc(
			name="SII1", doctype="Sales Invoice Item", idx=1, item_code="SERVICE", qty=1, stock_qty=1
		)
		self.invoice = Doc(name="SI1", company="C", docstatus=1, custom_job_order="JOB1", items=[self.sale])
		self.cost_doc = Doc(name="SC1", company="C", items=[self.source])
		self.docs = {
			("Job Order", "JOB1"): self.job,
			("Sublet Items", "SUB1"): self.sublet,
			("Sales Invoice", "SI1"): self.invoice,
			("Subcontract Invoice", "SC1"): self.cost_doc,
		}
		frappe.get_doc.side_effect = lambda dt, name: self.docs[(dt, name)]

	def repeated_rows(self):
		self.job.sublet_details = []
		self.invoice.items = []
		self.cost_doc.items = []
		for index, (description, qty, cost, sell) in enumerate(
			[("Outer seal", 1, 10, 15), ("Inner seal", 1, 20, 35), ("Support pin", 2, 30, 45)], 1
		):
			self.job.sublet_details.append(
				Doc(
					name=f"SUB{index}",
					item_code="SERVICE",
					description=f"<p>{description} &nbsp;</p>",
					quantity=qty,
					rate=cost,
					margin_rate=sell,
					uom="Nos",
				)
			)
			self.invoice.items.append(
				Doc(
					name=f"SII{index}",
					idx=index,
					doctype="Sales Invoice Item",
					item_code="SERVICE",
					description=description.upper(),
					qty=qty,
					stock_qty=qty,
					rate=sell,
					base_rate=sell,
					uom="Nos",
				)
			)
			self.cost_doc.items.append(
				Doc(
					name=f"SCI{index}",
					idx=index,
					doctype="Subcontract Invoice Item",
					item_code="SERVICE",
					description=description,
					quantity=qty,
					rate=cost,
					amount=qty * cost,
					job_order="JOB1",
				)
			)

	def test_repeated_sales_match_distinct_descriptions(self):
		self.repeated_rows()
		for index, row in enumerate(self.invoice.items, 1):
			self.assertEqual(mapping.resolve_sale(self.invoice, row), f"SUB{index}")

	def test_repeated_cost_rows_match_purchase_not_selling_rate(self):
		self.repeated_rows()
		for index, row in enumerate(self.cost_doc.items, 1):
			self.assertEqual(mapping.resolve_source(self.cost_doc, row), f"SUB{index}")
		self.cost_doc.items[0].rate = 15
		with self.assertRaises(MappingError):
			mapping.resolve_source(self.cost_doc, self.cost_doc.items[0])

	def test_repeated_matching_requires_quantity_rate_uom_and_full_description(self):
		for field, value in (("qty", 0.5), ("base_rate", 99), ("uom", "Box"), ("description", "seal")):
			with self.subTest(field=field):
				self.repeated_rows()
				row = self.invoice.items[0]
				row.set(field, value)
				with self.assertRaises(MappingError):
					mapping.resolve_sale(self.invoice, row)

	def test_identical_sales_rows_remain_ambiguous(self):
		self.repeated_rows()
		duplicate = copy.deepcopy(self.invoice.items[0])
		duplicate.name = "DUPLICATE"
		self.invoice.items.append(duplicate)
		with self.assertRaises(MappingError):
			mapping.resolve_sale(self.invoice, self.invoice.items[0])

	def test_identical_job_rows_remain_ambiguous(self):
		self.repeated_rows()
		duplicate = copy.deepcopy(self.job.sublet_details[0])
		duplicate.name = "DUPLICATE"
		self.job.sublet_details.append(duplicate)
		with self.assertRaises(MappingError):
			mapping.resolve_sale(self.invoice, self.invoice.items[0])

	def test_description_backfill_links_both_sides_once(self):
		self.repeated_rows()
		frappe.get_all.side_effect = lambda dt, **kw: ["SC1"] if dt == "Subcontract Invoice" else ["SI1"]
		all_rows = {r.name: r for r in self.invoice.items + self.cost_doc.items}
		original = copy.deepcopy({name: row.__dict__ for name, row in all_rows.items()})
		self.assertEqual(len(backfill.run(True)["linked"]), 6)
		frappe.db.set_value.assert_not_called()

		def write(dt, name, field, value, update_modified):
			self.assertFalse(update_modified)
			self.assertIn(field, (mapping.SALES_FIELD, mapping.SOURCE_FIELD))
			all_rows[name].set(field, value)

		with patch.object(frappe.db, "set_value", side_effect=write):
			self.assertEqual(len(backfill.run(False)["linked"]), 6)
			self.assertEqual(backfill.run(False)["linked"], [])
		for name, row in all_rows.items():
			business = {
				k: v for k, v in row.__dict__.items() if k not in (mapping.SOURCE_FIELD, mapping.SALES_FIELD)
			}
			self.assertEqual(business, original[name])

	def test_future_source_and_sales_links_without_accounting_writes(self):
		mapping.validate_source(self.cost_doc)
		mapping.validate_sales(self.invoice)
		self.assertEqual(self.source.job_order_sublet_row, "SUB1")
		self.assertEqual(self.sale.custom_job_order_sublet_row, "SUB1")
		frappe.db.set_value.assert_not_called()
		frappe.db.sql.assert_not_called()

	def test_wrong_job_company_rejected(self):
		self.cost_doc.company = "OTHER"
		with self.assertRaises(MappingError):
			mapping.resolve_source(self.cost_doc, self.source)

	def test_split_submission_capacity_and_lock(self):
		self.sublet.quantity = 2
		frappe.db.sql.side_effect = [[], [[1]]]
		mapping.check_sales_capacity(self.invoice)
		self.assertIn("FOR UPDATE", frappe.db.sql.call_args_list[0].args[0])
		frappe.db.sql.side_effect = [[], [[2]]]
		with self.assertRaises(ValueError):
			mapping.check_sales_capacity(self.invoice)
		frappe.db.sql.side_effect = None

	def test_return_resolves_original_row_even_before_backfill(self):
		ret = Doc(
			name="RET1", company="C", custom_job_order="JOB1", is_return=1, return_against="SI1", items=[]
		)
		row = Doc(item_code="SERVICE", sales_invoice_item="SII1")
		ret.items = [row]
		self.assertEqual(mapping.resolve_sale(ret, row), "SUB1")
		row.sales_invoice_item = "UNKNOWN"
		with self.assertRaises(MappingError):
			mapping.resolve_sale(ret, row)

	def test_backfill_dry_run_idempotence_and_write_allowlist(self):
		frappe.get_all.side_effect = lambda dt, **kw: ["SC1"] if dt == "Subcontract Invoice" else ["SI1"]
		result = backfill.run(True)
		self.assertEqual(len(result["linked"]), 2)
		frappe.db.set_value.assert_not_called()

		def write(dt, name, field, value, update_modified):
			self.assertFalse(update_modified)
			self.assertIn(
				(dt, field),
				[
					("Subcontract Invoice Item", mapping.SOURCE_FIELD),
					("Sales Invoice Item", mapping.SALES_FIELD),
				],
			)
			row = self.source if dt == "Subcontract Invoice Item" else self.sale
			row.set(field, value)

		frappe.db.set_value.side_effect = write
		result = backfill.run(False)
		self.assertEqual(len(result["linked"]), 2)
		self.assertEqual(backfill.run(False)["linked"], [])
		self.assertEqual(self.source.amount, 1000)
		frappe.db.set_value.side_effect = None

	def test_backfill_flags_ambiguity_without_writes(self):
		self.job.sublet_details.append(Row(name="SUB2", item_code="SERVICE"))
		frappe.get_all.side_effect = lambda dt, **kw: ["SC1"] if dt == "Subcontract Invoice" else ["SI1"]
		result = backfill.run(False)
		self.assertEqual(len(result["review"]), 2)
		frappe.db.set_value.assert_not_called()

	def test_snapshot_catches_ledger_change_but_allows_link_metadata(self):
		record = {"name": "ROW", "debit": 1000}
		frappe.db.sql.side_effect = lambda *a, **kw: [record.copy()]
		before = audit.snapshot()
		record["custom_job_order_sublet_row"] = "SUB1"
		self.assertEqual(before, audit.snapshot())
		record["debit"] = 1001
		self.assertNotEqual(before, audit.snapshot())
		frappe.db.sql.side_effect = None

	def test_cancelled_or_absent_subcontract_cost_is_zero(self):
		gen = SubcontractGrossProfitGenerator.__new__(SubcontractGrossProfitGenerator)
		gen.filters = Row(to_date="2026-10-01")
		frappe.db.sql.side_effect = [[], [[1]]]
		self.assertEqual(gen.cost_rate(self.job, self.sublet), 0)
		sql = frappe.db.sql.call_args_list[0].args[0]
		self.assertIn("sc.docstatus=1", sql)
		self.assertIn("sc.company=%s", sql)
		self.assertIn("sc.transaction_date<=%s", sql)
		frappe.db.sql.side_effect = None

	def test_multiple_cost_invoices_are_added_and_unmapped_cost_blocks_report(self):
		gen = SubcontractGrossProfitGenerator.__new__(SubcontractGrossProfitGenerator)
		gen.filters = Row(to_date="2026-10-01")
		rows = [
			Row(name="A", invoice="SC1", amount=600, job_order_sublet_row="SUB1"),
			Row(name="B", invoice="SC2", amount=400, job_order_sublet_row="SUB1"),
		]
		frappe.db.sql.side_effect = [rows, [[1]]]
		self.assertEqual(gen.cost_rate(self.job, self.sublet), 1000)
		rows[0].job_order_sublet_row = None
		frappe.db.sql.side_effect = [rows]
		with self.assertRaises(MappingError):
			gen.cost_rate(self.job, self.sublet)
		frappe.db.sql.side_effect = None


@unittest.skipUnless(
	hasattr(standard, "execute"), "Set UPSTREAM_GP_SOURCE to the ERPNext v15 gross_profit.py file"
)
class UpstreamReportTests(unittest.TestCase):
	"""Exercise actual upstream execution, grouping and return math with DB reads doubled."""

	def setUp(self):
		from omeir_motors.profitability import gross_profit

		self.report = gross_profit
		frappe.db.reset_mock()
		frappe.db.sql.side_effect = None
		frappe.db.exists.return_value = False
		frappe.db.get_default.side_effect = lambda key: 2 if key == "currency_precision" else 6
		frappe.db.get_single_value.return_value = "Naming Series"
		frappe.get_cached_value.side_effect = lambda dt, *args: "AED" if dt == "Company" else 0
		self.job = Doc(
			name="JOB1",
			company="C",
			docstatus=1,
			sublet_details=[Row(name="SUB1", item_code="S", quantity=1, uom="Nos")],
		)
		self.invoice = Doc(
			name="SI1",
			company="C",
			custom_job_order="JOB1",
			items=[Doc(name="SII1", idx=1, item_code="S", custom_job_order_sublet_row="SUB1")],
		)
		frappe.get_doc.side_effect = lambda dt, name: self.job if dt == "Job Order" else self.invoice
		self.rows = [
			Row(
				parenttype="Sales Invoice",
				parent="SI1",
				posting_date="2026-09-01",
				item_code="S",
				item_name="Service",
				qty=1,
				item_row="SII1",
				base_net_amount=1500,
				invoice_base_net_total=1500,
				customer="CUSTOMER",
				cost_center="CC",
				project="PROJECT",
			)
		]
		self.returns = {}
		self.patches = []
		base = standard.GrossProfitGenerator

		def apply(name, fn):
			p = patch.object(base, name, fn)
			p.start()
			self.patches.append(p)

		apply("load_invoice_items", lambda obj: setattr(obj, "si_list", copy.deepcopy(self.rows)))
		apply("load_drop_ship_buying_rates", lambda obj: None)
		apply("get_delivery_notes", lambda obj: setattr(obj, "delivery_notes", {}))
		apply("load_product_bundle", lambda obj: setattr(obj, "product_bundles", {}))
		apply("load_non_stock_items", lambda obj: setattr(obj, "non_stock_items", ["S"]))
		apply(
			"get_returned_invoice_items",
			lambda obj: setattr(obj, "returned_invoices", copy.deepcopy(self.returns)),
		)
		apply("allocate_legacy_return_items", lambda obj: None)
		self.cost_patch = patch.object(SubcontractGrossProfitGenerator, "cost_rate", return_value=1000)
		self.cost_patch.start()

	def tearDown(self):
		self.cost_patch.stop()
		for p in reversed(self.patches):
			p.stop()
		frappe.get_cached_value.side_effect = None
		frappe.db.get_default.side_effect = None

	def run_report(self, group):
		return self.report.execute(
			Row(company="C", from_date="2026-09-01", to_date="2026-10-01", group_by=group)
		)

	def test_standard_invoice_report_exact_example(self):
		_, rows = self.run_report("Invoice")
		total = rows[-1]
		self.assertEqual(total.selling_amount, 1500)
		self.assertEqual(total.buying_amount, 1000)
		self.assertEqual(total.gross_profit, 500)
		self.assertEqual(total["gross_profit_%"], 33.33)
		self.assertIs(standard.execute.__globals__["GrossProfitGenerator"], standard.GrossProfitGenerator)

	def test_standard_grouping_totals(self):
		for group in ("Item Code", "Customer", "Cost Center", "Project", "Monthly"):
			with self.subTest(group=group):
				cols, data = self.run_report(group)
				total = dict(
					zip(
						[c.get("fieldname") or c["label"].lower().replace(" ", "_") for c in cols],
						data[-1],
						strict=True,
					)
				)
				self.assertEqual(total["buying_amount"], 1000)
				self.assertEqual(total["gross_profit"], 500)
				self.assertEqual(total["gross_profit_%"], 33.33)

	def test_standard_partial_return(self):
		self.returns = {"SI1": {"SII1": [Row(qty=-0.25, base_amount=-375)]}}
		_, data = self.run_report("Invoice")
		self.assertEqual(data[-1].selling_amount, 1125)
		self.assertEqual(data[-1].buying_amount, 750)
		self.assertEqual(data[-1].gross_profit, 375)
		self.assertEqual(data[-1]["gross_profit_%"], 33.33)

	def test_distinct_costs_for_same_service_across_jobs(self):
		job2 = Doc(
			name="JOB2",
			company="C",
			docstatus=1,
			sublet_details=[Row(name="SUB2", item_code="S", quantity=1, uom="Nos")],
		)
		invoice2 = Doc(
			name="SI2",
			company="C",
			custom_job_order="JOB2",
			items=[Doc(name="SII2", idx=1, item_code="S", custom_job_order_sublet_row="SUB2")],
		)
		self.rows.append(
			Row(self.rows[0]).update(
				parent="SI2", item_row="SII2", base_net_amount=1200, invoice_base_net_total=1200
			)
		)
		docs = {
			("Job Order", "JOB1"): self.job,
			("Job Order", "JOB2"): job2,
			("Sales Invoice", "SI1"): self.invoice,
			("Sales Invoice", "SI2"): invoice2,
		}
		frappe.get_doc.side_effect = lambda dt, name: docs[(dt, name)]
		self.cost_patch.stop()
		self.cost_patch = patch.object(
			SubcontractGrossProfitGenerator,
			"cost_rate",
			side_effect=lambda job, sublet: 1000 if job.name == "JOB1" else 700,
		)
		self.cost_patch.start()
		_, data = self.run_report("Invoice")
		items = {r.parent_invoice: r for r in data if r.get("indent") == 1}
		self.assertEqual(items["SI1"].buying_amount, 1000)
		self.assertEqual(items["SI2"].buying_amount, 700)
		self.assertEqual(data[-1].gross_profit, 1000)

	def test_unrelated_service_uses_native_purchase_rate(self):
		self.invoice.custom_job_order = None
		with patch.object(standard.GrossProfitGenerator, "get_buying_amount", return_value=900):
			_, data = self.run_report("Invoice")
		self.assertEqual(data[-1].buying_amount, 900)
		self.assertEqual(data[-1].gross_profit, 600)

	def test_unmapped_historical_sublet_blocks_misleading_profit(self):
		self.invoice.items[0].custom_job_order_sublet_row = None
		with self.assertRaises(ValueError):
			self.run_report("Invoice")


if __name__ == "__main__":
	unittest.main()
