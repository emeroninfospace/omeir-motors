# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class TechnicianAllocation(Document):
	def validate(self):
		if self.start_date and self.end_date:
			diff = (getdate(self.end_date) - getdate(self.start_date)).days
			self.total_duration = diff * 24 * 60 * 60
	
	def on_submit(self):
		self.db_set("status", "Completed")
