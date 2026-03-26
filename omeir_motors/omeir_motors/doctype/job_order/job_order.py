# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

class JobOrder(Document):

	def before_save(self):
		self.validate_and_update_vehicle_odometer()

	def on_submit(self):
		self.validate_and_update_vehicle_odometer()
		self.create_vehicle_log()

	def validate_and_update_vehicle_odometer(self):
		if not self.vehicle or not self.odometer_value_last:
			return

		vehicle_odometer = frappe.db.get_value(
			"Vehicle", self.vehicle, "last_odometer"
		)

		job_odometer = float(self.odometer_value_last or 0)
		vehicle_odometer = float(vehicle_odometer or 0)

		if job_odometer < vehicle_odometer:
			frappe.throw(
				f"Odometer cannot be less than current vehicle reading ({vehicle_odometer})"
			)

		if job_odometer > vehicle_odometer:
			frappe.db.set_value(
				"Vehicle",
				self.vehicle,
				"last_odometer",
				job_odometer
			)


	def create_vehicle_log(self):
		if not self.vehicle:
			return

		vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)

		log = frappe.new_doc("Vehicle Log")
		log.custom_job_order = self.name
		log.vehicle = self.vehicle
		log.model = self.model or vehicle_doc.model
		log.license_plate = vehicle_doc.license_plate
		log.custom_model = self.model
		log.make = self.make
		log.date = frappe.utils.nowdate()
		log.last_odometer = self.odometer_value_last
		log.odometer = self.odometer_value_last

		for item in self.job_order_items:
			row = log.append("custom_service_items", {})
			row.item_code = item.item_code
			row.item_name = item.item_name
			row.uom = item.uom
			row.quantity = item.quantity
			row.rate = item.rate
			row.amount = (item.quantity or 0) * (item.rate or 0)

		log.insert(ignore_permissions=True)
		log.submit()


import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):    
    def set_missing_values(source, target):
        target.customer = source.customer
        target.posting_date = nowdate()
        target.set_posting_time = 1
        
        if source.company:
            target.company = source.company
            
        if target.get("items"):
            total_qty = sum([flt(item.qty) for item in target.items])
            target.total_qty = total_qty
            target.total = source.total_amount or 0
            target.grand_total = source.total_amount or 0
            target.outstanding_amount = source.total_amount or 0

    def update_item(source, target, source_parent):
        target.item_code = source.item_code
        target.item_name = source.item_name
        target.description = source.description
        target.qty = source.quantity
        target.rate = source.rate
        target.amount = source.amount
        target.uom = source.uom
        
        if not target.income_account:
            income_account = frappe.db.get_value("Item Default", 
                {"parent": source.item_code, "company": source_parent.company}, 
                "income_account")
            if not income_account:
                income_account = frappe.db.get_value("Company", 
                    source_parent.company, "default_income_account")
            target.income_account = income_account
      

    doc = get_mapped_doc(
        "Job Order",
        source_name,
        {
            "Job Order": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "customer": "customer",
                    "name": "custom_job_order", 
                    "posting_date": "posting_date",
                    "transaction_date": "posting_date",
                    "total_amount": "total",
                    "currency": "currency",
                    "conversion_rate": "conversion_rate"
                }
            },
            "Job Order Item": {   
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_code": "item_code",
                    "item_name": "item_name",
                    "uom": "uom",
                    "description": "description",
                    "quantity": "qty",   
                    "rate": "rate",
                    "amount": "amount"
                },
                "postprocess": update_item
            }
        },
        target_doc,
        set_missing_values
    )

    return doc


@frappe.whitelist()
def get_items_for_allocation(job_order):
	doc = frappe.get_doc("Job Order", job_order)
	return doc.job_order_items