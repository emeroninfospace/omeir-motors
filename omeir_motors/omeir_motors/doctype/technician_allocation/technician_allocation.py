# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class TechnicianAllocation(Document):
	def validate(self):
		if self.start_date and self.end_date:
			diff = (get_datetime(self.end_date) - get_datetime(self.start_date)).total_seconds()
			self.total_duration = diff
	
	def on_submit(self):
		self.db_set("status", "Completed")
