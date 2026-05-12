// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prepaid Expense", {
    refresh: function(frm) {
        const status_colors = {
            "Active": "blue",
            "Completed": "green",
            "Draft": "gray"
        };
        if (frm.doc.status && status_colors[frm.doc.status]) {
            frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
        }

        toggle_employee_fields(frm);

        if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
            frm.add_custom_button(__("Close Prepaid Expense"), function() {
                frappe.confirm(
                    __("Are you sure you want to close this Prepaid Expense? The remaining amount of <strong>{0}</strong> will be written off to the Expense Account immediately. This action cannot be undone.", [
                        format_currency(frm.doc.remaining_amount)
                    ]),
                    function() {
                        frappe.call({
                            method: "omeir_motors.omeir_motors.doctype.prepaid_expense.prepaid_expense.close_prepaid_expense",
                            args: { name: frm.doc.name },
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __("Closed Successfully"),
                                        message: __("Remaining amount written off via Journal Entry {0}.", [r.message]),
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("Actions"));
        }

        frm.set_query("prepaid_account", function() {
            return { filters: { company: frm.doc.company, is_group: 0 } };
        });

        frm.set_query("expense_account", function() {
            return { filters: { company: frm.doc.company, is_group: 0 } };
        });

        frm.set_query("payable_account", function() {
            if (frm.doc.type === "Rent") {
                return {
                    filters: {
                        company: frm.doc.company,
                        is_group: 0,
                        account_type: ["not in", ["Receivable", "Payable"]]
                    }
                };
            }
            return { filters: { company: frm.doc.company, is_group: 0 } };
        });

        frm.set_query("employee", function() {
            return { filters: { status: "Active" } };
        });
    },

    type: function(frm) {
        toggle_employee_fields(frm);
        frm.set_value("employee", null);
        frm.set_value("employee_name", null);
        frm.set_value("payable_account", null);
        frm.refresh_field("payable_account");
    },

    total_amount: function(frm) {
        calculate_monthly(frm);
    },

    number_of_months: function(frm) {
        calculate_monthly(frm);
    }
});

function toggle_employee_fields(frm) {
    let is_expense = frm.doc.type === "Expense";
    let is_rent = frm.doc.type === "Rent";

    frm.set_df_property("employee", "hidden", !is_expense);
    frm.set_df_property("employee_name", "hidden", !is_expense);
    frm.set_df_property("employee", "reqd", is_expense);

    frm.set_df_property("payable_account", "hidden", is_rent);
    frm.set_df_property("payable_account", "reqd", is_expense);
}

function calculate_monthly(frm) {
    if (frm.doc.total_amount && frm.doc.number_of_months && frm.doc.number_of_months > 0) {
        let monthly = flt(frm.doc.total_amount / frm.doc.number_of_months, 2);
        frm.set_value("monthly_amount", monthly);
        frm.set_value("remaining_amount", frm.doc.total_amount);
    }
}