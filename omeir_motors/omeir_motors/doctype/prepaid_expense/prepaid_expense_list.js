frappe.listview_settings['Prepaid Expense'] = {
    add_fields: ["status", "type", "total_amount", "remaining_amount"],

    get_indicator: function(doc) {
        if (doc.status === "Active") {
            return [__("Active"), "blue", "status,=,Active"];
        } else if (doc.status === "Completed") {
            return [__("Completed"), "green", "status,=,Completed"];
        } else if (doc.status === "Draft") {
            return [__("Draft"), "gray", "status,=,Draft"];
        }
    }
};