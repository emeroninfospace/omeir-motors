# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class TechnicianAllocation(Document):
	def validate(self):	
		if self.job_order:
			

			job_order = frappe.get_doc("Job Order", self.job_order)

			jo_items_map = {}
			for row in job_order.service_item:
				if row.item_code:
					jo_items_map[row.item_code] = row

			for row in self.table_yuoo:
				if not row.item_code:
					continue

				if row.item_code in jo_items_map:
					jo_row = jo_items_map[row.item_code]

					jo_row.start_time = row.start_time
					jo_row.end_time = row.end_time
					jo_row.total_duration = row.total_duration

			job_order.save(ignore_permissions=True)
					
	
	def on_submit(self):
		self.db_set("status", "Completed")

		if not self.job_order:
			return

		total_duration = 0

		for row in self.table_yuoo:
			total_duration += row.total_duration or 0

		

		job_order = frappe.get_doc("Job Order", self.job_order)

		
		job_order.total_duration = (job_order.total_duration or 0) + total_duration

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
