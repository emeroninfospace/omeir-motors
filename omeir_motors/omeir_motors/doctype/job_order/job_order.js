// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Order', {
    setup(frm) {
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
                        method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.get_items_for_allocation',
                        args: {
                            job_order: frm.doc.name
                        },
                        callback: function(r) {

                            if (r.message) {

                                frappe.new_doc('Technician Allocation', {}, (doc) => {

                                    doc.job_order = frm.doc.name;
                                    doc.start_date = frappe.datetime.now_datetime();
                                    doc.request_items = frm.doc.request_parts;
                                    (r.message || []).forEach(item => {
                                        let row = frappe.model.add_child(doc, 'table_yuoo');

                                        row.item_code = item.item_code;
                                        row.item_name = item.item_name;
                                        row.description = item.description
                                        row.quantity = item.quantity;
                                        row.rate = item.rate;
                                        row.amount = item.amount;
                                    });

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
            filters: { custom_job_order: frm.doc.name, docstatus: 1 },
            limit: 1
        }).then((invoice) => {

            if (!invoice.length) {
                frm.add_custom_button('Sales Invoice', () => {

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

                }, 'Create');
            }

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

    if (frm.doc.docstatus !== 2 && !frm.is_new() && !frm.doc.material_request) {

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
}

       if (frm.doc.docstatus === 2) {
            frm.page.set_indicator('Cancelled', 'grey');
        } else if (frm.doc.status === "Completed") {
            frm.page.set_indicator('Completed', 'green');
        } else if (frm.doc.status === "In Progress") {
            frm.page.set_indicator('In Progress', 'orange');
        } else {
            frm.page.set_indicator('Pending', 'red');
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
    refresh_field('service_item'); 
    
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