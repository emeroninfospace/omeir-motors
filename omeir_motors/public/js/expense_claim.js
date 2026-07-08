frappe.ui.form.on('Expense Claim Detail', {
    amount: function(frm, cdt, cdn) {
        update_row_total(frm, cdt, cdn);
    },
    custom_tax_amount: function(frm, cdt, cdn) {
        update_row_total(frm, cdt, cdn);
    }
});

function update_row_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let row_total = flt(row.amount) + flt(row.custom_tax_amount);
    frappe.model.set_value(cdt, cdn, 'custom_total_amount', row_total);
    frappe.model.set_value(cdt, cdn, 'sanctioned_amount', row_total);
    calculate_total_claimed(frm);
}

function calculate_total_claimed(frm) {
    let total = 0;
    (frm.doc.expenses || []).forEach(function(row) {
        total += flt(row.amount) + flt(row.custom_tax_amount);
    });
    frm.set_value('total_claimed_amount', flt(total, precision('total_claimed_amount')));
}
