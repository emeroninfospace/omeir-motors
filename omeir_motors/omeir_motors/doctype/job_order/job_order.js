// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Order', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button('Create Quotation', () => {
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
    }
});


frappe.ui.form.on('Job Order Item', {
    quantity: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
    }
});

function calculate_amount(cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    refresh_field('job_order_items'); 
}