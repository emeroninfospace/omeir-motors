import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.utils import now_datetime

class CustomSalesInvoice(SalesInvoice):

    def on_submit(self):
        super().on_submit()  

        if self.custom_job_order:
            job_order = frappe.get_doc("Job Order", self.custom_job_order)

            if job_order.status != "Completed":
                job_order.db_set("status", "Completed")
