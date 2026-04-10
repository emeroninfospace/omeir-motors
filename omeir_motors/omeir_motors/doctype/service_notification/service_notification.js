// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Notification", {
	refresh(frm) {
       if (frm.doc.docstatus === 1) {

    frappe.db.get_list('Sales Invoice', {
        filters: { custom_service_notification: frm.doc.name },
        fields: ['name', 'docstatus']
    }).then((invoices) => {

        let has_invoice = false;
        let has_draft = false;
        let has_submitted = false;

        if (invoices.length) {
            has_invoice = true;

            invoices.forEach(inv => {
                if (inv.docstatus === 0) has_draft = true;
                if (inv.docstatus === 1) has_submitted = true;
            });
        }

        frm.add_custom_button('Sales Invoice', () => {

            if (has_draft) {
                frappe.throw(__('A Draft Sales Invoice already exists for this Service Notification'));
            }

            if (has_submitted) {
                frappe.throw(__('A Submitted Sales Invoice already exists for this Service Notification'));
            }

            frappe.call({
                method: 'omeir_motors.omeir_motors.doctype.service_notification.service_notification.make_sales_invoice',
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

    });
}

	},
});


frappe.ui.form.on('Service Item', {
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
    refresh_field('service_items'); 
    
}

function calculate_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.service_items || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });

    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_amount', total_amt);
}