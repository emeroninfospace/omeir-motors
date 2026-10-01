# Subcontract costs in Gross Profit (ERPNext v15)

## Why Purchase Invoice behaves differently

ERPNext's non-stock cost lookup uses a matching Purchase Invoice rate (by item,
project/cost center), not the custom Subcontract Invoice expense GL entry. A
shared service item can therefore pick another job's purchase rate. Updating
Sales Invoice Item `incoming_rate`, an Item price, or its last purchase rate does
not provide reliable job-specific costs in this report.

The existing Subcontract Invoice controller already debits the subcontract
expense account and credits the supplier payable. This change leaves that
controller and its accounting lifecycle unchanged. It does not create Purchase
Invoices, Stock Ledger Entries, Journal Entries, expenses or payable entries.

## Implementation and allocation policy

- Exact `Sublet Items.name` identifiers travel from Job Order to Subcontract Work
  Item, Subcontract Invoice Item and Sales Invoice Item. Manually entered rows
  infer a link only when the job/item mapping is unique. Same-item sublet rows
  retain separate costs when selected explicitly.
- For a mapped job sublet row, Buying Amount = sum of submitted linked
  Subcontract Invoice Item amounts / Job Order stock quantity × invoice stock
  quantity. Multiple supplier cost rows are additive. Split billing receives
  proportional cost; one full job cost cannot be assigned to every split bill.
- Costs use company currency and exclude the separate tax rows, matching the
  custom controller's current expense posting. This app has no subcontract
  currency/conversion fields; foreign-currency subcontracting is not supported.
- Submitted subcontract invoices dated through the report's **To Date** count.
  Their dates may precede the report's From Date. Later-recorded costs appear
  when To Date includes them. Cancelled invoices are excluded immediately;
  no saved cost total needs clearing. Amendments count only when submitted.
- A mapped sublet with no eligible submitted cost has zero buying amount. This
  can still show 100% GP while vendor billing is pending or after cancellation.
  It is not an estimated Job Order cost. A linked zero-value cost is also valid.
- Returns use the original Sales Invoice Item link. ERPNext retains its normal
  return treatment; no arbitrary assumption is made for ambiguous old returns.
- Submitted sales quantities, net of returns, must remain within the sublet
  quantity. Same-row submits lock the Job Order sublet row to prevent concurrent
  duplicate allocation. Historical overbilling blocks the affected report until
  reviewed. Cancelled sales invoices do not consume the allocation.
- Missing/invalid links for sublet sales or submitted cost rows stop the affected
  report with a review message rather than silently using another job's rate.
  Non-sublet services and stock items keep the native cost calculation.
- Drop-shipped items and Product Bundles are outside this allocation model and
  are rejected when linked. Ordinary stock items remain on ERPNext's valuation.

The standard **Gross Profit** report name, UI, columns, filters and aggregation
remain in use. This requires an app-level `Report.execute_module` override; an
unchanged native report does not query custom subcontract invoices. The standard
execute function runs with a private generator binding; no ERPNext source file
or global class is monkey-patched. Other reports delegate to Frappe unchanged.
Prepared report workers use the same Report controller; previously cached
prepared results must be regenerated. Apps that also override `Report` need
compatibility review because Frappe uses the last installed override.

## Historical migration

`omeir_motors.patches.subcontract_profitability` runs once during migration after
schema sync. It creates the Sales Invoice Item custom field and fills only:

- `Subcontract Invoice Item.job_order_sublet_row`
- `Sales Invoice Item.custom_job_order_sublet_row`

No save/submit methods or invoice recalculations run. No commits are issued inside
the patch. Existing links are validated, never silently replaced. Ambiguous,
missing-job, cross-company, invalid-UOM and invalid-return rows go into a private
`subcontract-profitability-backfill.json` File. No customer data is committed to
the repository. Rows without a trustworthy Job Order remain for human review.

