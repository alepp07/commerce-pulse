# Power BI starter guide

This is a dashboard specification, not a finished report. Use the generated
sample CSVs first to verify the workflow; label the report **SYNTHETIC DEMO**.

1. Run the Python pipeline.
2. In Power BI Desktop, choose Get data → Text/CSV and import
   `artifacts/order_summary.csv`. Name the table `Orders`.
3. Set ID, region, and status fields to Text; date fields to Date;
   item_value_cents and is_late to Whole number; delivery_days to Decimal number.
4. Add the following measures. Format Late Delivery Rate as Percentage.

```dax
Delivered Orders =
CALCULATE(COUNTROWS(Orders), Orders[status] = "delivered")

Delivered Merchandise Value =
DIVIDE(
    CALCULATE(SUM(Orders[item_value_cents]), Orders[status] = "delivered"),
    100
)

Average Order Value =
DIVIDE([Delivered Merchandise Value], [Delivered Orders])

Late Delivery Rate =
DIVIDE(
    CALCULATE(SUM(Orders[is_late]), Orders[status] = "delivered"),
    [Delivered Orders]
)
```

## Page plan

| Page | Visuals | Question |
|---|---|---|
| Sales | Value/order-count/AOV cards, purchase-month trend, category value bar chart | What is driving sales value? |
| Customers | Repeat-purchase KPI and region order counts | How broad is repeat purchasing? |
| Delivery | Late-rate card, regional rates with order counts, delivery-days chart | Where should delivery operations investigate? |

For category analysis, import `category_sales.csv` as a separate pre-aggregated
summary. Likewise, repeat_customers.csv is an observation-window summary.
Do not connect these summaries to the order table as if they contained order
rows. Their values will not respond to order-level date or region slicers.
Label them **full dataset** or keep them on separate pages. A later star model
will support consistent interactive filtering across all pages.

## Validate the sample dashboard

Use the bundled synthetic data and clear all filters first. The four measures
above should produce these values:

| Filter on Orders[ordered_at] | Delivered Orders | Delivered Merchandise Value | Average Order Value | Late Delivery Rate |
|---|---:|---:|---:|---:|
| All dates | 4 | 295.00 | 73.75 | 25% |
| January 2025 | 2 | 180.00 | 90.00 | 50% |
| February 2025 | 2 | 115.00 | 57.50 | 0% |

Values use demo currency units. Apply the month filter to the `Orders` table
to check that all four cards respond together. These expectations are fixture
checks, not business findings.

The imported `Orders` table should contain six rows, including the shipped
and cancelled orders; the measures count only the four delivered orders.
If a delivered-order card shows six, check that it uses `Delivered Orders`
rather than an unfiltered row count. If the value card shows 29,500, check the
division by 100 in the merchandise-value measure.

The SQL growth export stores percentage points (for example -36.11), whereas
the DAX rate is a fraction (0.5). Do not apply percentage formatting directly
to the SQL percentage-point columns without dividing by 100.

After importing real data, add a date dimension, extraction date, meaningful
currency labels, source attribution, and screenshots. Document nulls and small
samples. Never invent findings or claim the fixture demonstrates real trends.
