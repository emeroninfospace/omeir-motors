from frappe import _
from erpnext.selling.doctype.quotation.quotation_dashboard import get_data as erpnext_get_data


def get_data(data=None):
	try:
		dashboard_data = erpnext_get_data()
	except TypeError:
		dashboard_data = erpnext_get_data(data)

	dashboard_data.setdefault("non_standard_fieldnames", {})
	dashboard_data["non_standard_fieldnames"].update({
		"Service Notification": "quotation"
	})

	dashboard_data["transactions"].append({
		"label": _("Service"),
		"items": ["Service Notification"]
	})

	return dashboard_data