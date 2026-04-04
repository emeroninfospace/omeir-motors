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

    def before_cancel(self):

        def cancel_stock_entries(material_requests):
            if not material_requests:
                return

            stock_entries = frappe.db.sql("""
                SELECT DISTINCT se.name
                FROM `tabStock Entry` se
                JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
                WHERE sed.material_request IN %s
                AND se.docstatus = 1
            """, (tuple(material_requests),), as_dict=True)

            for se in stock_entries:
                doc = frappe.get_doc("Stock Entry", se.name)
                doc.flags.ignore_links = True
                doc.cancel()


        def cancel_docs(doctype, filters):
            docs = frappe.get_all(doctype, filters=filters, pluck="name")

            for d in docs:
                doc = frappe.get_doc(doctype, d)

                if doc.docstatus == 1:
                    doc.flags.ignore_links = True
                    doc.cancel()


        material_requests = frappe.get_all(
            "Material Request",
            filters={"custom_job_order": self.name},
            pluck="name"
        )

        cancel_stock_entries(material_requests)

        cancel_docs("Sales Invoice", {"custom_job_order": self.name})

        cancel_docs("Technician Allocation", {"job_order": self.name})
        cancel_docs("Vehicle Log", {"custom_job_order": self.name})

        cancel_docs("Material Request", {"custom_job_order": self.name})

        cancel_docs("Quotation", {"custom_job_order": self.name})

    def create_vehicle_log(self):
        if not self.vehicle:
            return

        vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)

        log = frappe.new_doc("Vehicle Log")
        log.flags.ignore_mandatory = True
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
    
    def calculate_total(self):
        total_quantity = 0
        total_amount = 0

        for row in self.job_order_items:
            row.amount = (row.quantity or 0) * (row.rate or 0)

            total_quantity += row.quantity or 0
            total_amount += row.amount or 0

        self.total_quantity = total_quantity
        self.total_amount = total_amount

    def validate(self):
        self.calculate_total()
    

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):    
    def set_missing_values(source, target):
        target.customer = source.customer
        target.posting_date = nowdate()
        target.set_posting_time = 1
        target.update_stock = 1
        target.set_warehouse = source.warehouse
        if source.company:
            target.company = source.company
        if source.vehicle:
            target.custom_vehicle_no = source.vehicle
        if source.odometer_value_last:
            target.custom_odometer = source.odometer_value_last
        if source.vehicle_in:
            target.custom_vehicle_in = source.vehicle_in
        if source.vehicle_out:
            target.custom_vehicle_out = source.vehicle_out
        if source.make:
            target.custom_make = source.make
        if source.model:
            target.custom_model = source.model
        if source.fuel_type:
            target.custom_fuel_type = source.fuel_type
        if source.year:
            target.custom_year = source.year
        if source.chasis_number:
            target.custom_chasis_number = source.chasis_number
            
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
        
        if source.item_code:
            item_data = frappe.db.get_value(
            "Item",
            source.item_code,
            ["item_name", "stock_uom", "description"],
            as_dict=1
        )
            if item_data:
                target.item_name = item_data.item_name
                target.uom = item_data.stock_uom
                target.stock_uom = item_data.stock_uom
                target.conversion_factor = 1

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
            },
            "Service Item": {   
            "doctype": "Sales Invoice Item",
            "field_map": {
                "item_code": "item_code",
                "item_name": "item_name",
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
	return doc.service_item


@frappe.whitelist()
def make_quotation(source_name):
    job_order = frappe.get_doc("Job Order", source_name)

    quotation = frappe.new_doc("Quotation")

    quotation.party_name = job_order.customer
    quotation.custom_job_order = job_order.name
    quotation.custom_vehicle = job_order.vehicle
    quotation.custom_driver = job_order.driver

    quotation.custom_model = job_order.model
    quotation.custom_make = job_order.make
    quotation.custom_fuel_type = job_order.fuel_type
    quotation.custom_odometer = job_order.odometer_value_last
    quotation.custom_year = job_order.year

    for item in job_order.job_order_items:
        quotation.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.quantity,
            "rate": item.rate,
            "amount": item.amount
        })

    for service in job_order.service_item:
        quotation.append("items", {
            "item_code": service.item_code,
            "item_name": service.item_name,
            "qty": service.quantity,
            "rate": service.rate,
            "amount": service.amount
        })

    quotation.save(ignore_permissions=True)

    job_order.db_set("quotation", quotation.name)

    return quotation


