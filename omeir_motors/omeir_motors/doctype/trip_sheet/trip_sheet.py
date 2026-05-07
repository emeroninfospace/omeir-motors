# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import (
    get_datetime, time_diff_in_seconds, flt, now_datetime
)
 
 
class TripSheet(Document):
 
    # ── Validation (runs on Save & Submit) ───────────────────
    def validate(self):
        self.validate_times()
        self.validate_odometer()
        self.validate_fuel()
        self.calculate_trip_hours()
        self.calculate_distance()
        self.calculate_fuel_consumed()
        self.calculate_response_time()
        self.validate_technician_duplicates()
 
    # ── On Submit ────────────────────────────────────────────
    def on_submit(self):
        # Update vehicle odometer on submit
        if self.kms_in and self.vehicle:
            self.update_vehicle_odometer()
 
    
    # ──────────────────────────────────────────────────────────
    # VALIDATION METHODS
    # ──────────────────────────────────────────────────────────
 
    def validate_times(self):
        if self.trip_start_time and self.trip_finish_time:
            if get_datetime(self.trip_finish_time) < get_datetime(self.trip_start_time):
                frappe.throw(
                    "Trip Finish Time <b>{0}</b> cannot be before Trip Start Time <b>{1}</b>.".format(
                        self.trip_finish_time, self.trip_start_time
                    )
                )
 
        if self.repair_request_time and self.location_reached_time:
            if get_datetime(self.location_reached_time) < get_datetime(self.repair_request_time):
                frappe.throw(
                    "Location Reached Time cannot be before Repair Request Time."
                )
 
    def validate_odometer(self):
        if self.kms_in and self.kms_out:
            if flt(self.kms_in) < flt(self.kms_out):
                frappe.throw(
                    "KMs In (<b>{0}</b>) cannot be less than KMs Out (<b>{1}</b>).".format(
                        self.kms_in, self.kms_out
                    )
                )
 
    def validate_fuel(self):
        if self.fuel_in is not None and self.fuel_out is not None:
            if flt(self.fuel_in) > flt(self.fuel_out):
                frappe.msgprint(
                    "Fuel In is greater than Fuel Out. Please verify fuel readings.",
                    indicator="orange",
                    alert=True
                )
 
    def validate_technician_duplicates(self):
        technicians = [row.technician for row in self.technicians if row.technician]
        if len(technicians) != len(set(technicians)):
            frappe.throw("Duplicate technicians found in the Technicians table. Each technician should appear only once.")
 
    # ──────────────────────────────────────────────────────────
    # AUTO-CALCULATION METHODS
    # ──────────────────────────────────────────────────────────
 
    def calculate_trip_hours(self):
        if self.trip_start_time and self.trip_finish_time:
            seconds = time_diff_in_seconds(self.trip_finish_time, self.trip_start_time)
            self.total_trip_hours = round(flt(seconds) / 3600, 2)
        else:
            self.total_trip_hours = 0
 
    def calculate_distance(self):
        if self.kms_in and self.kms_out:
            self.total_distance = round(flt(self.kms_in) - flt(self.kms_out), 1)
        else:
            self.total_distance = 0
 
    def calculate_fuel_consumed(self):
        if self.fuel_out is not None and self.fuel_in is not None:
            consumed = flt(self.fuel_out) - flt(self.fuel_in)
            self.fuel_consumed = round(consumed if consumed >= 0 else 0, 2)
 
    def calculate_response_time(self):
        if self.repair_request_time and self.location_reached_time:
            seconds = time_diff_in_seconds(self.location_reached_time, self.repair_request_time)
            self.response_time_minutes = max(0, int(flt(seconds) / 60))
        else:
            self.response_time_minutes = 0
 
    # ──────────────────────────────────────────────────────────
    # POST-SUBMIT ACTIONS
    # ──────────────────────────────────────────────────────────
 
    def update_vehicle_odometer(self):
        """Update the Vehicle DocType odometer reading after trip submission."""
        try:
            vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)
            if flt(self.kms_in) > flt(vehicle_doc.last_odometer or 0):
                vehicle_doc.last_odometer = self.kms_in
                vehicle_doc.save(ignore_permissions=True)
                frappe.msgprint(
                    "Vehicle <b>{0}</b> odometer updated to <b>{1} KM</b>.".format(
                        self.vehicle, self.kms_in
                    ),
                    indicator="green",
                    alert=True
                )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Trip Monitoring - Odometer Update Failed")
            frappe.msgprint(
                "Could not update vehicle odometer automatically: {0}".format(str(e)),
                indicator="orange"
            )
 
 