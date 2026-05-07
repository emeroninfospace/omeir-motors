// Copyright (c) 2026, Emeron Infospace and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Service Log"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
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
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
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
			options: "\nDraft\nPending\nCompleted",
		},
	],

	get_chart_data: function (columns, result) {
		if (!result || !result.length) return null;

		var employeeMap = {};

		result.forEach(function (row) {
			var emp = row.employee_name || row.employee || "Unknown";
			if (!employeeMap[emp]) {
				employeeMap[emp] = {
					actual_seconds: 0,
					estimated_hours: 0,
					count: 0,
				};
			}
			employeeMap[emp].actual_seconds += row.total_duration || 0;
			employeeMap[emp].estimated_hours += parseFloat(row.estimated_time) || 0;
			employeeMap[emp].count += 1;
		});

		var labels = Object.keys(employeeMap);
		var actualHours = labels.map(function (emp) {
			return parseFloat((employeeMap[emp].actual_seconds / 3600).toFixed(2));
		});
		var estimatedHours = labels.map(function (emp) {
			return parseFloat(employeeMap[emp].estimated_hours.toFixed(2));
		});

		return {
			data: {
				labels: labels,
				datasets: [
					{
						name: "Actual Hours",
						values: actualHours,
						chartType: "bar",
					},
					{
						name: "Estimated Hours",
						values: estimatedHours,
						chartType: "bar",
					},
				],
			},
			type: "bar",
			colors: ["#1a7a4a", "#92400e"],
			barOptions: {
				spaceRatio: 0.3,
			},
			axisOptions: {
				xAxisMode: "tick",
				yAxisMode: "span",
			},
			tooltipOptions: {
				formatTooltipY: function (val) {
					return (val || 0).toFixed(2) + " hrs";
				},
			},
			title: "Actual vs Estimated Hours by Employee",
			height: 280,
		};
	},
};