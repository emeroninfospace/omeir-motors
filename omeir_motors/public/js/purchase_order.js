/** Match your Workflow State name exactly (as in Workflow → State). */
const PO_PRINT_ALLOWED_WORKFLOW_STATE = "Approved";

frappe.ui.form.on("Purchase Order", {
	setup(frm) {
		if (frm.__omeir_po_print_guard) {
			return;
		}
		frm.__omeir_po_print_guard = true;
		const _print = frm.print_doc.bind(frm);
		frm.print_doc = function () {
			if (po_print_requires_approve(frm) && frm.doc.workflow_state !== PO_PRINT_ALLOWED_WORKFLOW_STATE) {
				frappe.msgprint({
					title: __("Not Ready to Print"),
					message: __(
						"Print is available only when Workflow State is <b>{0}</b>. Current state: <b>{1}</b>.",
						[PO_PRINT_ALLOWED_WORKFLOW_STATE, frappe.utils.escape_html(frm.doc.workflow_state || __("Not set"))]
					),
					indicator: "orange",
				});
				return;
			}
			return _print();
		};
	},

	refresh(frm) {
		queue_toggle_po_print_visibility(frm);
	},

	workflow_state(frm) {
		queue_toggle_po_print_visibility(frm);
	},

	custom_invoice_ref(frm) {
		validate_duplicate_invoice_ref(frm, false);
	},

	supplier(frm) {
		if (frm.doc.custom_invoice_ref) {
			validate_duplicate_invoice_ref(frm, false);
		}
	},

	validate(frm) {
		return validate_duplicate_invoice_ref(frm, true);
	},
});

function po_print_requires_approve(frm) {
	return Boolean(frappe.meta.has_field(frm.doctype, "workflow_state"));
}

function queue_toggle_po_print_visibility(frm) {
	if (frm.is_new() || !po_print_requires_approve(frm)) {
		return;
	}
	const allowed = frm.doc.workflow_state === PO_PRINT_ALLOWED_WORKFLOW_STATE;
	frappe.after_ajax(() => {
		setTimeout(() => toggle_po_print_visibility(frm, allowed), 0);
	});
}

function toggle_po_print_visibility(frm, allowed) {
	if (!po_print_requires_approve(frm)) {
		return;
	}
	const t = frm.toolbar;
	if (t && t.print_icon && t.print_icon.length) {
		t.print_icon.toggleClass("hide", !allowed);
	}
	if (frm.page && frm.page.menu && frm.page.menu.length) {
		frm.page.menu.find("a.grey-link.dropdown-item").each(function () {
			const label = $(this).find(".menu-item-label").first().text().trim();
			if (label === __("Print") || label === "Print") {
				$(this).closest("li").toggleClass("hide", !allowed);
			}
		});
	}
}

function validate_duplicate_invoice_ref(frm, block_save) {
	const invoice_ref = (frm.doc.custom_invoice_ref || "").trim();
	if (!invoice_ref || !frm.doc.supplier) {
		return Promise.resolve();
	}

	return frappe.call({
		method: "omeir_motors.omeir_motors.api.purchase_order.check_duplicate_invoice_ref",
		args: {
			invoice_ref,
			supplier: frm.doc.supplier,
			name: frm.doc.name,
		},
	}).then((r) => {
		if (!r.message || !r.message.duplicate) {
			return;
		}

		frappe.msgprint({
			title: __("Duplicate Invoice Alert"),
			message: r.message.message,
			indicator: "red",
		});

		if (block_save) {
			frappe.validated = false;
		}
	});
}
