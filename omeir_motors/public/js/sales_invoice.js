frappe.ui.form.on('Sales Invoice', {
    custom_payment_type: function(frm) {
        if (frm.doc.custom_payment_type == 'CREDIT') {
            frm.set_value('naming_series', 'BOM-SICR-.YYYY.-.####');
        }
        else if (frm.doc.custom_payment_type == 'CASH') {
            frm.set_value('naming_series', 'BOM-SICS-.YYYY.-.####');
        }
        else if (frm.doc.custom_payment_type == 'WARRANTY') {
            frm.set_value('naming_series', 'BOM-SIWR-.YYYY.-.####');
        }
        else if (frm.doc.custom_payment_type == 'INSURANCE') {
            frm.set_value('naming_series', 'BOM-SIIN-.YYYY.-.####');
        }
    },
    
    refresh: function(frm) {
        if (frm.doc.custom_payment_type && !frm.doc.naming_series) {
            frm.trigger('custom_payment_type');
        }
    }
});