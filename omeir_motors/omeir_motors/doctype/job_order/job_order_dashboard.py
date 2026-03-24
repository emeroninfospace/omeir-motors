from frappe import _

def get_data(data=None):
	return {
		"fieldname": "name",

		"non_standard_fieldnames": {
			"Vehicle Log": "custom_job_order"
		},

		"transactions": [
			{
				"label": _("Vehicle"),
				"items": ["Vehicle Log"]
			}
		]
	}