frappe.listview_settings['Subcontract Work Order'] = {
    add_fields: ["status"],

    get_indicator: function(doc) {
        if (doc.status === "Draft") {
            return ["Draft", "gray", "status,=,Draft"];
        } else if (doc.status === "To Receive and Bill") {
            return ["To Receive and Bill", "orange", "status,=,To Receive and Bill"];
        } else if (doc.status === "To Bill") {
            return ["To Bill", "blue", "status,=,To Bill"];
        } else if (doc.status === "Partially Billed") {
            return ["Partially Billed", "yellow", "status,=,Partially Billed"];
        } else if (doc.status === "Paid") {
            return ["Paid", "green", "status,=,Paid"];
        }
    }
};