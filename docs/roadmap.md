# Delivery roadmap

## 1. Runnable foundation — implemented

- Validated relational inputs and deterministic sample fixture
- Four SQL analyses and order-level export
- Regression tests and GitHub Actions workflow
- Metric definitions and Power BI specification

## 2. Real-data analysis — next

- Select a public e-commerce dataset, verify its licence, and document the source.
- Build an adapter into the input contract; preserve stable customer identifiers.
- Document date parsing, status mappings, missingness, and exclusions.
- Add payment/returns fields only with explicit grain and metric definitions.
- Reconcile source totals, then write three to five supported findings with caveats.

### Acceptance criteria for the first real dataset

Before marking this stage complete, include:

- A source note with the download URL, licence, extraction date, observation
  window, and currency.
- A mapping from source columns to the four input tables, including the
  customer identity rule and every status conversion.
- A reconciliation table showing source rows, accepted rows, and excluded rows
  with reasons for each exclusion. Explain any row-count changes caused by
  aggregation or splitting records.
- A reproducible command that converts the source into the input contract and
  runs the pipeline successfully.
- Checks against independently calculated delivered-order counts and
  merchandise-value totals, plus an explanation of any differences.
- Findings linked to specific query results, with limitations such as missing
  returns, incomplete months, or a restricted observation window.

## 3. Dashboard

- Build a Power BI star schema with an explicit date table.
- Add sales, customers, and delivery pages with consistent slicers.
- Save a report and export screenshots for the README.
- Validate dashboard totals against SQL results.

## 4. Engineering extension

- Add PostgreSQL and Docker Compose for local development.
- Port SQLite-specific dates and verify parity against the fixture.
- Add source provenance and atomic report-bundle publication.
- Consider scheduled ingestion only when the source actually updates.

Complete the analysis before adding forecasting or an AI interface. The goal
is to make the business reasoning and data quality visible alongside the code.
