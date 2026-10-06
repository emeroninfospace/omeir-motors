# Copyright (c) 2026, Emeron Infospace and contributors
# For license information, please see license.txt

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce
from frappe.utils import flt, getdate

OUTPUT = "Output"
INPUT = "Input"

TRANSACTION_TYPES = (
    "Sales Invoice",
    "Purchase Invoice",
    "Subcontract Invoice",
    "Expense Entry",
    "Journal Entry",
)

# Which transaction types a party filter applies to
CUSTOMER_SIDE = {"Sales Invoice", "Journal Entry"}
SUPPLIER_SIDE = {"Purchase Invoice", "Subcontract Invoice", "Expense Entry", "Journal Entry"}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    vat_accounts = get_vat_accounts(filters.company)
    data = get_data(filters, vat_accounts)

    return get_columns(), data, None, None, get_summary(data, filters)


def validate_filters(filters):
    filters.transaction_type = filters.transaction_type or "All"

    if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date must be before To Date"))


def get_vat_accounts(company):
    """All ledger accounts with 'VAT' in the name (case-insensitive under default collation)."""
    account_filters = {"is_group": 0, "name": ["like", "%vat%"]}
    if company:
        account_filters["company"] = company
    return frappe.get_all("Account", filters=account_filters, pluck="name")


# ---------------------------------------------------------
# DATA
# ---------------------------------------------------------

def get_data(filters, vat_accounts):
    fetchers = {
        "Sales Invoice": get_sales_invoice_data,
        "Purchase Invoice": get_purchase_invoice_data,
        "Subcontract Invoice": get_subcontract_invoice_data,
        "Expense Entry": get_expense_entry_data,
        "Journal Entry": get_journal_entry_data,
    }

    data = []
    for transaction_type, fetch in fetchers.items():
        if should_include(transaction_type, filters):
            data.extend(fetch(filters, vat_accounts))

    # Stable sort keeps the tax rows of one voucher together
    data.sort(key=lambda r: (r.posting_date or date.min, r.transaction_type, r.voucher_no or ""))
    return data


def should_include(transaction_type, filters):
    if filters.transaction_type not in ("All", transaction_type):
        return False
    if filters.customer and transaction_type not in CUSTOMER_SIDE:
        return False
    if filters.supplier and transaction_type not in SUPPLIER_SIDE:
        return False
    return True


def apply_common_filters(query, doc, filters, date_field="posting_date"):
    date_col = getattr(doc, date_field)

    if filters.company:
        query = query.where(doc.company == filters.company)
    if filters.from_date:
        query = query.where(date_col >= filters.from_date)
    if filters.to_date:
        query = query.where(date_col <= filters.to_date)

    return query


def signed_purchase_tax(tax):
    """Purchase taxes marked 'Deduct' reduce input VAT."""
    return (
        Case()
        .when(tax.add_deduct_tax == "Deduct", tax.tax_amount * -1)
        .else_(tax.tax_amount)
    )


def finalize_rows(rows, transaction_type, vat_type=None, dedupe_totals=True):
    """
    Tag rows and show Net / Grand Total only on the first tax row of a voucher,
    so totals are not counted twice when an invoice has several tax rows.
    """
    seen = set()
    for row in rows:
        row.transaction_type = transaction_type
        if vat_type:
            row.vat_type = vat_type

        if dedupe_totals:
            if row.voucher_no in seen:
                row.net_total = None
                row.grand_total = None
            else:
                seen.add(row.voucher_no)

    return rows


# ---------------- SALES INVOICE ----------------

def get_sales_invoice_data(filters, vat_accounts):
    si = frappe.qb.DocType("Sales Invoice")
    tax = frappe.qb.DocType("Sales Taxes and Charges")

    query = (
        frappe.qb.from_(si)
        .inner_join(tax)
        .on((tax.parent == si.name) & (tax.parenttype == "Sales Invoice"))
        .select(
            si.name.as_("voucher_no"),
            si.posting_date,
            si.customer_name.as_("party_name"),
            si.tax_id.as_("trn"),
            si.po_no.as_("ref_no"),
            si.net_total,
            tax.account_head.as_("tax_account"),
            tax.rate.as_("tax_rate"),
            tax.tax_amount,
            si.grand_total,
            si.remarks,
        )
        .where((si.docstatus == 1) & (tax.tax_amount != 0))
        .orderby(si.name)
        .orderby(tax.idx)
    )
    query = apply_common_filters(query, si, filters)

    if filters.customer:
        query = query.where(si.customer == filters.customer)

    return finalize_rows(query.run(as_dict=True), "Sales Invoice", OUTPUT)


