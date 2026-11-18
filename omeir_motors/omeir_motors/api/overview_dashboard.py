import frappe
from frappe.utils import nowdate, flt, get_year_start, get_year_ending, get_first_day, get_last_day, add_months
from datetime import date as _date


@frappe.whitelist()
def get_overview_dashboard_data(period="this_year", date_from=None, date_to=None):
    company = (
        frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )

    if period == "custom" and date_from and date_to:
        df = str(date_from)
        dt = str(date_to)
        period_label = df + " → " + dt
    else:
        df, dt, period_label = _get_period_dates(period)

    total_customers = frappe.db.count("Customer")
    total_suppliers = frappe.db.count("Supplier")

    total_received = flt(frappe.db.sql(
        """SELECT SUM(paid_amount) FROM `tabPayment Entry`
           WHERE docstatus=1 AND payment_type='Receive' AND posting_date BETWEEN %s AND %s""",
        (df, dt),
    )[0][0])

    monthly_sales_purchase = _get_monthly_sales_purchase(df, dt)
    # The monthly breakdown covers the same invoices, so the period totals come from it
    total_sales = flt(sum(flt(m.sales) for m in monthly_sales_purchase))
    total_purchase = flt(sum(flt(m.purchase) for m in monthly_sales_purchase))

    bank_accounts, cash_accounts = [], []
    for account in frappe.db.sql(
        """SELECT a.name, a.account_name, a.account_type,
                  IFNULL(SUM(gl.debit - gl.credit), 0) AS balance
           FROM `tabAccount` a
           LEFT JOIN `tabGL Entry` gl ON gl.account = a.name AND gl.is_cancelled = 0
           WHERE a.account_type IN ('Bank', 'Cash', 'Petty Cash')
             AND a.is_group = 0
             AND a.disabled = 0
             AND (a.company = %s OR %s IS NULL)
           GROUP BY a.name
           ORDER BY balance DESC""",
        (company, company), as_dict=True,
    ):
        (bank_accounts if account.pop("account_type") == "Bank" else cash_accounts).append(account)

    payable = _get_outstanding_summary("Purchase Invoice")
    accounts_payable = payable.outstanding
    accounts_payable_count = payable.outstanding_count
    overdue_payable = payable.overdue_count
    paid_payable = payable.paid_count
    all_payable = frappe.db.get_list(
        "Purchase Invoice",
        filters=[["docstatus", "=", 1], ["outstanding_amount", ">", 0]],
        fields=["name", "supplier_name", "outstanding_amount", "due_date"],
        order_by="due_date asc",
        limit=200,
    )

    receivable = _get_outstanding_summary("Sales Invoice")
    accounts_receivable = receivable.outstanding
    accounts_receivable_count = receivable.outstanding_count
    overdue_receivable = receivable.overdue_count
    paid_receivable = receivable.paid_count
    all_receivable = frappe.db.get_list(
        "Sales Invoice",
        filters=[["docstatus", "=", 1], ["outstanding_amount", ">", 0]],
        fields=["name", "customer_name", "outstanding_amount", "due_date"],
        order_by="due_date asc",
        limit=200,
    )

    overdue_receivables = frappe.db.get_list(
        "Sales Invoice",
        filters=[
            ["docstatus", "=", 1],
            ["outstanding_amount", ">", 0],
            ["due_date", "<", nowdate()],
        ],
        fields=["name", "customer_name", "outstanding_amount", "due_date"],
        order_by="due_date asc",
        limit=200,
    )

    overdue_payables = frappe.db.get_list(
        "Purchase Invoice",
        filters=[
            ["docstatus", "=", 1],
            ["outstanding_amount", ">", 0],
            ["due_date", "<", nowdate()],
        ],
        fields=["name", "supplier_name", "outstanding_amount", "due_date"],
        order_by="due_date asc",
        limit=200,
    )

    emp_expense_records = frappe.db.sql(
        """SELECT
               ec.name,
               ec.employee_name,
               ec.posting_date,
               ec.total_claimed_amount,
               ec.status
           FROM `tabExpense Claim` ec
           WHERE ec.docstatus = 1
             AND ec.payable_account LIKE %s
           ORDER BY ec.posting_date DESC
           LIMIT 100""",
        ('%Employee Expense Payable%',),
        as_dict=True,
    )
    emp_expense_payable, emp_expense_count = frappe.db.sql(
        """SELECT IFNULL(SUM(total_claimed_amount), 0), COUNT(*)
           FROM `tabExpense Claim`
           WHERE docstatus = 1
             AND payable_account LIKE %s""",
        ('%Employee Expense Payable%',)
    )[0]

    # Match the account names on the small Account table, then use the GL Entry account index
    # (a LIKE on gl.account would scan the whole General Ledger)
    other_payable = 0.0
    other_payable_accounts = frappe.get_all(
        "Account", filters={"name": ["like", "%Other Payable%"]}, pluck="name"
    )
    if other_payable_accounts:
        other_payable = flt(frappe.db.sql(
            """SELECT IFNULL(SUM(gl.credit - gl.debit), 0)
               FROM `tabGL Entry` gl
               WHERE gl.account IN %s
                 AND gl.is_cancelled = 0""",
            (other_payable_accounts,)
        )[0][0])

    inv_type_raw = frappe.db.sql(
        """SELECT custom_invoice_type AS `type`,
                  SUM(grand_total) AS total,
                  COUNT(*) AS count
           FROM `tabSales Invoice`
           WHERE docstatus=1
             AND posting_date BETWEEN %s AND %s
             AND custom_invoice_type IS NOT NULL
             AND custom_invoice_type != ''
           GROUP BY custom_invoice_type
           ORDER BY total DESC""",
        (df, dt), as_dict=True,
    )

    sales_by_inv_type = []
    for t in inv_type_raw:
        invoices = frappe.db.get_list(
            "Sales Invoice",
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", "between", [df, dt]],
                ["custom_invoice_type", "=", t.type],
            ],
            fields=["name", "customer_name", "posting_date", "grand_total", "custom_payment_type"],
            order_by="posting_date desc",
            limit=50,
        )
        sales_by_inv_type.append({
            "type": t.type,
            "total": flt(t.total),
            "count": t.count,
            "invoices": invoices,
        })

    pay_type_raw = frappe.db.sql(
        """SELECT custom_payment_type AS `type`,
                  SUM(grand_total) AS total,
                  COUNT(*) AS count
           FROM `tabSales Invoice`
           WHERE docstatus=1
             AND posting_date BETWEEN %s AND %s
             AND custom_payment_type IS NOT NULL
             AND custom_payment_type != ''
           GROUP BY custom_payment_type
           ORDER BY total DESC""",
        (df, dt), as_dict=True,
    )

    sales_by_pay_type = []
    for t in pay_type_raw:
        invoices = frappe.db.get_list(
            "Sales Invoice",
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", "between", [df, dt]],
                ["custom_payment_type", "=", t.type],
            ],
            fields=["name", "customer_name", "posting_date", "grand_total", "custom_invoice_type"],
            order_by="posting_date desc",
            limit=50,
        )
        sales_by_pay_type.append({
            "type": t.type,
            "total": flt(t.total),
            "count": t.count,
            "invoices": invoices,
        })

    recent_sales = frappe.db.get_list(
        "Sales Invoice",
        filters=[["docstatus", "=", 1], ["posting_date", "between", [df, dt]]],
        fields=["name", "customer_name", "posting_date", "grand_total",
                "custom_invoice_type", "custom_payment_type", "status"],
        order_by="posting_date desc",
        limit=50,
    )

    recent_purchases = frappe.db.get_list(
        "Purchase Invoice",
        filters=[["docstatus", "=", 1], ["posting_date", "between", [df, dt]]],
        fields=["name", "supplier_name", "posting_date", "grand_total", "status"],
        order_by="posting_date desc",
        limit=50,
    )

    return {
        "period_label": period_label,
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
        "total_sales": total_sales,
        "total_purchase": total_purchase,
        "total_received": total_received,
        "monthly_sales_purchase": monthly_sales_purchase,
        "bank_accounts": bank_accounts,
        "bank_total": flt(sum(flt(a.balance) for a in bank_accounts)),
        "cash_accounts": cash_accounts,
        "cash_total": flt(sum(flt(a.balance) for a in cash_accounts)),
        "accounts_payable": accounts_payable,
        "accounts_payable_count": accounts_payable_count,
        "overdue_payable": overdue_payable,
        "paid_payable": paid_payable,
        "all_payable": all_payable,
        "accounts_receivable": accounts_receivable,
        "accounts_receivable_count": accounts_receivable_count,
        "overdue_receivable": overdue_receivable,
        "paid_receivable": paid_receivable,
        "all_receivable": all_receivable,
        "overdue_receivables": overdue_receivables,
        "overdue_payables": overdue_payables,
        "emp_expense_payable": flt(emp_expense_payable),
        "emp_expense_count": int(emp_expense_count),
        "emp_expense_records": emp_expense_records,
        "other_payable": other_payable,
        "sales_by_inv_type": sales_by_inv_type,
        "sales_by_pay_type": sales_by_pay_type,
        "recent_sales": recent_sales,
        "recent_purchases": recent_purchases,
    }


