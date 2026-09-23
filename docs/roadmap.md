# Delivery roadmap

## 1. Runnable foundation — implemented

- Validated relational inputs and deterministic sample fixture
- Four SQL analyses and order-level export
- Seven regression tests and GitHub Actions workflow
- Metric definitions and Power BI specification

## 2. Real-data analysis — next

- Select a public e-commerce dataset, verify its licence, and document the source.
- Build an adapter into the input contract; preserve stable customer identifiers.
- Document date parsing, status mappings, missingness, and exclusions.
- Add payment/returns fields only with explicit grain and metric definitions.
- Reconcile source totals, then write three to five supported findings with caveats.

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
