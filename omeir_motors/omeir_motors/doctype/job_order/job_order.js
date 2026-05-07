// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Order', {
    setup(frm) {
        frm.ignore_doctypes_on_cancel_all = ["Technician Allocation", "Material Request", "Quotation", "Vehicle Log", "Sales Invoice", "Stock Entry"];
        frm.set_query('item_code', 'service_item', function(doc, cdt, cdn) {
            return {
                filters: {
                    is_stock_item: 0
                }
            };
        });
        frm.set_query('item_code', 'job_order_items', function(doc, cdt, cdn) {
            return {
                filters: {
                    is_stock_item: 1
                }
            };
        });
        frm.set_query('employee', 'service_item', function(doc, cdt, cdn) {

            let row = locals[cdt][cdn];

            return {
                query: "omeir_motors.omeir_motors.doctype.job_order.job_order.get_filtered_employees",
                filters: {
                    item_code: row.item_code || ""
                }
            };
        });
    },
    onload: function(frm) {
        frappe.db.get_single_value('Binomeir Settings', 'sublet_margin')
            .then(value => {
                frm.sublet_margin = value || 0;
            });
    },

    refresh: function(frm) {
        // frm.get_field('job_order_items').grid.cannot_add_rows = true;
        // frm.refresh_field('job_order_items');
        let vehicle_field = frm.get_docfield("vehicle");

        if (vehicle_field) {
            vehicle_field.get_route_options_for_new_doc = () => {
                return {
                    custom_customer: frm.doc.customer
                };
            };
        }

       if (frm.doc.docstatus !== 2 && !frm.is_new()) {

        frappe.db.get_list('Technician Allocation', {
            filters: { job_order: frm.doc.name, docstatus: 1 },
            limit: 1
        }).then((alloc) => {

            if (!alloc.length) {
               frm.add_custom_button('Technician Allocation', () => {

                    frappe.call({
                        method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.create_multiple_allocations',
                        args: {
                            job_order: frm.doc.name
                        },
                        callback: function(r) {
                            if (!r.exc && r.message) {

                                frappe.set_route('List', 'Technician Allocation', {
                                    name: ['in', r.message]
                                });

                            }
                        }
                    });

                }, 'Create');
            }

        });
    }

    if (frm.doc.docstatus === 1) {

        frappe.db.get_list('Sales Invoice', {
            filters: { custom_job_order: frm.doc.name },
            fields: ['name', 'docstatus']
        }).then((invoices) => {

    let active_invoices = invoices.filter(inv => inv.docstatus !== 2);

    frm.add_custom_button('Sales Invoice', () => {

        // Re-fetch fresh data at click time to avoid stale results
        frappe.db.get_list('Sales Invoice', {
            filters: { custom_job_order: frm.doc.name },
            fields: ['name', 'docstatus']
        }).then((fresh_invoices) => {

            let fresh_active = fresh_invoices.filter(inv => inv.docstatus !== 2);

            if (fresh_active.length >= 2) {
                frappe.throw(__('Maximum of 2 Sales Invoices already exist for this Job Order'));
                return;
            }

            // ✅ REMOVED the draft check — allows 2nd invoice even if 1st is draft
            // Only block if both slots are already filled (handled above)

            frappe.call({
                method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.make_sales_invoice',
                args: {
                    source_name: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        let doc = frappe.model.sync(r.message)[0];
                        frappe.set_route('Form', doc.doctype, doc.name);
                    }
                }
            });

        });

    }, 'Create');

});
}
    if (frm.doc.docstatus !== 2 && !frm.is_new() && !frm.doc.quotation) {

    frm.add_custom_button('Quotation', () => {
        frappe.call({
            method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.make_quotation',
            args: {
                source_name: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    let doc = frappe.model.sync(r.message)[0];
                    frappe.set_route('Form', doc.doctype, doc.name);
                }
            }
        });
    }, 'Create');
}
if (frm.doc.docstatus !== 2 && !frm.is_new()) {

    frm.add_custom_button('Material Request', () => {
        frappe.call({
            method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.make_material_request_from_jo',
            args: {
                job_order: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    let doc = frappe.model.sync(r.message)[0];
                    frappe.set_route('Form', doc.doctype, doc.name);
                }
            }
        });
    }, 'Create');

    frm.add_custom_button('Subcontract Work Order', () => {
        frappe.call({
            method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.make_subcontract',
            args: {
                name: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    let doc = frappe.model.sync(r.message)[0];
                    frappe.set_route('Form', doc.doctype, doc.name);
                }
            }
        });
    }, 'Create');

}

    if (frm.doc.docstatus === 2) {
        frm.page.set_indicator('Cancelled', 'red');

    } else if (frm.doc.docstatus === 0) {
        frm.page.set_indicator('Draft', 'grey');

    } else if (frm.doc.status === "Completed") {
        frm.page.set_indicator('Completed', 'green');

    } else if (frm.doc.status === "Pending") {
        frm.page.set_indicator('Pending', 'orange');

    } else {
        frm.page.set_indicator('Pending', 'orange');
    }
},

    vehicle: function(frm) {
        if (frm.doc.vehicle) {
            frappe.db.get_value('Vehicle', frm.doc.vehicle, 'last_odometer')
                .then(r => {
                    if (r.message) {
                        frm.set_value('odometer_value_last', r.message.last_odometer);
                    }
                });
        }
    },
    vehicle_in: function(frm) {
        validate_vehicle_time(frm, 'vehicle_in');
    },

    vehicle_out: function(frm) {
        validate_vehicle_time(frm, 'vehicle_out');
    }
});



function calculate_amount(cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    refresh_field('job_order_items'); 
    
}

function calculate_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.job_order_items || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });

    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_amount', total_amt);
}


