frappe.listview_settings['Subcontract Invoice'] = {
    add_fields: ["status", "grand_total", "paid_amount", "supplier", "company"],

    get_indicator: function(doc) {
        if (doc.status === "Paid") {
            return [__("Paid"), "green", "status,=,Paid"];
        } else if (doc.status === "Partially Paid") {
            return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
        } else if (doc.status === "Unpaid") {
            return [__("Unpaid"), "red", "status,=,Unpaid"];
        } else if (doc.status === "Cancelled" || doc.docstatus === 2) {
            return [__("Cancelled"), "red", "status,=,Cancelled"];
        } else {
            return [__("Draft"), "gray", "status,=,Draft"];
        }
    },

    onload: function(listview) {
        listview.page.add_inner_button(__("Make Payment (Multiple Invoices)"), () => {
            show_multi_payment_dialog(listview);
        });
    }
};

function show_multi_payment_dialog(listview) {
    let d = new frappe.ui.Dialog({
        title: "Make Payment",
        size: "extra-large",
        fields: [
            {
                label: "Supplier",
                fieldname: "supplier",
                fieldtype: "Link",
                options: "Supplier",
                reqd: 1
            },
            {
                label: "Posting Date",
                fieldname: "posting_date",
                fieldtype: "Date",
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: "Mode of Payment",
                fieldname: "mode_of_payment",
                fieldtype: "Link",
                options: "Mode of Payment",
                reqd: 1
            },
            {
                fieldtype: "Section Break"
            },
            {
                label: "Outstanding Invoices",
                fieldname: "invoices",
                fieldtype: "Table",
                cannot_add_rows: true,
                in_place_edit: true,
                data: [],
                fields: [
                    {
                        label: "Invoice",
                        fieldname: "invoice",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 3
                    },
                    {
                        label: "Grand Total",
                        fieldname: "grand_total",
                        fieldtype: "Currency",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    },
                    {
                        label: "Outstanding",
                        fieldname: "outstanding_amount",
                        fieldtype: "Currency",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    },
                    {
                        label: "Pay",
                        fieldname: "pay",
                        fieldtype: "Check",
                        in_list_view: 1,
                        columns: 1
                    },
                    {
                        label: "Amount to Pay",
                        fieldname: "amount",
                        fieldtype: "Currency",
                        in_list_view: 1,
                        columns: 2
                    }
                ]
            }
        ],
        primary_action_label: "Create Payment",
        primary_action(values) {
            let selected = d.get_value("invoices").filter(row => row.pay && flt(row.amount) > 0);

            if (!selected.length) {
                frappe.msgprint("Select at least one invoice and enter an amount to pay");
                return;
            }

            let allocations = selected.map(row => ({
                invoice: row.invoice,
                amount: row.amount
            }));

            frappe.call({
                method: "omeir_motors.omeir_motors.doctype.subcontract_invoice.subcontract_invoice.make_payment_entry_multi",
                args: {
                    invoices: allocations,
                    mode_of_payment: values.mode_of_payment,
                    posting_date: values.posting_date
                },
                freeze: true,
                freeze_message: "Creating Payment...",
                callback(r) {
                    if (r.message) {
                        d.hide();
                        frappe.show_alert({
                            message: `Journal Entry <b>${r.message}</b> created successfully.`,
                            indicator: "green"
                        }, 7);
                        listview.refresh();
                    }
                }
            });
        }
    });

    d.fields_dict.supplier.df.onchange = () => {
        let supplier = d.get_value("supplier");
        if (!supplier) return;

        frappe.call({
            method: "omeir_motors.omeir_motors.doctype.subcontract_invoice.subcontract_invoice.get_outstanding_invoices",
            args: { supplier },
            callback(r) {
                let rows = (r.message || []).map(inv => ({
                    invoice: inv.name,
                    grand_total: inv.grand_total,
                    outstanding_amount: inv.outstanding_amount,
                    pay: 1,
                    amount: inv.outstanding_amount
                }));

                d.fields_dict.invoices.df.data = rows;
                d.fields_dict.invoices.grid.refresh();

                if (!rows.length) {
                    frappe.show_alert({
                        message: "No outstanding invoices found for this supplier",
                        indicator: "orange"
                    });
                }
            }
        });
    };

    d.show();
}