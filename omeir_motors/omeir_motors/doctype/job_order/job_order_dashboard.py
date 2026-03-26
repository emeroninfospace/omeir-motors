from frappe import _

def get_data(data=None):
	return {
		"fieldname": "job_order",

		"non_standard_fieldnames": {
			"Vehicle Log": "custom_job_order",
			"Technician Allocation": "job_order",
			"Sales Invoice": "custom_job_order"
		},

		"internal_links": {
			"Vehicle Log": [],
			"Technician Allocation": [],
			"Sales Invoice": []
		},

		"transactions": [
			{
				"label": _("Vehicle"),
				"items": ["Vehicle Log"]
			},
			{
				"label": _("Sales Invoice"),
				"items": ["Sales Invoice"]
			},
			{
				"label": _("Technician Allocation"),
				"items": ["Technician Allocation"]
			}
		]
	}