# ---------------- PURCHASE INVOICE ----------------

def get_purchase_invoice_data(filters, vat_accounts):
    pi = frappe.qb.DocType("Purchase Invoice")
    tax = frappe.qb.DocType("Purchase Taxes and Charges")

    query = (
        frappe.qb.from_(pi)
        .inner_join(tax)
        .on((tax.parent == pi.name) & (tax.parenttype == "Purchase Invoice"))
        .select(
            pi.name.as_("voucher_no"),
            pi.posting_date,
            pi.supplier_name.as_("party_name"),
            pi.tax_id.as_("trn"),
            pi.bill_no.as_("ref_no"),
            pi.net_total,
            tax.account_head.as_("tax_account"),
            tax.rate.as_("tax_rate"),
            signed_purchase_tax(tax).as_("tax_amount"),
            pi.grand_total,
            pi.remarks,
        )
        .where((pi.docstatus == 1) & (tax.tax_amount != 0))
        .orderby(pi.name)
        .orderby(tax.idx)
    )
    query = apply_common_filters(query, pi, filters)

    if filters.supplier:
        query = query.where(pi.supplier == filters.supplier)

    return finalize_rows(query.run(as_dict=True), "Purchase Invoice", INPUT)


# ---------------- SUBCONTRACT INVOICE ----------------

def get_subcontract_invoice_data(filters, vat_accounts):
    sc = frappe.qb.DocType("Subcontract Invoice")
    tax = frappe.qb.DocType("Purchase Taxes and Charges")
    sup = frappe.qb.DocType("Supplier")

    query = (
        frappe.qb.from_(sc)
        .inner_join(tax)
        .on((tax.parent == sc.name) & (tax.parenttype == "Subcontract Invoice"))
        .left_join(sup)
        .on(sup.name == sc.supplier)
        .select(
            sc.name.as_("voucher_no"),
            sc.transaction_date.as_("posting_date"),
            Coalesce(sup.supplier_name, sc.supplier).as_("party_name"),
            sup.tax_id.as_("trn"),
            sc.supplier_invoice_no.as_("ref_no"),
            sc.total_amount.as_("net_total"),
            tax.account_head.as_("tax_account"),
            tax.rate.as_("tax_rate"),
            signed_purchase_tax(tax).as_("tax_amount"),
            sc.grand_total,
            sc.custom_supplier_details.as_("remarks"),
        )
        .where((sc.docstatus == 1) & (tax.tax_amount != 0))
        .orderby(sc.name)
        .orderby(tax.idx)
    )
    query = apply_common_filters(query, sc, filters, date_field="transaction_date")

    if filters.supplier:
        query = query.where(sc.supplier == filters.supplier)

    return finalize_rows(query.run(as_dict=True), "Subcontract Invoice", INPUT)


# ---------------- EXPENSE ENTRY ----------------

