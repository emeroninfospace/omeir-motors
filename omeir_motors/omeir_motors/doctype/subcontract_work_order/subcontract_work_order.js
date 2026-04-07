frappe.ui.form.on("Subcontract Work Order", {
    refresh(frm) {
        // calculate_totals(frm);
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Job Order"),
                function () {
                    erpnext.utils.map_current_doc({
                        method: "omeir_motors.omeir_motors.doctype.subcontract_work_order.subcontract_work_order.make_subcontract_work_order_from_job_order",
                        source_doctype: "Job Order",
                        target: frm,
                        setters: {
                            company: frm.doc.company || undefined
                        },
                        get_query_filters: {
                            docstatus: ["in", [0, 1]]
                        },
                        allow_child_item_selection: true,
                        child_fieldname: "sublet_details",
                        child_columns: ["item_code", "item_name", "quantity", "amount"]
                    });
                },
                __("Get Items From")
            );
        }
        if (frm.doc.docstatus === 1 && frm.doc.supplier) {

            frm.add_custom_button("Subcontract Invoice", () => {
                frappe.call({
                    method: "omeir_motors.omeir_motors.doctype.subcontract_work_order.subcontract_work_order.create_subcontract_invoice",
                    args: {
                        docname: frm.doc.name
                    },
                    callback(r) {
                        if (r.message) {
                            frappe.msgprint("Subcontract Invoice Created: " + r.message);
                            frappe.set_route("Form", "Subcontract Invoice", r.message);
                        }
                    }
                });
            }, "Create");

        }
    },

    purchase_taxes_and_charges_template(frm) {
        if (!frm.doc.purchase_taxes_and_charges_template) return;

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Purchase Taxes and Charges Template",
                name: frm.doc.purchase_taxes_and_charges_template
            },
            callback(r) {
                if (r.message) {
                    frm.clear_table("purchase_taxes_and_charges");

                    (r.message.taxes || []).forEach(tax => {
                        let row = frm.add_child("purchase_taxes_and_charges");
                        row.charge_type = tax.charge_type;
                        row.rate = tax.rate;
                        row.account_head = tax.account_head;
                        row.add_deduct_tax = tax.add_deduct_tax;
                        row.description = tax.description;
                    });

                    frm.refresh_field("purchase_taxes_and_charges");
                    calculate_taxes(frm);
                }
            }
        });
    },

    items_add(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Subcontract Work Item', {

    items_add(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.quantity) {
            row.quantity = 1;
        }

        calculate_row_amount(frm, cdt, cdn);
    },

    item_code(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code) {
            frappe.db.get_value('Item Price', {
                item_code: row.item_code
            }, 'price_list_rate').then(r => {
                if (r.message) {
                    row.rate = r.message.price_list_rate || 0;
                    calculate_row_amount(frm, cdt, cdn);
                }
            });
        }
    },

    quantity(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },

    rate(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },

    items_remove(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on("Purchase Taxes and Charges", {
    rate(frm) {
        calculate_taxes(frm);
    },
    charge_type(frm) {
        calculate_taxes(frm);
    },
    add_deduct_tax(frm) {
        calculate_taxes(frm);
    },
    tax_amount(frm) {
        calculate_taxes(frm);
    }
});

function calculate_row_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    row.amount = (row.quantity || 0) * (row.rate || 0);

    refresh_field('items');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.items || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });

    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_currency', total_amt);

    frm.refresh_field("total_currency");

    calculate_taxes(frm);
}

function calculate_taxes(frm) {
    let net_total = frm.doc.total_currency || 0;
    let running_total = net_total;

    let added = 0;
    let deducted = 0;

    (frm.doc.purchase_taxes_and_charges || []).forEach((row, index) => {
        let tax_amount = 0;

        if (row.charge_type === "On Net Total") {
            tax_amount = (net_total * (row.rate || 0)) / 100;
        }

        else if (row.charge_type === "On Previous Row Amount" && index > 0) {
            let prev = frm.doc.purchase_taxes_and_charges[index - 1];
            tax_amount = ((prev.tax_amount || 0) * (row.rate || 0)) / 100;
        }

        else if (row.charge_type === "On Previous Row Total" && index > 0) {
            tax_amount = ((running_total || 0) * (row.rate || 0)) / 100;
        }

        else if (row.charge_type === "Actual") {
            tax_amount = row.tax_amount || 0;
        }

        row.tax_amount = tax_amount;

        if (row.add_deduct_tax === "Add") {
            running_total += tax_amount;
            added += tax_amount;
        } else {
            running_total -= tax_amount;
            deducted += tax_amount;
        }

        row.total = running_total;
    });

    refresh_field("purchase_taxes_and_charges");

    let total = added - deducted;

    frm.set_value("taxes_and_charges_added", added);
    frm.set_value("taxes_and_charges_deducted", deducted);
    frm.set_value("total_taxes_and_charges", total);

    frm.set_value("grand_total", running_total);
}

function fetch_job_orders(frm) {
    frm.add_custom_button("Get Items from Job Order", () => {

            let d = new frappe.ui.Dialog({
                title: "Select Job Order",
                fields: [
                    {
                        label: "Job Order",
                        fieldname: "job_order",
                        fieldtype: "Link",
                        options: "Job Order",
                        reqd: 1
                    }
                ],
                primary_action_label: "Get Items",
                primary_action(values) {

                    frappe.call({
                        method: "omeir_motors.omeir_motors.doctype.subcontract_work_order.subcontract_work_order.get_items_from_job_order",
                        args: {
                            job_order: values.job_order
                        },
                        callback(r) {
                            if (r.message) {

                                frm.clear_table("items");

                                r.message.forEach(item => {
                                    let row = frm.add_child("items");

                                    row.item_code = item.item_code;
                                    row.item_name = item.item_name;
                                    row.uom = item.uom;
                                    row.description = item.description;
                                    row.quantity = item.quantity;
                                    row.rate = item.rate;
                                    row.amount = item.amount;
                                });

                                frm.refresh_field("items");
                                calculate_totals(frm);
                            }
                        }
                    });

                    d.hide();
                }
            });

            d.show();
        });
}