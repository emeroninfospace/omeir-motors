frappe.listview_settings['Expense Entry'] = {
    add_fields: ["status", "grand_total", "journal_entry"],
    
    get_indicator: function(doc) {
        if (doc.status === "Paid") {
            return [__("Paid"), "green", "status,=,Paid"];
        } else if (doc.status === "Unpaid") {
            return [__("Unpaid"), "orange", "status,=,Unpaid"];
        } else if (doc.docstatus === 0) {
            return [__("Draft"), "red", "docstatus,=,0"];
        } else if (doc.docstatus === 2) {
            return [__("Cancelled"), "red", "docstatus,=,2"];
        }
    },
    
    onload: function(listview) {
        // Optional: Add custom buttons or filters if needed
    }
};