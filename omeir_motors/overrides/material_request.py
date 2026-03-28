import frappe
from frappe.model.document import Document

class CustomMaterialRequest(Document):

    def on_submit(self):
        if self.custom_job_order:
            frappe.db.set_value(
                "Job Order",
                self.custom_job_order,
                "material_request",
                self.name
            )