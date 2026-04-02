frappe.listview_settings['Job Order'] = {
    add_fields: ["status", "docstatus"],

    onload: function(listview) {
        setTimeout(() => {
            if (listview.page.sidebar) {
                listview.page.sidebar.hide();
            }
        }, 100);
    },

    get_indicator: function(doc) {

        if (doc.docstatus === 2) {
            return ["Cancelled", "red"];
        }

        if (doc.docstatus === 0) {
            return ["Draft", "grey"];
        }

        if (doc.status === "Completed") {
            return ["Completed", "green"];
        } 
        else if (doc.status === "Pending") {
            return ["Pending", "orange"];
        } 
        else {
            return ["Pending", "orange"];
        }
    }
};