frappe.ui.form.on('Job Order Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code) {

            frappe.model.set_value(cdt, cdn, 'quantity', 1);

            frappe.db.get_value('Item Price', {
                item_code: row.item_code,
                price_list: "Standard Selling",
                selling: 1
            }, 'price_list_rate').then(r => {
                frappe.model.set_value(cdt, cdn, 'rate', (r.message && r.message.price_list_rate) || 0);
                calculate_amount(cdt, cdn);
                calculate_totals(frm);
            });
        }
    },

    quantity: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_totals(frm);
        let row = locals[cdt][cdn];
        let amount = (row.quantity || 0) * (row.rate || 0);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    },

    rate: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_totals(frm);
        let row = locals[cdt][cdn];
        let amount = (row.quantity || 0) * (row.rate || 0);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    },
    service_items_remove: function(frm) {
        calculate_service_totals(frm);
    }
});

frappe.ui.form.on('Service Item', {
    item_code: function(frm) {
        toggle_totals(frm);
    },
    quantity: function(frm) {
        toggle_totals(frm);
    },
    item_code: function(frm, cdt, cdn) {
        filter_employees(frm,cdt,cdn)
        let row = locals[cdt][cdn];

        if (row.item_code) {

            frappe.model.set_value(cdt, cdn, 'quantity', 1);

            frappe.db.get_value('Item Price', {
                item_code: row.item_code,
                price_list: "Standard Selling",
                selling: 1
            }, 'price_list_rate').then(r => {
                frappe.model.set_value(cdt, cdn, 'rate', (r.message && r.message.price_list_rate) || 0);
                calculate_amount(cdt, cdn);
                calculate_totals(frm);
            });
        }
    },

    quantity: function(frm, cdt, cdn) {
        calculate_service_amount(cdt, cdn);
        calculate_service_totals(frm);
        let row = locals[cdt][cdn];
        let amount = (row.quantity || 0) * (row.rate || 0);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    },

    rate: function(frm, cdt, cdn) {
        calculate_service_amount(cdt, cdn);
        calculate_service_totals(frm);
        let row = locals[cdt][cdn];
        let amount = (row.quantity || 0) * (row.rate || 0);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    },
    start_time: function(frm, cdt, cdn) {
        calculate_row_duration(frm, cdt, cdn);
    },
    end_time: function(frm, cdt, cdn) {
        calculate_row_duration(frm, cdt, cdn);
    },

});
frappe.ui.form.on('Sublet Items', {
    item_code: function(frm, cdt, cdn) {
        fetch_description(cdt, cdn);
    },
    quantity: function(frm, cdt, cdn) {
        calculate_sublet_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_sublet_amount(frm, cdt, cdn);
    },
});
    function calculate_row_duration(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (row.start_time && row.end_time) {

        let start = frappe.datetime.str_to_obj(row.start_time);
        let end = frappe.datetime.str_to_obj(row.end_time);

        let diff = (end - start) / 1000;

        if (diff < 0) {
            frappe.model.set_value(cdt, cdn, 'start_time', null);
            frappe.model.set_value(cdt, cdn, 'end_time', null);
            frappe.msgprint("End Time cannot be before Start Time");
            frappe.model.set_value(cdt, cdn, 'total_duration', 0);
            return;
        }

        frappe.model.set_value(cdt, cdn, 'total_duration', diff);
    }
}

function calculate_service_amount(cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    refresh_field('sublet_details'); 
    
}
function calculate_sublet_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let qty = row.quantity || 0;
    let rate = row.rate || 0;
    let margin = frm.sublet_margin || 0;
    console.log(margin);

    
    let margin_amount = qty * rate ;
    let amount = qty * (rate * (1+margin / 100));

    frappe.model.set_value(cdt, cdn, 'amount', amount);
    frappe.model.set_value(cdt, cdn, 'margin_amount', margin_amount);

    calculate_sublet_totals(frm);
}
function fetch_description(cdt, cdn) {
    let row = locals[cdt][cdn];
    row.description = frappe.db.get_value('Item', row.item_code, 'description', (r) => {
        row.description = r.description;
        refresh_field('sublet_details');
    });
    refresh_field('sublet_details');
}
function calculate_service_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.service_item || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });
    frm.set_value('total_quantity_service', total_qty);
    frm.set_value('total_amount_service', total_amt);
}
function calculate_sublet_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.sublet_details || []).forEach(row => {
        total_qty += flt(row.quantity);
        total_amt += flt(row.amount);
    });

    frm.set_value('total_qty_sub', total_qty);
    frm.set_value('total_am_sub', total_amt);
}

function toggle_totals(frm) {
    let has_service_items = (frm.doc.service_items || []).length > 0;

    frm.set_df_property('total_amount', 'hidden', has_service_items);
    frm.set_df_property('total_quantity', 'hidden', has_service_items);

    frm.set_df_property('total_amount_service', 'hidden', !has_service_items);
    frm.set_df_property('total_quantity_service', 'hidden', !has_service_items);
}


function validate_vehicle_time(frm, fieldname) {

    if (frm.doc.vehicle_in && frm.doc.vehicle_out) {

        let start = frappe.datetime.str_to_obj(frm.doc.vehicle_in);
        let end = frappe.datetime.str_to_obj(frm.doc.vehicle_out);

        if (end < start) {
            frappe.msgprint("Vehicle Out cannot be before Vehicle In");

            frm.set_value(fieldname, null);
        }
    }
}

function filter_employees(frm,cdt,cdn) {
  frm.set_query('employee', 'service_item', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            return {
                query: "omeir_motors.omeir_motors.doctype.job_order.job_order.get_filtered_employees",
                filters: {
                    item_code: row.item_code
                }
            };
        });
}