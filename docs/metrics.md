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
