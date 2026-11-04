// Adds a "Payment Request Voucher" button to ERPNext's Accounts Payable report.
// The report's own script assigns frappe.query_reports["Accounts Payable"] when it loads,
// so a setter on that key lets us extend it without copying the ERPNext report.
(() => {
	const REPORT_NAME = "Accounts Payable";
	let report_settings;

	frappe.provide("frappe.query_reports");
	Object.defineProperty(frappe.query_reports, REPORT_NAME, {
		configurable: true,
		enumerable: true,
		get: () => report_settings,
		set: (settings) => {
			report_settings = extend_report_settings(settings);
		},
	});

	function extend_report_settings(settings) {
		if (!settings || settings.__omeir_payment_request_voucher) {
			return settings;
		}
		settings.__omeir_payment_request_voucher = true;

		const get_datatable_options = settings.get_datatable_options;
		settings.get_datatable_options = (options) => {
			options = get_datatable_options ? get_datatable_options(options) : options;
			return Object.assign(options, { checkboxColumn: true });
		};

		const onload = settings.onload;
		settings.onload = (report) => {
			onload && onload(report);
			report.page.add_inner_button(__("Payment Request Voucher"), () =>
				show_voucher_dialog(report)
			);
		};

		return settings;
	}

	function show_voucher_dialog(report) {
		const invoices = get_open_invoices(report);
		if (!invoices.length) {
			frappe.msgprint(
				__("Tick the Purchase Invoices to include, or filter the report to one supplier.")
			);
			return;
		}

		const suppliers = [...new Set(invoices.map((row) => row.party))];
		if (suppliers.length > 1) {
			frappe.msgprint(__("Select invoices of one supplier only."));
			return;
		}

		const company = report.get_filter_value("company");
		const dialog = new frappe.ui.Dialog({
			title: __("Payment Request Voucher"),
			size: "large",
			fields: [
				{
					fieldname: "supplier",
					label: __("Supplier"),
					fieldtype: "Data",
					read_only: 1,
					default: invoices[0].party_name || invoices[0].party,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "mode_of_payment",
					label: __("Payment Mode"),
					fieldtype: "Link",
					options: "Mode of Payment",
					default: "Bank Transfer",
				},
				{
					fieldname: "paid_from",
					label: __("Paid From"),
					fieldtype: "Link",
					options: "Account",
					get_query: () => ({
						filters: { company, account_type: ["in", ["Bank", "Cash"]], is_group: 0 },
					}),
				},
				{ fieldtype: "Section Break" },
				{
					fieldname: "invoices",
					label: __("Invoices"),
					fieldtype: "Table",
					cannot_add_rows: true,
					in_place_edit: true,
					data: invoices.map((row) => ({
						invoice: row.voucher_no,
						bill_no: row.bill_no,
						outstanding: row.outstanding,
						amount: row.outstanding,
					})),
					fields: [
						{
							fieldname: "invoice",
							label: __("Purchase Invoice"),
							fieldtype: "Link",
							options: "Purchase Invoice",
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "bill_no",
							label: __("Invoice No"),
							fieldtype: "Data",
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "outstanding",
							label: __("Outstanding"),
							fieldtype: "Currency",
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "amount",
							label: __("Payment Amount"),
							fieldtype: "Currency",
							in_list_view: 1,
							reqd: 1,
						},
					],
				},
			],
			primary_action_label: __("Print"),
			primary_action(values) {
				const rows = (values.invoices || []).filter((row) => flt(row.amount) > 0);
				if (!rows.length) {
					frappe.msgprint(__("Enter a Payment Amount for at least one invoice."));
					return;
				}
				const too_much = rows.find((row) => flt(row.amount) > flt(row.outstanding));
				if (too_much) {
					frappe.msgprint(
						__("Payment Amount for {0} is more than its outstanding amount.", [
							too_much.invoice,
						])
					);
					return;
				}

				const args = {
					invoices: JSON.stringify(
						rows.map((row) => ({ invoice: row.invoice, amount: row.amount }))
					),
					paid_from: values.paid_from || "",
					mode_of_payment: values.mode_of_payment || "",
				};
				window.open(
					frappe.urllib.get_full_url(
						"/api/method/omeir_motors.omeir_motors.api.payment_request_voucher.download_payment_request_voucher?" +
							new URLSearchParams(args).toString()
					)
				);
				dialog.hide();
			},
		});

		if (company) {
			frappe.db.get_value("Company", company, "default_bank_account").then((r) => {
				const account = r.message && r.message.default_bank_account;
				if (account && !dialog.get_value("paid_from")) {
					dialog.set_value("paid_from", account);
				}
			});
		}
		dialog.show();
	}

	function get_open_invoices(report) {
		const is_open_invoice = (row) =>
			row && row.voucher_type === "Purchase Invoice" && row.voucher_no && flt(row.outstanding) > 0;

		const checked = report.datatable ? report.get_checked_items().filter(is_open_invoice) : [];
		if (checked.length) {
			return checked;
		}
		// Nothing ticked: use every open invoice in the report, which works when it is filtered to one supplier.
		return (report.data || []).filter(is_open_invoice);
	}
})();
