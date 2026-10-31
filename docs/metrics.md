# Metric definitions

| Metric | Definition | Caveat |
|---|---|---|
| Delivered merchandise value | Sum of quantity × unit price for delivered orders, divided by 100 | Excludes shipped/cancelled orders; not accounting revenue |
| Average order value | Delivered merchandise value / delivered order count | Order grain, not item grain |
| Month-over-month growth | (Current value − previous value) / previous value × 100 | Null if prior calendar month is absent or value is zero |
| Late delivery rate | Delivered orders with actual delivery date after estimated date / delivered orders × 100 | Delivery on the estimated date is on time |
| Average delivery days | Mean calendar-day difference between purchase and actual delivery for delivered orders | Not working days |
| Repeat customer rate | Customers with at least two delivered orders / customers with at least one × 100 | Observation-window metric, not cohort retention |
| Category units | Sum of item quantities for delivered orders | Not the number of order lines |

Monthly grouping uses the purchase date. Historical totals can change when
previously shipped orders become delivered. The latest month may be incomplete;
check the source extraction date before comparing months.

Category order counts are not additive across categories: one order can contain
multiple categories. All-customer repeat purchase rate should not be interpreted
as retention without acquisition cohorts and comparable follow-up periods.
Small regional samples are unstable; show denominators beside percentages.

The SQL uses SQLite-specific date expressions. A PostgreSQL migration must adapt
those expressions and re-run metric tests; these scripts are not claimed to be
portable without modification.

## Combining groups correctly

Recalculate rates and averages from their totals when combining regions or
months. A simple average of the displayed percentages gives small groups the
same weight as large groups.

For illustration, if one region has 1 late order out of 2 deliveries and
another has 1 out of 8, the overall late rate is `100 × (1 + 1) / (2 + 8) = 20%`.
Averaging the regional rates, 50% and 12.5%, would incorrectly give 31.25%.
These numbers are illustrative, not results from the included sample.

Calculate the overall delivery rate directly from the order-level view:

```sql
SELECT COUNT(*) AS delivered_orders,
       COALESCE(SUM(is_late), 0) AS late_orders,
       ROUND(100.0 * SUM(is_late) / NULLIF(COUNT(*), 0), 2) AS late_delivery_pct
FROM order_summary
WHERE status = 'delivered';
```

With no delivered orders, the counts are zero and the rate is null.
For combined average order value, divide total merchandise value by total
delivered orders. For average delivery days, average the order-level
`delivery_days` values; combining rounded regional averages can lose precision.

## Reading category ranks

The category report ranks delivered merchandise value from highest to lowest.
Equal values share a rank, and the next distinct value receives the next
consecutive rank (`DENSE_RANK`). For example, illustrative values of 100, 100,
and 50 produce ranks 1, 1, and 2. Category names determine display order
within a tie; they do not break the tie.

A filter such as `value_rank <= 3` can therefore include more than three
categories. Label it as the top three value ranks if ties are retained.
Categories with no delivered items are absent from this report. A category
whose delivered items are all free appears with zero merchandise value.