def _get_outstanding_summary(doctype):
    """Outstanding total and open / overdue / paid counts of submitted invoices, in one scan."""
    row = frappe.db.sql(
        f"""SELECT
               IFNULL(SUM(CASE WHEN outstanding_amount > 0 THEN outstanding_amount END), 0) AS outstanding,
               IFNULL(SUM(outstanding_amount > 0), 0) AS outstanding_count,
               IFNULL(SUM(outstanding_amount > 0 AND due_date < %(today)s), 0) AS overdue_count,
               IFNULL(SUM(status = 'Paid'), 0) AS paid_count
           FROM `tab{doctype}`
           WHERE docstatus = 1""",
        {"today": nowdate()}, as_dict=True,
    )[0]
    row.outstanding = flt(row.outstanding)
    for key in ("outstanding_count", "overdue_count", "paid_count"):
        row[key] = int(row[key])
    return row


def _get_monthly_sales_purchase(df, dt):
    rows = frappe.db.sql(
        """SELECT
             DATE_FORMAT(posting_date, '%%b %%Y') AS month,
             DATE_FORMAT(posting_date, '%%Y-%%m') AS month_key,
             SUM(CASE WHEN doctype = 'SI' THEN grand_total ELSE 0 END) AS sales,
             SUM(CASE WHEN doctype = 'PI' THEN grand_total ELSE 0 END) AS purchase
           FROM (
             SELECT posting_date, grand_total, 'SI' AS doctype
               FROM `tabSales Invoice` WHERE docstatus=1 AND posting_date BETWEEN %s AND %s
             UNION ALL
             SELECT posting_date, grand_total, 'PI' AS doctype
               FROM `tabPurchase Invoice` WHERE docstatus=1 AND posting_date BETWEEN %s AND %s
           ) t
           GROUP BY month_key, month
           ORDER BY month_key""",
        (df, dt, df, dt), as_dict=True,
    )
    return rows


def _get_period_dates(period):
    today = nowdate()
    if period == "this_month":
        return get_first_day(today), get_last_day(today), "This Month"
    elif period == "last_month":
        first = get_first_day(add_months(today, -1))
        last  = get_last_day(add_months(today, -1))
        return first, last, "Last Month"
    elif period == "last_year":
        y = _date.today().year - 1
        return str(y) + "-01-01", str(y) + "-12-31", "Last Year"
    else:
        return get_year_start(today), get_year_ending(today), "This Year"