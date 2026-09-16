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
        function get_eligible_selection() {
            var selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint({
                    title: __("No Records Selected"),
                    message: __("Please select one or more Expense Entries."),
                    indicator: "orange"
                });
                return null;
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
                return null;
            }

            return unpaid;
        }

        function prompt_posting_date(callback) {
            var d = new frappe.ui.Dialog({
                title: __("Journal Entry Details"),
                fields: [
                    {
                        fieldtype: "Date",
                        fieldname: "posting_date",
                        label: __("Posting Date"),
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        fieldtype: "Small Text",
                        fieldname: "remark",
                        label: __("Remark")
                    }
                ],
                primary_action_label: __("Create Journal Entry"),
                primary_action: function(values) {
                    d.hide();
                    callback(values.posting_date, values.remark);
                }
            });
            d.show();
        }

        // Option 1: Create a separate Journal Entry for each selected Expense Entry
        listview.page.add_action_item(__("Make Payment (Separate JV)"), function() {
            var unpaid = get_eligible_selection();
            if (!unpaid) return;

            prompt_posting_date(function(posting_date, remark) {
                frappe.confirm(
                    __("Create separate Journal Entries for <strong>{0}</strong> Unpaid Expense {1}?", [
                        unpaid.length,
                        unpaid.length === 1 ? "Entry" : "Entries"
                    ]),
                    function() {
                        frappe.call({
                            method: "omeir_motors.omeir_motors.doctype.expense_entry.expense_entry.make_payment_for_expense_entries",
                            args: {
                                names: unpaid.map(function(doc) { return doc.name; }),
                                payment_date: posting_date,
                                remark: remark
                            },
                            freeze: true,
                            freeze_message: __("Creating Journal Entries..."),
                            callback: function(r) {
                                var results = r.message || [];
                                var success = results.filter(function(row) { return row.success; }).length;
                                var failed = results.filter(function(row) { return !row.success; }).map(function(row) { return row.name; });

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
                            }
                        });
                    }
                );
            });
        });

        listview.page.add_action_item(__("Consolidate & Make Payment"), function() {
            var unpaid = get_eligible_selection();
            if (!unpaid) return;

            prompt_posting_date(function(posting_date, remark) {
                frappe.confirm(
                    __("Create <strong>one consolidated</strong> Journal Entry for <strong>{0}</strong> Unpaid Expense {1}? All selected entries must use the same 'Paid From' account.", [
                        unpaid.length,
                        unpaid.length === 1 ? "Entry" : "Entries"
                    ]),
                    function() {
                        frappe.call({
                            method: "omeir_motors.omeir_motors.doctype.expense_entry.expense_entry.make_consolidated_journal_entry",
                            args: {
                                names: unpaid.map(function(doc) { return doc.name; }),
                                posting_date: posting_date,
                                remark: remark
                            },
                            freeze: true,
                            freeze_message: __("Creating Consolidated Journal Entry..."),
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __("Success"),
                                        message: __("Consolidated Journal Entry <strong>{0}</strong> created and submitted for {1} Expense {2}.", [
                                            r.message,
                                            unpaid.length,
                                            unpaid.length === 1 ? "Entry" : "Entries"
                                        ]),
                                        indicator: "green"
                                    });
                                    listview.refresh();
                                }
                            }
                        });
                    }
                );
            });
        });
    }
};
