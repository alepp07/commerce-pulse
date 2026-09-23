"""Load validated CSVs into SQLite and export SQL results. Standard library only."""
import argparse
import csv
import json
import os
from datetime import date
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = {
    'customers': ['customer_id', 'region'],
    'products': ['product_id', 'category'],
    'orders': ['order_id', 'customer_id', 'status', 'ordered_at', 'estimated_delivery_at', 'delivered_at'],
    'order_items': ['order_id', 'item_id', 'product_id', 'quantity', 'unit_price_cents'],
}
REPORTS = ['monthly_sales', 'category_sales', 'delivery_performance', 'repeat_customers']


def read_rows(folder, table):
    with (folder / f'{table}.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS[table]:
            raise ValueError(f'{table}: expected columns {COLUMNS[table]}')
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'{table}:{line}: malformed CSV row')
            row = {key: value.strip() for key, value in row.items()}
            if any(not value for key, value in row.items() if key != 'delivered_at'):
                raise ValueError(f'{table}:{line}: missing required value')
            if table == 'orders':
                dates = {}
                for key in ('ordered_at', 'estimated_delivery_at', 'delivered_at'):
                    if row[key]:
                        parsed = date.fromisoformat(row[key])
                        if parsed.isoformat() != row[key]:
                            raise ValueError(f'{table}:{line}: use YYYY-MM-DD dates')
                        dates[key] = parsed
                if dates['estimated_delivery_at'] < dates['ordered_at']:
                    raise ValueError(f'{table}:{line}: estimate precedes purchase')
                if (row['status'] == 'delivered') != bool(row['delivered_at']):
                    raise ValueError(f'{table}:{line}: status and delivery date disagree')
                if row['delivered_at'] and dates['delivered_at'] < dates['ordered_at']:
                    raise ValueError(f'{table}:{line}: delivery precedes purchase')
                row['delivered_at'] = row['delivered_at'] or None
            if table == 'order_items':
                for key in ('item_id', 'quantity', 'unit_price_cents'):
                    row[key] = int(row[key])
            rows.append(tuple(row[key] for key in COLUMNS[table]))
        if not rows:
            raise ValueError(f'{table}: no data rows')
        return rows


def build_database(folder, database):
    """Validate in a temporary database; replace the old database only on success."""
    folder, database = Path(folder), Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(dir=database.parent, suffix='.sqlite')
    os.close(fd)
    staging = Path(filename)
    connection = None
    try:
        connection = sqlite3.connect(staging)
        connection.executescript((ROOT / 'sql/schema.sql').read_text())
        counts = {}
        with connection:
            for table, columns in COLUMNS.items():
                rows = read_rows(folder, table)
                connection.executemany(
                    f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})", rows
                )
                counts[table] = len(rows)
            missing = connection.execute('''SELECT COUNT(*) FROM orders o WHERE NOT EXISTS
                (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id)''').fetchone()[0]
            if missing:
                raise ValueError(f'{missing} orders have no items')
        connection.close()
        connection = None
        os.replace(staging, database)
        return counts
    finally:
        if connection is not None:
            connection.close()
        staging.unlink(missing_ok=True)


def export_reports(database, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        queries = {name: (ROOT / f'sql/{name}.sql').read_text() for name in REPORTS}
        queries['order_summary'] = 'SELECT * FROM order_summary ORDER BY order_id'
        for name, query in queries.items():
            cursor = connection.execute(query)
            with (output / f'{name}.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow(column[0] for column in cursor.description)
                writer.writerows(cursor)
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/sample')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts')
    args = parser.parse_args()
    # Avoid overwriting user input by accidentally exporting into the source folder.
    if args.input.resolve() == args.output.resolve():
        parser.error('--output must differ from --input')
    database = args.output / 'commerce.sqlite'
    counts = build_database(args.input, database)
    export_reports(database, args.output)
    manifest = {'source': str(args.input.resolve()),
                'synthetic_sample': args.input.resolve() == (ROOT / 'data/sample').resolve(),
                'loaded_rows': counts, 'reports': REPORTS + ['order_summary']}
    (args.output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Validated {sum(counts.values())} rows. Reports: {args.output.resolve()}')


if __name__ == '__main__':
    main()
