frappe.ui.form.on('Sales Invoice', {
    custom_invoice_type: function(frm) {
        if (frm.doc.custom_payment_type && frm.doc.custom_invoice_type) {
            frm.trigger('custom_payment_type');
        }
    },

    custom_payment_type: function(frm) {
        const naming_series_map = {
            'Job Card Invoice': {
                'CREDIT': 'BOM-SICR-.YYYY.-.####',
                'CASH': 'BOM-SICS-.YYYY.-.####',
                'WARRANTY': 'BOM-SIWR-.YYYY.-.####',
                'INSURANCE': 'BOM-SIIN-.YYYY.-.####'
            },
            'Notification Invoice': {
                'CREDIT': 'BOM-SNCR-.YYYY.-.####',
                'CASH': 'BOM-SNCS-.YYYY.-.####'
            },
            'Counter Invoice': {
                'CREDIT': 'BOM-CSCR-.YYYY.-.####',
                'CASH': 'BOM-CSCS-.YYYY.-.####'
            }
        };

        const invoice_type = frm.doc.custom_invoice_type;
        const payment_type = frm.doc.custom_payment_type;
        const series = naming_series_map[invoice_type]?.[payment_type];

        if (series) {
            frm.set_value('naming_series', series);
        }
    },

    refresh: function(frm) {
        if (frm.doc.custom_payment_type && !frm.doc.naming_series) {
            frm.trigger('custom_payment_type');
        }
    },

    additional_discount_percentage: function(frm) {
        validate_discount_limit(frm);
    },

    discount_amount: function(frm) {
        validate_discount_limit(frm);
    },
    before_submit: function(frm) {
        if (!frm.doc.custom_job_order) return;

        return new Promise(function(resolve, reject) {
            frappe.call({
                method: 'omeir_motors.omeir_motors.doctype.job_order.job_order.validate_invoice_items_match',
                args: {
                    job_order: frm.doc.custom_job_order,
                    sales_invoice: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.mismatches && r.message.mismatches.length) {
                        var msg = '<b>The following items do not match the Job Order:</b><br><br>';
                        r.message.mismatches.forEach(function(m) {
                            msg += '&bull; ' + m + '<br>';
                        });
                        msg += '<br>Use the <b>Sync to Sales Invoice</b> button on the Job Order to fix this before submitting.';

                        frappe.msgprint({
                            title: __('Item Mismatch with Job Order'),
                            message: msg,
                            indicator: 'red'
                        });
                        reject();
                    } else {
                        resolve();
                    }
                }
            });
        });
    }
});

function validate_discount_limit(frm) {
    let discount = frm.doc.additional_discount_percentage || 0;
    if (discount <= 0) return;

    frappe.call({
        method: "omeir_motors.omeir_motors.api.sales_invoice.validate_discount",
        args: { discount_percentage: discount },
        callback: function(r) {
            if (r.message && !r.message.allowed) {
                frappe.msgprint({
                    title: __("Discount Limit Exceeded"),
                    message: __(r.message.message),
                    indicator: "red"
                });
                frm.set_value("additional_discount_percentage", r.message.max_discount);
            }
        }
    });
}


    

