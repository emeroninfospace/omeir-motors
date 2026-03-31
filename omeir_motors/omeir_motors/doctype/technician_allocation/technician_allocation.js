// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technician Allocation", {


	refresh(frm) {
        // filter_employees(frm);
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
        if (frm.doc.job_order && frm.doc.docstatus == 0 && !frm.is_new()) {

        frm.add_custom_button('Request Items', () => {

            let formatted_text = (frm.doc.request_items || "No items")
                .split("\n")
                .map(line => line.trim())   // removes unwanted spaces
                .join("\n");

            frappe.confirm(
                `
                <div>
                    <p><b>Requested Items:</b></p>
                    <div style="
                        white-space: pre-line;
                        font-family: monospace;
                        border: 1px solid #ccc;
                        padding: 10px;
                        max-height: 200px;
                        overflow: auto;
                        background: #fafafa;
                    ">
            ${frappe.utils.escape_html(formatted_text)}
                    </div>
                    <br>
                    <p>Is there all items you need to request?</p>
                </div>
                `,
                () => {

                   frappe.call({
                        method: "frappe.client.get_value",
                        args: {
                            doctype: "Job Order",
                            filters: { name: frm.doc.job_order },
                            fieldname: ["request_parts"]
                        },
                        callback: function(r) {
                            let existing = r.message.request_parts || "";
                            let new_value = frm.doc.request_items || "";

                            // ✅ Merge with line break
                            let combined = existing 
                                ? existing + "\n\n" + new_value 
                                : new_value;

                            frappe.call({
                                method: "frappe.client.set_value",
                                args: {
                                    doctype: "Job Order",
                                    name: frm.doc.job_order,
                                    fieldname: {
                                        request_parts: combined
                                    }
                                },
                                callback: function() {
                                    frappe.msgprint("Request Items updated in Job Order");
                                }
                            });
                        }
                    });

                },
                () => {
                    frappe.msgprint("Request cancelled");
                }
            );

        });
    }
	}
});


frappe.ui.form.on('Technician Service Item', {
    quantity: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },
    start_time: function(frm, cdt, cdn) {
        calculate_row_duration(frm, cdt, cdn);
    },

    end_time: function(frm, cdt, cdn) {
        calculate_row_duration(frm, cdt, cdn);
    }
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

