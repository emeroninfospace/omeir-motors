frappe.listview_settings['Subcontract Invoice'] = {
    add_fields: ["status", "grand_total", "paid_amount"],

    get_indicator: function(doc) {
        if (doc.status === "Paid") {
            return [__("Paid"), "green", "status,=,Paid"];
        } else if (doc.status === "Partially Paid") {
            return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
        } else if (doc.status === "Unpaid") {
            return [__("Unpaid"), "red", "status,=,Unpaid"];
        } else if (doc.status === "Cancelled" || doc.docstatus === 2) {
            return [__("Cancelled"), "red", "status,=,Cancelled"];
        } else {
            return [__("Draft"), "gray", "status,=,Draft"];
        }
    }
};