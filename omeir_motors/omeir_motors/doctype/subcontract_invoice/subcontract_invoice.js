frappe.ui.form.on("Subcontract Invoice", {
    refresh(frm) {
        const status_colors = {
            "Paid": "green",
            "Partially Paid": "orange",
            "Unpaid": "red",
            "Draft": "gray",
            "Cancelled": "red"
        };
        if (frm.doc.status && status_colors[frm.doc.status]) {
            frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
        }

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Accounting Ledger", () => {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.transaction_date,
                    to_date: frappe.datetime.get_today(),
                    company: frm.doc.company,
                    categorize_by: "Categorize by Voucher (Consolidated)"
                };
                frappe.set_route("query-report", "General Ledger");
            }, "View");
        }

        make_payment(frm);
    },

    purchase_taxes_and_charges_add(frm) {
        calculate_taxes(frm);
    },

    purchase_taxes_and_charges_remove(frm) {
        calculate_taxes(frm);
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
        calculate_invoice_totals(frm);
    }
});

frappe.ui.form.on("Subcontract Invoice Item", {
    quantity(frm, cdt, cdn) {
        calculate_invoice_row(frm, cdt, cdn);
    },
    rate(frm, cdt, cdn) {
        calculate_invoice_row(frm, cdt, cdn);
    },
    items_remove(frm) {
        calculate_invoice_totals(frm);
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

function calculate_invoice_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    refresh_field("items");
    calculate_invoice_totals(frm);
}

function calculate_invoice_totals(frm) {
    let total_qty = 0;
    let total_amt = 0;

    (frm.doc.items || []).forEach(row => {
        total_qty += row.quantity || 0;
        total_amt += row.amount || 0;
    });

    frm.set_value("total_quantity", total_qty);
    frm.set_value("total_amount", total_amt);
    frm.refresh_field("total_amount");
    calculate_taxes(frm);
}

function calculate_taxes(frm) {
    let net_total = frm.doc.total_amount || 0;
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

function make_payment(frm) {
    if (frm.doc.docstatus !== 1) return;
    if (frm.doc.status === "Paid") return;

    frm.add_custom_button("Make Payment", () => {

        let outstanding = (frm.doc.grand_total || 0) - (frm.doc.paid_amount || 0);

        if (outstanding <= 0) {
            frappe.msgprint("Invoice already fully paid");
            return;
        }

        let d = new frappe.ui.Dialog({
            title: "Make Payment",
            fields: [
                {
                    label: "Mode of Payment",
                    fieldname: "mode_of_payment",
                    fieldtype: "Link",
                    options: "Mode of Payment",
                    reqd: 1
                },
                {
                    label: "Grand Total",
                    fieldname: "grand_total",
                    fieldtype: "Currency",
                    read_only: 1,
                    default: frm.doc.grand_total
                },
                {
                    label: "Outstanding Amount",
                    fieldname: "outstanding",
                    fieldtype: "Currency",
                    read_only: 1,
                    default: outstanding
                },
                {
                    label: "Amount",
                    fieldname: "amount",
                    fieldtype: "Currency",
                    reqd: 1,
                    default: outstanding
                }
            ],
            primary_action_label: "Create Payment",
            primary_action(values) {

                if (values.amount > outstanding) {
                    frappe.msgprint("Amount cannot exceed outstanding amount");
                    return;
                }

                frappe.call({
                    method: "omeir_motors.omeir_motors.doctype.subcontract_invoice.subcontract_invoice.make_payment_entry",
                    args: {
                        invoice: frm.doc.name,
                        mode_of_payment: values.mode_of_payment,
                        amount: values.amount
                    },
                    callback(r) {
                        if (r.message) {
                            d.hide();
                            frappe.msgprint({
                                title: __("Payment Created"),
                                message: __("Journal Entry {0} created successfully.", [r.message]),
                                indicator: "green"
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }
        });

        d.show();
    });
}