@frappe.whitelist()
def make_material_request(quotation):
    quotation_doc = frappe.get_doc("Quotation", quotation)

    job_order_name = quotation_doc.custom_job_order
    if not job_order_name:
        frappe.throw("Job Order not linked in Quotation")

    job_order = frappe.get_doc("Job Order", job_order_name)

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Material Transfer"
    mr.company = quotation_doc.company
    mr.custom_job_order = quotation_doc.custom_job_order

    mr.set_warehouse = job_order.warehouse

    default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    if not default_warehouse:
        frappe.throw("Default Warehouse not set in Stock Settings")

    mr.set_from_warehouse  = default_warehouse

    for item in job_order.job_order_items:
        if not item.item_code:
            continue

        stock_uom = frappe.db.get_value("Item", item.item_code, "stock_uom")

        mr.append("items", {
            "item_code": item.item_code,
            "qty": item.quantity,
            "stock_qty": item.quantity,
            "uom": stock_uom,
            "stock_uom": stock_uom,
            "conversion_factor": 1,
            "schedule_date": frappe.utils.nowdate(),
            "from_warehouse": default_warehouse,
            "warehouse": job_order.warehouse,
            "allow_zero_valuation_rate": 1
        })

    mr.save(ignore_permissions=True)

    job_order.db_set("quotation", quotation_doc.name)

    return mr


@frappe.whitelist()
def make_material_request_from_jo(job_order):

    job_order = frappe.get_doc("Job Order", job_order)

    existing_items = frappe.db.sql("""
        SELECT 
            mri.item_code,
            SUM(mri.qty) as total_qty
        FROM `tabMaterial Request Item` mri
        JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mr.custom_job_order = %s
        AND mr.docstatus != 2
        GROUP BY mri.item_code
    """, job_order.name, as_dict=1)

    existing_qty_map = {d.item_code: d.total_qty for d in existing_items}

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Material Transfer"
    mr.company = job_order.company
    mr.custom_job_order = job_order.name

    mr.transaction_date = frappe.utils.nowdate()
    mr.schedule_date = frappe.utils.nowdate()

    mr.set_warehouse = job_order.warehouse

    default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    if not default_warehouse:
        frappe.throw("Default Warehouse not set in Stock Settings")

    mr.set_from_warehouse = default_warehouse

    added = False

    for item in job_order.job_order_items:
        if not item.item_code or item.quantity <= 0:
            continue

        already_requested = existing_qty_map.get(item.item_code, 0)
        remaining_qty = item.quantity - already_requested

        if remaining_qty <= 0:
            continue

        item_doc = frappe.get_doc("Item", item.item_code)

        mr.append("items", {
            "item_code": item.item_code,
            "item_name": item_doc.item_name,
            "description": item_doc.description or item_doc.item_name,
            "item_group": item_doc.item_group,
            "qty": remaining_qty,
            "stock_qty": remaining_qty,
            "uom": item_doc.stock_uom,
            "stock_uom": item_doc.stock_uom,
            "conversion_factor": 1,
            "schedule_date": frappe.utils.nowdate(),
            "from_warehouse": default_warehouse,
            "warehouse": job_order.warehouse,
            "allow_zero_valuation_rate": 1
        })

        added = True

    if not added:
        frappe.throw("All items are already requested in previous Material Requests")

    mr.save(ignore_permissions=True)


    return mr


@frappe.whitelist()
def get_filtered_employees(doctype, txt, searchfield, start, page_len, filters):
    item_code = filters.get("item_code")

    if not item_code:
        return []

    item = frappe.get_doc("Item", item_code)

    employees = [
        d.employee for d in item.custom_technician_allocation_
        if d.employee
    ]

    if not employees:
        return []

    return frappe.db.sql("""
        SELECT name, employee_name
        FROM `tabEmployee`
        WHERE name IN %(employees)s
        AND name LIKE %(txt)s
        LIMIT %(start)s, %(page_len)s
    """, {
        "employees": tuple(employees),
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })


@frappe.whitelist()
def create_multiple_allocations(job_order):
    job_order_doc = frappe.get_doc("Job Order", job_order)

    created_docs = []

    for item in job_order_doc.service_item:
        if not item.item_code or not item.employee:
            continue

        exists = frappe.db.sql("""
            SELECT ta.name
            FROM `tabTechnician Allocation` ta
            INNER JOIN `tabTechnician Service Item` tsi
                ON tsi.parent = ta.name
            WHERE ta.job_order = %s
            AND ta.employee = %s
            AND tsi.item_code = %s
            AND ta.docstatus != 2
        """, (job_order_doc.name, item.employee, item.item_code))

        if exists:
            frappe.msgprint(
                f"Allocation already exists for Item {item.item_code} and Employee {item.employee}"
            )
            continue

        ta = frappe.new_doc("Technician Allocation")
        ta.job_order = job_order_doc.name
        ta.start_date = frappe.utils.now_datetime()
        ta.request_items = job_order_doc.request_parts
        ta.employee = item.employee

        ta.append("table_yuoo", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "quantity": item.quantity,
            "rate": item.rate,
            "amount": item.amount
        })

        ta.insert(ignore_permissions=True)
        created_docs.append(ta.name)

    return created_docs