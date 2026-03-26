// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technician Allocation", {
	refresh(frm) {
        if (frm.doc.status === "Completed") {
            frm.page.set_indicator('Completed', 'green');
        }
	},
});
