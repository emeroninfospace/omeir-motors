// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip Sheet", {
	onload: function(frm) {
        frm.set_query('driver', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
 
        frm.set_query('technician', 'technicians', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
    },
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Expense Claim'), function() {

                frappe.db.get_value("Driver", frm.doc.driver, "employee")
                .then(r => {

                    frappe.new_doc("Expense Claim", {
                        employee: r.message.employee,
                        custom_trip_sheet: frm.doc.name
                    });

                });

            });
    }
    },
 
    // ── Trip Start / Finish Time ─────────────────────────────
    trip_start_time: function(frm) {
        calculate_trip_hours(frm);
    },
 
    trip_finish_time: function(frm) {
        calculate_trip_hours(frm);
        // Validate finish is after start
        if (frm.doc.trip_start_time && frm.doc.trip_finish_time) {
            if (frm.doc.trip_finish_time < frm.doc.trip_start_time) {
                frappe.msgprint({
                    title: __('Validation Error'),
                    message: __('Trip Finish Time cannot be before Trip Start Time.'),
                    indicator: 'red'
                });
                frm.set_value('trip_finish_time', '');
            }
        }
    },
 
    // ── Odometer Readings ────────────────────────────────────
    kms_out: function(frm) {
        calculate_distance(frm);
    },
 
    kms_in: function(frm) {
        calculate_distance(frm);
        // Validate kms_in >= kms_out
        if (frm.doc.kms_out && frm.doc.kms_in && frm.doc.kms_in < frm.doc.kms_out) {
            frappe.msgprint({
                title: __('Validation Error'),
                message: __('KMs In cannot be less than KMs Out.'),
                indicator: 'red'
            });
            frm.set_value('kms_in', '');
        }
    },
 
    // ── Fuel ─────────────────────────────────────────────────
    fuel_out: function(frm) {
        calculate_fuel(frm);
    },
 
    fuel_in: function(frm) {
        calculate_fuel(frm);
    },
 
    // ── Breakdown Times ──────────────────────────────────────
    repair_request_time: function(frm) {
        calculate_response_time(frm);
    },
 
    location_reached_time: function(frm) {
        calculate_response_time(frm);
    },
 
    // ── Vehicle Fetch ────────────────────────────────────────
    vehicle: function(frm) {
        if (frm.doc.vehicle) {
            frappe.db.get_value('Vehicle', frm.doc.vehicle, ['last_odometer', 'license_plate'], function(r) {
                if (r && r.last_odometer) {
                    frm.set_value('kms_out', r.last_odometer);
                }
            });
        }
    }
});
 
// ============================================================
// CALCULATION HELPERS
// ============================================================
 
function calculate_trip_hours(frm) {
    if (frm.doc.trip_start_time && frm.doc.trip_finish_time) {
        let start = moment(frm.doc.trip_start_time);
        let end   = moment(frm.doc.trip_finish_time);
        let diff  = end.diff(start, 'minutes');
        if (diff > 0) {
            frm.set_value('total_trip_hours', (diff / 60).toFixed(2));
        }
    } else {
        frm.set_value('total_trip_hours', 0);
    }
}
 
function calculate_distance(frm) {
    if (frm.doc.kms_in && frm.doc.kms_out && frm.doc.kms_in >= frm.doc.kms_out) {
        frm.set_value('total_distance', (frm.doc.kms_in - frm.doc.kms_out).toFixed(1));
    } else {
        frm.set_value('total_distance', 0);
    }
}
 
function calculate_fuel(frm) {
    if (frm.doc.fuel_out != null && frm.doc.fuel_in != null) {
        let consumed = frm.doc.fuel_out - frm.doc.fuel_in;
        frm.set_value('fuel_consumed', consumed >= 0 ? consumed.toFixed(2) : 0);
    }
}
 
function calculate_response_time(frm) {
    if (frm.doc.repair_request_time && frm.doc.location_reached_time) {
        let request  = moment(frm.doc.repair_request_time);
        let reached  = moment(frm.doc.location_reached_time);
        let minutes  = reached.diff(request, 'minutes');
        if (minutes >= 0) {
            frm.set_value('response_time_minutes', minutes);
        }
    }
}
