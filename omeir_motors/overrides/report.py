from frappe.core.doctype.report.report import Report


class OmeirReport(Report):
	def execute_module(self, filters):
		if self.name == "Gross Profit" and self.is_standard == "Yes" and self.module == "Accounts":
			from omeir_motors.profitability.gross_profit import execute

			return execute(filters)
		return super().execute_module(filters)
