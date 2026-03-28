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
		
		if self.job_order:
			frappe.db.set_value("Job Order", self.job_order, "status", "In Progress")
	
	def on_submit(self):
		self.db_set("status", "Completed")
		if self.job_order:
			frappe.db.set_value("Job Order", self.job_order, "status", "In Progress")
		if not self.job_order:
			return

		job_order = frappe.get_doc("Job Order", self.job_order)

		existing_items_map = {}
		for row in job_order.job_order_items:
			existing_items_map[row.item_code] = row

		for part in self.parts_items:

			if part.item_code in existing_items_map:
				jo_row = existing_items_map[part.item_code]
				jo_row.quantity = part.quantity

			else:
				job_order.append("job_order_items", {
					"item_code": part.item_code,
					"item_name": part.item_name,
					"uom": part.uom,
					"quantity": part.quantity,
				})

		total_qty = 0
		total_amt = 0

		for row in job_order.job_order_items:
			qty = row.quantity or 0
			rate = row.rate or 0

			row.amount = qty * rate

			total_qty += qty
			total_amt += row.amount

		job_order.total_quantity = total_qty
		job_order.total_amount = total_amt

		job_order.total_duration = self.total_duration
		job_order.save(ignore_permissions=True)
		
	
	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if self.job_order:
			update_job_order_status(self.job_order)
	

def update_job_order_status(job_order):
	has_allocation = frappe.db.exists("Technician Allocation", {
		"job_order": job_order,
		"docstatus": ["!=", 2]
	})

	if has_allocation:
		status = "In Progress"
	else:
		status = "Pending"

	frappe.db.set_value("Job Order", job_order, "status", status)
