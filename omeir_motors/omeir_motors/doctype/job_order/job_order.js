// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Order', {
    refresh: function(frm) {
        let vehicle_field = frm.get_docfield("vehicle");

        if (vehicle_field) {
            vehicle_field.get_route_options_for_new_doc = () => {
                return {
                    custom_customer: frm.doc.customer
                };
            };
        }

        if (frm.doc.docstatus === 1) {
            Promise.all([
                frappe.db.get_list('Technician Allocation', {
                    filters: { job_order: frm.doc.name , docstatus: ["in", [0, 1]]},
                    limit: 1
                }),
                frappe.db.get_list('Sales Invoice', {
                    filters: { custom_job_order: frm.doc.name, docstatus: ["in", [0, 1]]},
                    limit: 1
                })
            ]).then(([alloc, invoice]) => {

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

                                        (r.message || []).forEach(item => {
                                            let row = frappe.model.add_child(doc, 'table_yuoo');

                                            row.item_code = item.item_code;
                                            row.item_name = item.item_name;
                                            row.uom = item.uom;
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
    }
});