# CommercePulse

**E-commerce sales and delivery analytics with Python and SQL.**

CommercePulse turns order-level CSV data into validated tables and repeatable
reports answering four questions:

- How do delivered order value and average order value change each month?
- Which product categories contribute the most merchandise value?
- Where are late deliveries most common?
- What share of purchasing customers place more than one delivered order?

## Current status

Working foundation: a dependency-free Python loader, SQLite database, four SQL
analyses, CSV exports for Power BI, and automated tests. The included 20-row
fixture is **synthetic demonstration data**, not evidence about a real business.
A real-data adapter, PostgreSQL deployment, and a finished Power BI dashboard
are planned; they are not implemented yet.

## Quick start

Install Python 3.11 or newer. From a terminal:

```bash
git clone https://github.com/alepp07/commerce-pulse.git
cd commerce-pulse
python src/commerce_pulse/pipeline.py
python -m unittest discover -s tests -v
```

On systems where Python is named `python3`, use that command instead.
No API keys, cloud account, or third-party Python packages are required.

The pipeline creates these local files in `artifacts/`:

| File | Purpose |
|---|---|
| `commerce.sqlite` | Validated relational database and order-level view |
| `monthly_sales.csv` | Delivered order count, value, average value, and monthly growth |
| `category_sales.csv` | Category value ranking and units sold |
| `delivery_performance.csv` | Late delivery rate and average delivery time by region |
| `repeat_customers.csv` | Repeat purchase rate across the observation window |
| `order_summary.csv` | One row per order, ready for Power BI |
| `run_manifest.json` | Input location, row counts, and sample-data flag |

To load your own data, prepare the four CSVs using the exact column contract
in [the data dictionary](docs/data_dictionary.md), then run:

```bash
python src/commerce_pulse/pipeline.py --input data/raw --output artifacts
```

Raw data and generated reports are ignored by Git. The schema requires one
currency per dataset. Use integer cents rather than floating-point prices.
The loader rejects invalid input instead of silently dropping or repairing rows.
Each successful run rebuilds the database; it does not append duplicate records.
Failed validation preserves the existing database. Run one pipeline process at
a time; the report files are generated after database validation and are not
published as an atomic bundle.

## Model and metric design

Customers have many orders. Orders have many items, and each item references a
product. Item values are aggregated to one row per order before calculating
order counts and delivery rates. This prevents join multiplication from
inflating the metrics.

Read [metric definitions](docs/metrics.md) before interpreting results.
Merchandise value is not profit, net revenue, or cash collected: the current
model does not contain costs, returns, discounts, taxes, freight, or payments.

## Explore the sample

The fixture produces these **test expectations**, not business findings:

| Metric | Expected value |
|---|---:|
| January delivered merchandise value | 180.00 demo currency units |
| February delivered merchandise value | 115.00 demo currency units |
| January average delivered order value | 90.00 demo currency units |
| North region late delivery rate | 50% (1 of 2 delivered orders) |

Start a dashboard with [the Power BI guide](docs/power_bi.md). It includes
measures and page specifications; no completed `.pbix` file is included yet.

## Repository map

- `src/commerce_pulse/`: CSV validation, database loading, report exports
- `sql/`: relational schema and readable business queries
- `data/sample/`: tiny synthetic fixture for learning and regression tests
- `tests/`: metric, integrity, and repeat-run tests
- `docs/`: definitions, data contract, dashboard guide, and roadmap
- `.github/workflows/`: automated checks on pushes and pull requests

## Next milestones

See [the roadmap](docs/roadmap.md). The immediate priority is a documented,
licensed real-world dataset and an adapter preserving customer identity and
order/item grain. Only then should this project make substantive business
recommendations.