def get_expense_entry_data(filters, vat_accounts):
    ee = frappe.qb.DocType("Expense Entry")
    eei = frappe.qb.DocType("Expense Entry Item")

    query = (
        frappe.qb.from_(ee)
        .inner_join(eei)
        .on((eei.parent == ee.name) & (eei.parenttype == "Expense Entry"))
        .select(
            ee.name.as_("voucher_no"),
            ee.posting_date,
            eei.supplier_name.as_("party_name"),
            eei.trn,
            eei.voucher_no.as_("ref_no"),
            eei.amount.as_("net_total"),
            eei.tax_account,
            eei.vat_percentage.as_("tax_rate"),
            eei.vat_amount.as_("tax_amount"),
            eei.total_amount.as_("grand_total"),
            ee.journal_entry,
            eei.narration.as_("remarks"),
        )
        .where((ee.docstatus == 1) & (eei.vat_amount != 0))
        .orderby(ee.name)
        .orderby(eei.idx)
    )
    query = apply_common_filters(query, ee, filters)

    if filters.supplier:
        # Expense Entry Item stores supplier as free text, so match both ID and name
        supplier_name = frappe.db.get_value("Supplier", filters.supplier, "supplier_name")
        names = list({filters.supplier, supplier_name} - {None})
        query = query.where(eei.supplier_name.isin(names))

    rows = query.run(as_dict=True)

    # Fallback: if the item has no Tax Account, take the VAT account from the linked Journal Entry
    missing = list({r.journal_entry for r in rows if not r.tax_account and r.journal_entry})
    if missing and vat_accounts:
        jea = frappe.qb.DocType("Journal Entry Account")
        je_vat_rows = (
            frappe.qb.from_(jea)
            .select(jea.parent, jea.account)
            .where(jea.parent.isin(missing) & jea.account.isin(vat_accounts))
            .orderby(jea.parent)
            .orderby(jea.idx)
        ).run(as_dict=True)

        first_vat_account = {}
        for r in je_vat_rows:
            first_vat_account.setdefault(r.parent, r.account)

        for row in rows:
            row.tax_account = row.tax_account or first_vat_account.get(row.journal_entry)

    # Each item is its own line, so totals are not de-duplicated
    return finalize_rows(rows, "Expense Entry", INPUT, dedupe_totals=False)


# ---------------- JOURNAL ENTRY ----------------

def get_journal_entry_data(filters, vat_accounts):
    """Journal Entries that post to a VAT account (excluding those created by Expense Entry)."""
    if not vat_accounts:
        return []

    je = frappe.qb.DocType("Journal Entry")
    jea = frappe.qb.DocType("Journal Entry Account")
    ee = frappe.qb.DocType("Expense Entry")

    # JEs already reported through Expense Entry -> skip to avoid double counting
    expense_jes = (
        frappe.qb.from_(ee)
        .select(ee.journal_entry)
        .where((ee.docstatus == 1) & ee.journal_entry.isnotnull())
    )

    query = (
        frappe.qb.from_(je)
        .inner_join(jea)
        .on(jea.parent == je.name)
        .select(
            je.name.as_("voucher_no"),
            je.posting_date,
            je.total_debit,
            je.cheque_no.as_("ref_no"),
            je.user_remark.as_("remarks"),
            jea.account.as_("tax_account"),
            jea.debit,
            jea.credit,
        )
        .where(
            (je.docstatus == 1)
            & jea.account.isin(vat_accounts)
            & je.name.notin(expense_jes)
        )
        .orderby(je.name)
        .orderby(jea.idx)
    )
    query = apply_common_filters(query, je, filters)

    if filters.customer or filters.supplier:
        party_type, party = (
            ("Customer", filters.customer) if filters.customer else ("Supplier", filters.supplier)
        )
        party_jes = (
            frappe.qb.from_(jea)
            .select(jea.parent)
            .where((jea.party_type == party_type) & (jea.party == party))
        )
        query = query.where(je.name.isin(party_jes))

    rows = query.run(as_dict=True)
    if not rows:
        return []

    parties = get_journal_entry_parties({r.voucher_no for r in rows})

    vat_total = defaultdict(float)
    for r in rows:
        vat_total[r.voucher_no] += abs(flt(r.debit) - flt(r.credit))

    data = []
    for r in rows:
        amount = flt(r.debit) - flt(r.credit)
        if not amount:
            continue

        net_total = flt(r.total_debit) - vat_total[r.voucher_no]
        tax_amount = abs(amount)
        party = parties.get(r.voucher_no, {})

        data.append(
            frappe._dict(
                voucher_no=r.voucher_no,
                posting_date=r.posting_date,
                party_name=party.get("party_name"),
                trn=party.get("trn"),
                ref_no=r.ref_no,
                net_total=net_total,
                tax_account=r.tax_account,
                tax_rate=flt(tax_amount / net_total * 100, 2) if net_total else 0,
                tax_amount=tax_amount,
                grand_total=flt(r.total_debit),
                # Debit to VAT = input VAT (recoverable), Credit = output VAT (payable)
                vat_type=INPUT if amount > 0 else OUTPUT,
                remarks=r.remarks,
            )
        )

    return finalize_rows(data, "Journal Entry")


