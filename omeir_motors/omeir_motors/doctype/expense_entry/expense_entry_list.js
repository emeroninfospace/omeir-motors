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
        listview.page.add_action_item(__("Make Payment"), function() {
            var selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint({
                    title: __("No Records Selected"),
                    message: __("Please select one or more Expense Entries."),
                    indicator: "orange"
                });
                return;
            }

            var unpaid = selected.filter(function(doc) {
                return doc.status === "Unpaid" && doc.docstatus === 1 && !doc.journal_entry;
            });

            if (!unpaid.length) {
                frappe.msgprint({
                    title: __("Nothing to Process"),
                    message: __("Selected records are either already Paid, not submitted, or already have a Journal Entry."),
                    indicator: "orange"
                });
                return;
            }

            frappe.confirm(
                __("Create Journal Entries for <strong>{0}</strong> Unpaid Expense {1}?", [
                    unpaid.length,
                    unpaid.length === 1 ? "Entry" : "Entries"
                ]),
                function() {
                    var success = 0;
                    var failed = [];
                    var processed = 0;

                    var finish = function() {
                        processed++;
                        if (processed < unpaid.length) return;

                        var msg = "";
                        if (success) {
                            msg += "<span style='color:green'>✔ " + success + " Journal " + (success === 1 ? "Entry" : "Entries") + " created successfully.</span>";
                        }
                        if (failed.length) {
                            msg += "<br><span style='color:red'>✘ Failed: " + failed.join(", ") + "</span>";
                        }

                        frappe.msgprint({
                            title: __("Make Payment — Results"),
                            message: msg,
                            indicator: success && !failed.length ? "green" : "orange"
                        });

                        listview.refresh();
                    };

                    unpaid.forEach(function(doc) {
                        frappe.call({
                            method: "omeir_motors.omeir_motors.doctype.expense_entry.expense_entry.make_payment_for_expense_entry",
                            args: { name: doc.name },
                            callback: function(r) {
                                if (r.message) {
                                    success++;
                                } else {
                                    failed.push(doc.name);
                                }
                                finish();
                            },
                            error: function() {
                                failed.push(doc.name);
                                finish();
                            }
                        });
                    });
                }
            );
        });
    }
};