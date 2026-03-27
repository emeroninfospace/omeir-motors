// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technician Allocation", {
	refresh(frm) {
        calculate_totals(frm);
        filter_employees(frm);
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