def get_journal_entry_parties(journal_entries):
    """First party on each Journal Entry, with its display name and TRN."""
    jea = frappe.qb.DocType("Journal Entry Account")
    party_rows = (
        frappe.qb.from_(jea)
        .select(jea.parent, jea.party_type, jea.party)
        .where(jea.parent.isin(list(journal_entries)) & jea.party.isnotnull() & (jea.party != ""))
        .orderby(jea.parent)
        .orderby(jea.idx)
    ).run(as_dict=True)

    first_party = {}
    for r in party_rows:
        first_party.setdefault(r.parent, r)

    details = {}
    for party_type, name_field in (("Customer", "customer_name"), ("Supplier", "supplier_name")):
        ids = list({r.party for r in first_party.values() if r.party_type == party_type})
        if not ids:
            continue
        for d in frappe.get_all(
            party_type,
            filters={"name": ["in", ids]},
            fields=["name", f"{name_field} as party_name", "tax_id"],
        ):
            details[(party_type, d.name)] = d

    result = {}
    for je_name, r in first_party.items():
        d = details.get((r.party_type, r.party))
        result[je_name] = {
            "party_name": d.party_name if d else r.party,
            "trn": d.tax_id if d else None,
        }
    return result


# ---------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------

def get_columns():
    return [
        {"label": _("Transaction Type"), "fieldname": "transaction_type", "width": 140},
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "transaction_type",
            "width": 160,
        },
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Party"), "fieldname": "party_name", "width": 180},
        {"label": _("TRN"), "fieldname": "trn", "width": 140},
        {"label": _("Reference No"), "fieldname": "ref_no", "width": 120},
        {"label": _("Net Amount"), "fieldname": "net_total", "fieldtype": "Currency", "width": 120},
        {
            "label": _("Tax Account"),
            "fieldname": "tax_account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 160,
        },
        {"label": _("VAT %"), "fieldname": "tax_rate", "fieldtype": "Float", "width": 70},
        {"label": _("VAT Amount"), "fieldname": "tax_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": _("VAT Type"), "fieldname": "vat_type", "width": 80},
        {
            "label": _("Journal Entry"),
            "fieldname": "journal_entry",
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 150,
        },
        {"label": _("Remarks"), "fieldname": "remarks", "width": 200},
    ]


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

SUMMARY_LABELS = {
    "Sales Invoice": _("VAT on Sales"),
    "Purchase Invoice": _("VAT on Purchase"),
    "Subcontract Invoice": _("VAT on Subcontract"),
    "Expense Entry": _("VAT on Expenses"),
    "Journal Entry": _("VAT on Journal Entries"),
}


def get_summary(data, filters):
    if not data:
        return []

    def total(field, transaction_type=None, vat_type=None):
        return sum(
            flt(r.get(field))
            for r in data
            if (not transaction_type or r.transaction_type == transaction_type)
            and (not vat_type or r.vat_type == vat_type)
        )

    transaction_type = filters.transaction_type
    summary = []

    if transaction_type == "All":
        summary = [
            {"label": label, "value": total("tax_amount", ttype), "datatype": "Currency"}
            for ttype, label in SUMMARY_LABELS.items()
        ]
    else:
        is_expense = transaction_type == "Expense Entry"
        summary = [
            {
                "label": _("Total Expense Amount") if is_expense else _("Total Net Amount"),
                "value": total("net_total"),
                "datatype": "Currency",
            },
            {
                "label": _("Total Expense VAT") if is_expense else _("Total VAT Amount"),
                "value": total("tax_amount"),
                "datatype": "Currency",
            },
            {
                "label": _("Total Expense with VAT") if is_expense else _("Total Grand Amount"),
                "value": total("grand_total"),
                "datatype": "Currency",
            },
        ]

    if transaction_type in ("All", "Journal Entry"):
        output_vat = total("tax_amount", vat_type=OUTPUT)
        input_vat = total("tax_amount", vat_type=INPUT)
        vat_payable = output_vat - input_vat

        summary += [
            {"label": _("Output VAT"), "value": output_vat, "datatype": "Currency"},
            {"label": _("Input VAT"), "value": input_vat, "datatype": "Currency"},
            {
                "label": _("VAT Payable") if vat_payable >= 0 else _("VAT Refundable"),
                "value": abs(vat_payable),
                "datatype": "Currency",
                "indicator": "Red" if vat_payable > 0 else "Green",
            },
        ]

    return summary