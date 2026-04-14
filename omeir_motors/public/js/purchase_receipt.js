frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {

        if (frm.doc.docstatus === 1) {

            frm.add_custom_button(__('Expense Entry'), function() {

                frappe.new_doc('Expense Entry', {
                    custom_purchase_reference: frm.doc.name,
                    supplier: frm.doc.supplier,
                    posting_date: frappe.datetime.get_today()
                    
                });

            }, __('Create'));
        }
    }
});