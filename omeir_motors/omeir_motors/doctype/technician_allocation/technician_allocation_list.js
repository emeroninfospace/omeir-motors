frappe.listview_settings['Technician Allocation'] = {
    get_indicator: function(doc) {
        if (doc.status === "Completed") {
            return ["Completed", "green", "status,=,Completed"];
        } else if (doc.status === "Pending") {
            return ["Pending", "orange", "status,=,Pending"];
        }
    }
};