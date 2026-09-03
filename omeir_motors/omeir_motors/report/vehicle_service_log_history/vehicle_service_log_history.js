// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Service Log History"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "job_type",
			label: __("Job Type"),
			fieldtype: "Select",
			options: "\nNew\nRoutine Service\nWarranty\nInsurance Claim\nOther",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nPending\nCompleted\nCancelled",
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Print Log History"), function () {
			const f = report.get_values();

			frappe.call({
				method:
					"omeir_motors.omeir_motors.report.vehicle_service_log_history.vehicle_service_log_history.get_print_html",
				args: {
					vehicle: f.vehicle,
					customer: f.customer,
					from_date: f.from_date,
					to_date: f.to_date,
					job_type: f.job_type,
					status: f.status,
				},
				freeze: true,
				freeze_message: __("Building service log..."),
				callback: function (r) {
					if (!r.message) return;
					const w = window.open("", "_blank");
					w.document.write(
						"<html><head><title>Vehicle Service Log History - " +
							frappe.utils.escape_html(f.vehicle || f.customer || "All") +
							"</title></head><body>" +
							r.message +
							"</body></html>"
					);
					w.document.close();
					w.focus();
					setTimeout(function () {
						w.print();
					}, 400);
				},
			});
		});
	},
};
