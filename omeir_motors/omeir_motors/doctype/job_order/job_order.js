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
        frm.add_custom_button('Technician Allocation', () => {
            frappe.new_doc('Technician Allocation', {
                start_date: frappe.datetime.get_today(),
                job_order: frm.doc.name,
            });
        }, 'Create');
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