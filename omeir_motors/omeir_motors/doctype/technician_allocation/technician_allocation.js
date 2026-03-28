// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technician Allocation", {
    setup(frm) {
        frm.set_query('item_code', 'parts_items', function(doc, cdt, cdn) {
            return {
                filters: {
                    is_stock_item: 1
                }
            };
        });
    },

	refresh(frm) {
        calculate_totals(frm);
        filter_employees(frm);
        frm.get_field('table_yuoo').grid.cannot_add_rows = true;
        frm.refresh_field('table_yuoo');
        if (frm.doc.status === "Completed") {
            frm.page.set_indicator('Completed', 'green');
        }
        if (frm.doc.docstatus === 2) {
            frm.page.set_indicator('Cancelled', 'grey');
        } else if (frm.doc.status === "Completed") {
            frm.page.set_indicator('Completed', 'green');
        } else {
            frm.page.set_indicator('Pending', 'red');
        }
	},
});


frappe.ui.form.on('Technician Service Item', {
    quantity: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    }
});

function calculate_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    frm.refresh_field('table_yuoo');
    calculate_totals(frm);
}


function calculate_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.table_yuoo || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });

    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_amount', total_amt);
}

function filter_employees(frm) {
    let item_codes = (frm.doc.table_yuoo || []).map(row => row.item_code);

    if (!item_codes.length) return;

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Item',
            filters: {
                name: ['in', item_codes]
            },
            fields: ['name'],
            limit_page_length: 100
        },
        callback: function(res) {

            let employees = [];

            let promises = res.message.map(item => {
                return frappe.db.get_doc('Item', item.name).then(doc => {
                    (doc.custom_technician_allocation_ || []).forEach(row => {
                        if (row.employee) {
                            employees.push(row.employee);
                        }
                    });
                });
            });

            Promise.all(promises).then(() => {

                employees = [...new Set(employees)];

                frm.set_query('employee', function() {
                    return {
                        filters: {
                            name: ['in', employees]
                        }
                    };
                });

            });
        }
    });
}

frappe.ui.form.on('Technician Allocation Item', {
    item_code: function(frm) {
        filter_employees(frm);
    }
});


frappe.ui.form.on('Parts Items', {
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
    }
});


function calculate_service_amount(cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    refresh_field('parts_items'); 
    
}

function calculate_service_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.parts_items || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });
    frm.set_value('total_quantity_service', total_qty);
    frm.set_value('total_amount_service', total_amt);
}