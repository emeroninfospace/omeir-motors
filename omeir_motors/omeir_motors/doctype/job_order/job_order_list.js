frappe.listview_settings['Job Order'] = {
    add_fields: ["status"],

    get_indicator: function(doc) {
        if (doc.status === "Completed") {
            return ["Completed", "green", "status,=,Completed"];
        } else if (doc.status === "In Progress") {
            return ["In Progress", "orange", "status,=,In Progress"];
        } else {
            return ["Pending", "red", "status,=,Pending"];
        }
    }
};