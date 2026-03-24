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
        if (!frm.is_new()) {
			frm.add_custom_button('Service Notification', () => {
				frappe.call({
					method: 'omeir_motors.overrides.quotation.create_from_quotation',
					args: {
						quotation: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'Service Notification', r.message);
						}
					}
				});
			}, 'Create');
		}
        
    }
});