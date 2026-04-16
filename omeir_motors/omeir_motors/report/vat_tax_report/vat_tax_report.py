# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)

    if filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("From Date must be before To Date"))

    summary = get_summary(data, filters)
    return columns, data, None, None, summary


# ---------------------------------------------------------
# DATA - Consolidated into one method
# ---------------------------------------------------------

def get_data(filters):
    data = []
    transaction_type = filters.get("transaction_type", "All")

    # Sales Invoice Data
    if transaction_type in ["All", "Sales Invoice"]:
        si = frappe.qb.DocType("Sales Invoice")
        sit = frappe.qb.DocType("Sales Taxes and Charges")

        query = (
            frappe.qb.from_(si)
            .left_join(sit).on(si.name == sit.parent)
            .select(
                si.name.as_("voucher_no"),
                frappe.qb.terms.ValueWrapper("Sales Invoice").as_("transaction_type"),
                si.posting_date,
                si.customer_name.as_("party_name"),
                si.net_total,
                sit.tax_amount.as_("tax_amount"),
                sit.rate.as_("tax_rate"),
                sit.account_head.as_("tax_account"),
                si.grand_total,
                frappe.qb.terms.ValueWrapper(None).as_("vat_account")
            )
            .where(si.docstatus == 1)
        )

        if filters.get("from_date"):
            query = query.where(si.posting_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(si.posting_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(si.company == filters.get("company"))
        if filters.get("customer"):
            query = query.where(si.customer == filters.get("customer"))

        data.extend(query.run(as_dict=True))

    # Purchase Invoice Data
    if transaction_type in ["All", "Purchase Invoice"]:
        pi = frappe.qb.DocType("Purchase Invoice")
        pit = frappe.qb.DocType("Purchase Taxes and Charges")

        query = (
            frappe.qb.from_(pi)
            .left_join(pit).on(pi.name == pit.parent)
            .select(
                pi.name.as_("voucher_no"),
                frappe.qb.terms.ValueWrapper("Purchase Invoice").as_("transaction_type"),
                pi.posting_date,
                pi.supplier_name.as_("party_name"),
                pi.net_total,
                pit.tax_amount.as_("tax_amount"),
                pit.rate.as_("tax_rate"),
                pit.account_head.as_("tax_account"),
                pi.grand_total,
                frappe.qb.terms.ValueWrapper(None).as_("vat_account")
            )
            .where(pi.docstatus == 1)
        )

        if filters.get("from_date"):
            query = query.where(pi.posting_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(pi.posting_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(pi.company == filters.get("company"))
        if filters.get("supplier"):
            query = query.where(pi.supplier == filters.get("supplier"))

        data.extend(query.run(as_dict=True))

    # Expense Entry Data
    if transaction_type in ["All", "Expense Entry"]:
        ee = frappe.qb.DocType("Expense Entry")
        eei = frappe.qb.DocType("Expense Entry Item")

        query = (
            frappe.qb.from_(ee)
            .inner_join(eei)
            .on(ee.name == eei.parent)
            .select(
                ee.name.as_("voucher_no"),
                frappe.qb.terms.ValueWrapper("Expense Entry").as_("transaction_type"),
                ee.posting_date,
                eei.amount.as_("net_total"),
                eei.vat_amount.as_("tax_amount"),
                eei.vat_percentage.as_("tax_rate"),
                frappe.qb.terms.ValueWrapper(None).as_("tax_account"),
                eei.total_amount.as_("grand_total"),
                ee.journal_entry.as_("journal_entry_name")
            )
            .where(ee.docstatus == 1)
            .orderby(ee.posting_date, order=Order.desc)
        )

        if filters.get("from_date"):
            query = query.where(ee.posting_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(ee.posting_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(ee.company == filters.get("company"))

        expense_data = query.run(as_dict=True)
        
        # Get all unique Journal Entry names
        journal_entries = list(set([row.get("journal_entry_name") for row in expense_data if row.get("journal_entry_name")]))
        
        # Fetch all VAT accounts in one query (case-insensitive)
        vat_accounts_map = {}
        if journal_entries:
            placeholders = ",".join(["%s"] * len(journal_entries))
            vat_accounts = frappe.db.sql("""
                SELECT DISTINCT parent, account 
                FROM `tabJournal Entry Account`
                WHERE parent IN ({})
                AND LOWER(account) LIKE LOWER(%s)
                ORDER BY parent, idx
            """.format(placeholders), 
                journal_entries + ["%vat%"], as_dict=True)
            
            # Create a map (first VAT account per Journal Entry)
            for entry in vat_accounts:
                if entry.get("parent") not in vat_accounts_map:
                    vat_accounts_map[entry.get("parent")] = entry.get("account")
        
        # Enrich data with VAT account from Journal Entry
        for row in expense_data:
            journal_entry = row.get("journal_entry_name")
            if journal_entry and journal_entry in vat_accounts_map:
                row["tax_account"] = vat_accounts_map[journal_entry]
            else:
                row["tax_account"] = None
            # Remove the temporary journal_entry_name field
            row.pop("journal_entry_name", None)
        data.extend(expense_data)
    
    data = [row for row in data if flt(row.get("tax_amount", 0)) != 0]

    return data


# ---------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------

def get_columns(filters):
    return [
        {"label": _("Transaction Type"), "fieldname": "transaction_type", "width": 130},
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "transaction_type",
            "width": 150,
        },
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Party"), "fieldname": "party_name", "width": 150},
        {"label": _("Net Amount"), "fieldname": "net_total", "fieldtype": "Currency", "width": 120},
        {
            "label": _("Tax Account"),
            "fieldname": "tax_account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 150,
        },
        {"label": _("VAT %"), "fieldname": "tax_rate", "fieldtype": "Float", "width": 80},
        {"label": _("VAT Amount"), "fieldname": "tax_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
    ]


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

def get_summary(data, filters):
    """Calculate summary totals based on transaction type"""
    if not data:
        return []

    transaction_type = filters.get("transaction_type", "All")

    # ---------------- SALES ----------------
    if transaction_type == "Sales Invoice":
        total_net = sum(
            flt(row.get("net_total", 0))
            for row in data
            if row.get("transaction_type") == "Sales Invoice"
        )
        total_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Sales Invoice"
        )
        total_grand = sum(
            flt(row.get("grand_total", 0))
            for row in data
            if row.get("transaction_type") == "Sales Invoice"
        )

        return [
            {"label": _("Total Net Amount"), "value": total_net, "datatype": "Currency"},
            {"label": _("Total Tax Amount"), "value": total_tax, "datatype": "Currency"},
            {"label": _("Total Grand Amount"), "value": total_grand, "datatype": "Currency"},
        ]

    # ---------------- PURCHASE ----------------
    elif transaction_type == "Purchase Invoice":
        total_net = sum(
            flt(row.get("net_total", 0))
            for row in data
            if row.get("transaction_type") == "Purchase Invoice"
        )
        total_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Purchase Invoice"
        )
        total_grand = sum(
            flt(row.get("grand_total", 0))
            for row in data
            if row.get("transaction_type") == "Purchase Invoice"
        )

        return [
            {"label": _("Total Net Amount"), "value": total_net, "datatype": "Currency"},
            {"label": _("Total Tax Amount"), "value": total_tax, "datatype": "Currency"},
            {"label": _("Total Grand Amount"), "value": total_grand, "datatype": "Currency"},
        ]

    # ---------------- EXPENSE ----------------
    elif transaction_type == "Expense Entry":
        total_net = sum(
            flt(row.get("net_total", 0))
            for row in data
            if row.get("transaction_type") == "Expense Entry"
        )
        total_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Expense Entry"
        )
        total_grand = sum(
            flt(row.get("grand_total", 0))
            for row in data
            if row.get("transaction_type") == "Expense Entry"
        )

        return [
            {"label": _("Total Expense Amount"), "value": total_net, "datatype": "Currency"},
            {"label": _("Total Expense VAT"), "value": total_tax, "datatype": "Currency"},
            {"label": _("Total Expense with VAT"), "value": total_grand, "datatype": "Currency"},
        ]

    # ---------------- ALL ----------------
    else:
        sales_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Sales Invoice"
        )
        purchase_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Purchase Invoice"
        )
        expense_tax = sum(
            flt(row.get("tax_amount", 0))
            for row in data
            if row.get("transaction_type") == "Expense Entry"
        )

        vat_payable = sales_tax - (purchase_tax + expense_tax)

        return [
            {"label": _("VAT on Sales"), "value": sales_tax, "datatype": "Currency"},
            {"label": _("VAT on Purchase"), "value": purchase_tax, "datatype": "Currency"},
            {"label": _("VAT on Expenses"), "value": expense_tax, "datatype": "Currency"},
            {"label": _("VAT Payable"), "value": vat_payable, "datatype": "Currency"},
        ]