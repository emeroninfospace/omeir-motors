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
    }
});