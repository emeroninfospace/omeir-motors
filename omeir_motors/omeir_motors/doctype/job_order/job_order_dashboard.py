from frappe import _

def get_data(data=None):
	return {
		"fieldname": "job_order",

		"non_standard_fieldnames": {
			"Vehicle Log": "custom_job_order",
			"Technician Allocation": "job_order"
		},

		"transactions": [
			{
				"label": _("Vehicle"),
				"items": ["Vehicle Log"]
			},
			{
				"label": _("Technician Allocation"),
				"items": ["Technician Allocation"]
			}
		]
	}