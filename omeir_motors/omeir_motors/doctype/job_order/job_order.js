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
            frm.add_custom_button('Create Sales Invoice', () => {
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
    }
});


frappe.ui.form.on('Job Order Item', {
    quantity: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_totals(frm);
    },
    rate: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_totals(frm);
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