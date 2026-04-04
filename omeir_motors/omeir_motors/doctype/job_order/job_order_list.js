frappe.listview_settings['Job Order'] = {
    add_fields: ["status", "docstatus"],

    onload: function(listview) {
        setTimeout(() => {
            if (listview.page.sidebar) {
                listview.page.sidebar.hide();
            }
        }, 100);

      listview.page.add_action_item('Create Sales Invoice', function() {

            let selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint("Please select at least one Job Order");
                return;
            }

            let invalid_docs = selected.filter(doc => doc.docstatus !== 1);

            if (invalid_docs.length) {
                frappe.throw(
                    "Only Submitted Job Orders can be used.\nInvalid: " +
                    invalid_docs.map(d => d.name).join(", ")
                );
            }

            let non_pending = selected.filter(doc => doc.status !== "Pending");

            if (non_pending.length) {
                frappe.throw(
                    "Only Pending Job Orders allowed.\nInvalid: " +
                    non_pending.map(d => d.name).join(", ")
                );
            }

            // 👉 Now open dialog (same as before)
            let dialog = new frappe.ui.Dialog({
                title: 'Enter Payment Details',
                fields: [
                    {
                        label: 'Payment Type',
                        fieldname: 'custom_payment_type',
                        fieldtype: 'Select',
                        options: '\nCREDIT\nCASH\nWARRANTY\nINSURANCE',
                        reqd: 1
                    },
                    {
                        label: 'Due Date',
                        fieldname: 'due_date',
                        fieldtype: 'Date',
                        reqd: 1
                    },
                    {
                    label: 'Posting Date',
                    fieldname: 'posting_date',
                    fieldtype: 'Date',
                    reqd: 1,
                    default: frappe.datetime.get_today()
                }
                ],
                primary_action_label: 'Create',
                primary_action(values) {

                    let job_orders = selected.map(doc => doc.name);

                    frappe.call({
                        method: "omeir_motors.omeir_motors.doctype.job_order.job_order.make_bulk_sales_invoice",
                        args: {
                            job_orders: job_orders,
                            payment_type: values.custom_payment_type,
                            due_date: values.due_date,
                            posting_date: values.posting_date
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.msgprint("Sales Invoices Created Successfully");

                                frappe.set_route('List', 'Sales Invoice', {
                                    name: ['in', r.message]
                                });
                            }
                        }
                    });

                    dialog.hide();
                }
            });

            dialog.show();
        });
    },

    get_indicator: function(doc) {
        if (doc.docstatus === 2) return ["Cancelled", "red"];
        if (doc.docstatus === 0) return ["Draft", "grey"];
        if (doc.status === "Completed") return ["Completed", "green"];
        return ["Pending", "orange"];
    }
};