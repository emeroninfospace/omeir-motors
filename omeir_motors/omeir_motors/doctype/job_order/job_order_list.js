frappe.listview_settings['Job Order'] = {
    add_fields: ["status"],

    get_indicator: function(doc) {

        if (doc.status === "Completed") {
            return ["Completed", "green"];
        } 
        else if (doc.status === "In Progress") {
            return ["In Progress", "orange"];
        } 
        else {
            return ["Pending", "red"];
        }
    }
};