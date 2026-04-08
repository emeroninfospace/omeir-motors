# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ServiceNotification(Document):
	def validate_rate_amount(self):
		if self.service_items:
			self.total_amount = sum(item.amount for item in self.service_items)
			self.total_quantity = sum(item.quantity for item in self.service_items)
			
