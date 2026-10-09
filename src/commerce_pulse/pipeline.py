"""Load validated CSVs into SQLite and export SQL results. Standard library only."""
import argparse
import csv
import json
import os
from datetime import date, datetime, timezone
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
        for row in reader:
            # Physical ending line of the record, including blanks and quoted newlines.
            line = reader.line_num
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'{table}:{line}: malformed CSV row')
            row = {key: value.strip() for key, value in row.items()}
            missing_fields = [
                key for key, value in row.items()
                if key != 'delivered_at' and not value
            ]
            if missing_fields:
                raise ValueError(
                    f'{table}:{line}: missing required value in {", ".join(missing_fields)}'
                )
            if table == 'orders':
                dates = {}
                for key in ('ordered_at', 'estimated_delivery_at', 'delivered_at'):
                    if row[key]:
                        try:
                            parsed = date.fromisoformat(row[key])
                        except ValueError as exc:
                            raise ValueError(
                                f'{table}:{line}: {key} must be a valid YYYY-MM-DD date'
                            ) from exc
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
                    try:
                        row[key] = int(row[key])
                    except ValueError as exc:
                        raise ValueError(
                            f'{table}:{line}: {key} must be an integer'
                        ) from exc
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
    # Reports must read an existing database, never create or modify one.
    database_uri = Path(database).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(database_uri, uri=True)
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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=('Relative paths are resolved from your current working directory. '
                'Input column definitions: docs/data_dictionary.md.'),
    )
    parser.add_argument(
        '--input', type=Path, default=ROOT / 'data/sample', metavar='DIR',
        help=('Folder containing customers.csv, products.csv, orders.csv, '
              'and order_items.csv; the default uses synthetic demo data'),
    )
    parser.add_argument(
        '--output', type=Path, default=ROOT / 'artifacts', metavar='DIR',
        help=('Folder for commerce.sqlite, CSV reports, and run_manifest.json; '
              'existing generated files are replaced on rerun'),
    )
    args = parser.parse_args()
    # Avoid overwriting user input by accidentally exporting into the source folder.
    if args.input.resolve() == args.output.resolve():
        parser.error('--output must differ from --input')
    database = args.output / 'commerce.sqlite'
    counts = build_database(args.input, database)
    export_reports(database, args.output)
    # Report generation time, not the source dataset's extraction time.
    manifest = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                'source': str(args.input.resolve()),
                'synthetic_sample': args.input.resolve() == (ROOT / 'data/sample').resolve(),
                'loaded_rows': counts, 'reports': REPORTS + ['order_summary']}
    (args.output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Validated {sum(counts.values())} rows. Reports: {args.output.resolve()}')


if __name__ == '__main__':
    main()
