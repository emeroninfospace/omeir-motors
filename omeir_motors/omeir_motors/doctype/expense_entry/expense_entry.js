// Copyright (c) 2026, emeron and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Entry", {
    onload: function(frm) {
        frm.set_query("account", "items", function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
        
        frm.set_query("account_from", "items", function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
        frm.set_query("party_type", "items", function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
                filters: {
                    account: row.account,
                    company: doc.company
                },
            };
        });
    },
    refresh: function(frm) {
        // Set query filters for account and account_from fields in items table
        
        if (frm.doc.docstatus === 1 && !frm.is_new() && !frm.doc.journal_entry) {
            frm.add_custom_button(__("Make Payment"), function() {
                frappe.confirm(
                    __("Are you sure you want to create and submit a Journal Entry for this Expense Entry?"),
                    function() {
                        frm.call({
                            method: "make_journal_entry",
                            doc: frm.doc,
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __("Success"),
                                        message: __("Journal Entry {0} created and submitted successfully", [r.message]),
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            });
        }
    }
});

frappe.ui.form.on('Expense Entry Item', {
    account: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
    },
    party: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.party_type && row.party) {
            // Fetch tax_id from the party document based on party_type
            frappe.db.get_value(row.party_type, row.party, "tax_id")
                .then(function(r) {
                    if (r && r.message && r.message.tax_id) {
                        frappe.model.set_value(cdt, cdn, "trn", r.message.tax_id);
                    } else {
                        frappe.model.set_value(cdt, cdn, "trn", "");
                    }
                })
                .catch(function(error) {
                    console.error("Error fetching tax_id:", error);
                    frappe.model.set_value(cdt, cdn, "trn", "");
                });
        } else {
            frappe.model.set_value(cdt, cdn, "trn", "");
        }
    },
    party_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Clear party and trn when party_type changes
        if (!row.party_type) {
            frappe.model.set_value(cdt, cdn, "party", "");
            frappe.model.set_value(cdt, cdn, "trn", "");
        } else if (row.party) {
            // If party is already set, fetch tax_id again
            frappe.db.get_value(row.party_type, row.party, "tax_id")
                .then(function(r) {
                    if (r && r.message && r.message.tax_id) {
                        frappe.model.set_value(cdt, cdn, "trn", r.message.tax_id);
                    } else {
                        frappe.model.set_value(cdt, cdn, "trn", "");
                    }
                })
                .catch(function(error) {
                    console.error("Error fetching tax_id:", error);
                    frappe.model.set_value(cdt, cdn, "trn", "");
                });
        }
    },
    amount: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },
    
    vat_percentage: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },
    
    items_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_row_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (row.amount && row.vat_percentage) {
        row.vat_amount = flt(row.amount * row.vat_percentage / 100);
        row.total_amount = flt(row.amount) + flt(row.vat_amount);
    } else {
        row.vat_amount = 0;
        row.total_amount = flt(row.amount);
    }
    
    frm.refresh_field('items');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_amount = 0;
    let total_vat = 0;
    
    frm.doc.items.forEach(function(item) {
        total_amount += flt(item.amount);
        total_vat += flt(item.vat_amount);
    });
    
    frm.set_value('total_amount', total_amount);
    frm.set_value('total_vat', total_vat);
    frm.set_value('grand_total', total_amount + total_vat);
}