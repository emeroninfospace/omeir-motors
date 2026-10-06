// Copyright (c) 2026, emeron and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Entry", {
    setup(frm) {
        const account_query = () => ({
            filters: { is_group: 0, company: frm.doc.company },
        });

        frm.set_query("account", "items", account_query);
        frm.set_query("account_from", "items", account_query);
        frm.set_query("tax_account", "items", account_query);

        frm.set_query("party_type", "items", (doc, cdt, cdn) => ({
            query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
            filters: { account: locals[cdt][cdn].account, company: doc.company },
        }));
    },

    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        if (frm.doc.journal_entry) {
            frm.add_custom_button(__("View Journal Entry"), () =>
                frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry)
            );
            return;
        }

        frm.add_custom_button(__("Make Payment"), () => {
            frappe.confirm(
                __("Are you sure you want to create and submit a Journal Entry for this Expense Entry?"),
                () =>
                    frm.call({
                        method: "make_journal_entry",
                        doc: frm.doc,
                        freeze: true,
                        freeze_message: __("Creating Journal Entry..."),
                        callback(r) {
                            if (!r.message) return;
                            frappe.show_alert({
                                message: __("Journal Entry {0} created and submitted", [r.message]),
                                indicator: "green",
                            });
                            frm.reload_doc();
                        },
                    })
            );
        }).addClass("btn-primary");
    },
});

frappe.ui.form.on("Expense Entry Item", {
    party: set_trn,

    party_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.party_type) {
            frappe.model.set_value(cdt, cdn, { party: "", trn: "" });
        } else if (row.party) {
            set_trn(frm, cdt, cdn);
        }
    },

    amount: calculate_row_total,
    vat_percentage: calculate_row_total,

    items_remove(frm) {
        calculate_totals(frm);
    },
});

async function set_trn(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    let trn = "";

    if (row.party_type && row.party) {
        try {
            const r = await frappe.db.get_value(row.party_type, row.party, "tax_id");
            trn = r?.message?.tax_id || "";
        } catch (e) {
            console.error("Error fetching tax_id:", e);
        }
    }

    frappe.model.set_value(cdt, cdn, "trn", trn);
}

function calculate_row_total(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const amount = flt(row.amount);
    const vat_amount = flt((amount * flt(row.vat_percentage)) / 100, precision("vat_amount", row));

    row.vat_amount = vat_amount;
    row.total_amount = flt(amount + vat_amount, precision("total_amount", row));

    frm.refresh_field("items");
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_amount = 0;
    let total_vat = 0;

    (frm.doc.items || []).forEach((item) => {
        total_amount += flt(item.amount);
        total_vat += flt(item.vat_amount);
    });

    frm.set_value({
        total_amount: total_amount,
        total_vat: total_vat,
        grand_total: total_amount + total_vat,
    });
}