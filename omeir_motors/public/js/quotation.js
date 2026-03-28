frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        
        // if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
        //     frm.add_custom_button(__('Job Order'), function() {
        //         frappe.model.open_mapped_doc({
        //             method: "omeir_motors.overrides.quotation.create_job_order",
        //             frm: frm,
        //             freeze_message: __("Creating Job Order...")
        //         });
        //     }, __('Create'));
        //     setTimeout(() => {
        //     frm.remove_custom_button('Sales Order', 'Create');
        //     }, 10);
        // }
        if (frm.doc.docstatus === 1 && !frm.doc.custom_material_request) {

            frm.add_custom_button('Material Request', () => {
                frappe.call({
                    method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.make_material_request',
                    args: {
                        quotation: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            let doc = frappe.model.sync(r.message)[0];
                            frappe.set_route('Form', doc.doctype, doc.name);
                        }
                    }
                });
            }, 'Create');
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
        
    },
     party_name: function(frm) {
        if (frm.doc.party_name) {
            frappe.db.get_value('Customer', frm.doc.party_name, 'custom_type')
                .then(r => {
                    frm.set_value('custom_type', (r.message && r.message.custom_type) || '');
                });
        }
    }
});