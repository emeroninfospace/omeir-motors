frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.custom_job_order) {

        frm.add_custom_button('Job Order', () => {

            frappe.new_doc('Job Order', {}, (doc) => {

                doc.customer = frm.doc.party_name;
                doc.company = frm.doc.company;
                doc.quotation = frm.doc.name;
                doc.vehicle = frm.doc.custom_vehicle

                let item_codes = (frm.doc.items || []).map(i => i.item_code);

                if (!item_codes.length) return;

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Item",
                        filters: {
                            name: ["in", item_codes]
                        },
                        fields: ["name", "is_stock_item"]
                    },
                    callback: function(r) {

                        let item_map = {};
                        (r.message || []).forEach(i => {
                            item_map[i.name] = i.is_stock_item;
                        });

                        (frm.doc.items || []).forEach(item => {

                            if (!item.item_code) return;

                            if (item_map[item.item_code]) {

                                let row = frappe.model.add_child(doc, "job_order_items");

                                row.item_code = item.item_code;
                                row.item_name = item.item_name;
                                row.uom = item.uom;
                                row.quantity = item.qty;
                                row.rate = item.rate;
                                row.amount = item.amount;


                            } else {

                                let row = frappe.model.add_child(doc, "service_item");

                                row.item_code = item.item_code;
                                row.item_name = item.item_name;
                                row.uom = item.uom;
                                row.quantity = item.qty;
                                row.rate = item.rate;
                                row.amount = item.amount;

                            }

                        });
                        cur_frm.refresh_fields();  
                        cur_frm.refresh_field('job_order_items');
                        cur_frm.refresh_field('service_item');
                    }
                });

            });

    }, 'Create');
}
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