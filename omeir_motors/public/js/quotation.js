frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        
        if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
            frm.add_custom_button(__('Job Order'), function() {
                frappe.model.open_mapped_doc({
                    method: "omeir_motors.overrides.quotation.create_job_order",
                    frm: frm,
                    freeze_message: __("Creating Job Order...")
                });
            }, __('Create'));
            setTimeout(() => {
            frm.remove_custom_button('Sales Order', 'Create');
            }, 10);
        }
    }
});