The patch fingerprints every business column in GL Entry, Payment Ledger Entry,
Sales Invoice, Sales Invoice Item, Subcontract Invoice, Subcontract Invoice Item,
Job Order and Sublet Items before/after. Only the two new mapping columns are
excluded. A difference raises an error and must roll back migration. Counts and
hashes are included in the audit JSON. This scans those tables, so schedule the
one-time migration in maintenance mode, with enough memory for the largest table.

After resolving the review rows, rerun the CLI-only linker safely:

```bash
bench --site YOUR-SITE execute omeir_motors.profitability.audit.verified_backfill --kwargs '{"dry_run": true}'
bench --site YOUR-SITE execute omeir_motors.profitability.audit.verified_backfill --kwargs '{"dry_run": false}'
```

For duplicates that require a human choice, inspect the actual `Sublet Items`
row IDs and use the CLI-only reviewed mapping command. It validates company,
job, item, UOM and original-return relationships and fingerprints business data.
Change `dry_run` to false only after inspecting the proposed mapping:

```bash
bench --site YOUR-SITE execute omeir_motors.profitability.review.apply_links --kwargs '{"dry_run": true, "links": [{"doctype": "Sales Invoice Item", "name": "ACTUAL-INVOICE-ROW-ID", "sublet_row": "ACTUAL-JOB-SUBLET-ROW-ID"}]}'
```

Use `Subcontract Invoice Item` for the corresponding cost row. This command only
changes mapping metadata and stores a private before/after mapping audit. It
cannot invent a missing Job Order or infer a legacy return's original item;
those relationships require separately reviewed source-data correction.

## Staging rollout and accounting verification

1. Back up the site/database and restore a staging copy. Confirm ERPNext/Frappe
   v15 and check that another app does not replace the Report override.
2. Install this branch on staging; run `bench --site YOUR-SITE migrate`, clear
   cache and restart workers. Migration performs the guarded one-time linking.
3. Inspect the private audit JSON. Confirm `business_data_unchanged: true` and
   resolve every review exception relevant to the selected reporting period.
4. Check the original Subcontract Invoice GL: expense and payable entries,
   taxes, supplier balance and payment allocations must be unchanged. Compare
   Trial Balance and supplier outstanding with the pre-migration copy.
5. Run standard Gross Profit grouped by Invoice for an existing linked job:
   net sales AED 1,500, subcontract amount AED 1,000 → buying AED 1,000,
   GP AED 500, margin 33.33%. Repeat by Item Code, Customer and Project.
6. Test another job with the same service item and a different vendor cost;
   repeated sublet rows; multiple vendor invoices; partial sales quantities;
   a partial/full return; cancel/amend; zero vendor cost; costs posted after the
   sales date; different UOMs; mixed stock/service invoices; tax/discount cases.
7. Submit a new Subcontract Invoice using the existing workflow. Confirm exactly
   the usual expense/payable/tax entries are posted, and no additional entries
   originate from profitability linking. Submit the corresponding Sales Invoice,
   rerun Gross Profit, and repeat the audit. Test both cost-before-sale and
   sale-before-cost ordering. Verify normal non-sublet Purchase Invoice costing.
8. Regenerate prepared Gross Profit reports. Only promote after staging passes.

To roll back code, restore the preceding revision and restart/clear cache. The
unused link columns can remain. No accounting reversal is necessary for metadata
linking. Never reverse the original subcontract expense merely to undo this patch.

## Tests and limits of verification

```bash
# Core tests (upstream report tests explicitly skip without its source):
python -m unittest discover -s tests -v
# Include actual ERPNext standard report execution/grouping/return calculations:
UPSTREAM_GP_SOURCE=/path/to/erpnext/accounts/report/gross_profit/gross_profit.py \
  python -m unittest discover -s tests -v
```

Local tests run against the v15 source with database/dependency doubles. They
exercise the real standard report's calculations, not a copied GP formula.
GitHub's Subcontract profitability workflow repeats these tests against v15.
This is not a full Bench/MariaDB integration test or a live transaction audit.
Actual balances and installed-version compatibility require the staging checks
above. The pre-existing repository CI installs Frappe's default branch without
ERPNext; that older workflow is not an adequate integration gate for this change.
