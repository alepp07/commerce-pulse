import csv
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from commerce_pulse.pipeline import build_database, export_reports


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input'
        shutil.copytree(ROOT / 'data/sample', self.source)
        self.db = self.root / 'commerce.sqlite'

    def report(self, name):
        build_database(self.source, self.db)
        export_reports(self.db, self.root / 'reports')
        with (self.root / f'reports/{name}.csv').open() as handle:
            return list(csv.DictReader(handle))

    def test_sales_excludes_cancelled_and_shipped_without_double_counting(self):
        rows = self.report('monthly_sales')
        self.assertEqual([int(r['delivered_orders']) for r in rows], [2, 2])
        self.assertEqual([float(r['merchandise_value']) for r in rows], [180, 115])
        self.assertEqual(float(rows[0]['average_order_value']), 90)
        self.assertEqual(float(rows[1]['month_over_month_pct']), -36.11)

    def test_delivery_boundary_and_repeat_customers(self):
        rows = {r['region']: r for r in self.report('delivery_performance')}
        self.assertEqual(float(rows['Central']['late_delivery_pct']), 0)
        self.assertEqual(float(rows['North']['late_delivery_pct']), 50)
        self.assertEqual(float(self.report('repeat_customers')[0]['repeat_customer_pct']), 100)

    def test_repeat_rate_counts_customers_with_delivered_orders_only(self):
        path = self.source / 'orders.csv'
        path.write_text(path.read_text().replace('O003,C001,delivered',
                                                 'O003,C003,delivered'))
        # C001 and C003 each have one delivery; C002 has two.
        # C003's cancelled order is not a repeat, and C004 is shipped-only.
        self.assertEqual(self.report('repeat_customers'), [{
            'purchasing_customers': '3',
            'repeat_customers': '1',
            'repeat_customer_pct': '33.33',
        }])

    def test_category_totals_and_units_match_delivered_sales(self):
        rows = self.report('category_sales')
        actual = [
            (r['category'], int(r['units']), int(r['delivered_orders']),
             float(r['merchandise_value']), int(r['value_rank']))
            for r in rows
        ]
        self.assertEqual(actual, [
            ('Electronics', 2, 2, 200.0, 1),
            ('Home', 1, 1, 50.0, 2),
            ('Books', 3, 2, 45.0, 3),
        ])
        # An order spanning categories contributes once to each category.
        # Merchandise value is additive; category order counts are not.
        self.assertEqual(sum(float(r['merchandise_value']) for r in rows), 295.0)

    def test_equal_category_values_share_rank(self):
        path = self.source / 'order_items.csv'
        path.write_text(path.read_text().replace('O002,1,P002,1,5000',
                                                 'O002,1,P002,1,4500'))
        rows = self.report('category_sales')
        self.assertEqual(
            [(r['category'], int(r['value_rank'])) for r in rows],
            [('Electronics', 1), ('Books', 2), ('Home', 2)],
        )

    def test_duplicate_failure_preserves_existing_database(self):
        build_database(self.source, self.db)
        original = self.db.read_bytes()
        with (self.source / 'customers.csv').open('a') as handle:
            handle.write('C001,Central\n')
        with self.assertRaises(sqlite3.IntegrityError):
            build_database(self.source, self.db)
        self.assertEqual(original, self.db.read_bytes())

    def test_malformed_csv_quoting_preserves_existing_database(self):
        build_database(self.source, self.db)
        original = self.db.read_bytes()
        path = self.source / 'products.csv'
        for row in ('P001,"Unclosed\n', 'P001,"Home"x\n'):
            with self.subTest(row=row):
                path.write_text('product_id,category\n' + row, encoding='utf-8')
                with self.assertRaises(csv.Error):
                    build_database(self.source, self.db)
                self.assertEqual(self.db.read_bytes(), original)

    def test_quoted_category_text_survives_import_and_export(self):
        categories = {
            'P001': 'Electronics, audio',
            'P002': 'Home "special"',
            'P003': 'Books\nMultiline',
        }
        with (self.source / 'products.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(['product_id', 'category'])
            writer.writerows(categories.items())
        rows = self.report('category_sales')
        self.assertEqual(
            {row['category']: float(row['merchandise_value']) for row in rows},
            {'Electronics, audio': 200.0, 'Home "special"': 50.0,
             'Books\nMultiline': 45.0},
        )

    def test_order_without_items_preserves_existing_database(self):
        build_database(self.source, self.db)
        original = self.db.read_bytes()
        path = self.source / 'order_items.csv'
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = [row for row in reader if row['order_id'] != 'O001']
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        # O001 has multiple items; removing all of them must not silently
        # remove the order from the order_summary view and sales reports.
        with self.assertRaisesRegex(ValueError, 'orders have no items'):
            build_database(self.source, self.db)
        self.assertEqual(self.db.read_bytes(), original)

    def test_orphan_product_rejected(self):
        path = self.source / 'order_items.csv'
        path.write_text(path.read_text().replace('P001', 'UNKNOWN'))
        with self.assertRaises(sqlite3.IntegrityError):
            build_database(self.source, self.db)

    def test_invalid_delivery_rejected(self):
        path = self.source / 'orders.csv'
        path.write_text(path.read_text().replace('2025-01-04', '2024-12-01'))
        with self.assertRaises(ValueError):
            build_database(self.source, self.db)

    def test_status_delivery_date_mismatch_preserves_existing_database(self):
        build_database(self.source, self.db)
        original = self.db.read_bytes()
        path = self.source / 'orders.csv'
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            source_rows = list(reader)
        cases = [
            ('O001', ''),           # Delivered orders require an actual date.
            ('O004', '2025-02-07'), # Cancelled orders must have no actual date.
            ('O005', '2025-02-08'), # Shipped orders must have no actual date.
        ]
        for order_id, delivered_at in cases:
            with self.subTest(order_id=order_id):
                rows = [dict(row) for row in source_rows]
                for row in rows:
                    if row['order_id'] == order_id:
                        row['delivered_at'] = delivered_at
                with path.open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaisesRegex(ValueError, 'status and delivery date disagree'):
                    build_database(self.source, self.db)
                self.assertEqual(self.db.read_bytes(), original)

    def test_monthly_growth_across_year_boundary(self):
        path = self.source / 'orders.csv'
        # Move January/February to December/January while preserving day values.
        path.write_text(path.read_text().replace('2025-01', '2024-12')
                                        .replace('2025-02', '2025-01'))
        rows = self.report('monthly_sales')
        self.assertEqual([row['month'] for row in rows], ['2024-12', '2025-01'])
        self.assertEqual([float(row['merchandise_value']) for row in rows],
                         [180.0, 115.0])
        self.assertEqual(rows[0]['month_over_month_pct'], '')
        self.assertEqual(float(rows[1]['month_over_month_pct']), -36.11)

    def test_nonconsecutive_month_has_no_growth_rate(self):
        path = self.source / 'orders.csv'
        path.write_text(path.read_text().replace('2025-02', '2025-03'))
        self.assertEqual(self.report('monthly_sales')[1]['month_over_month_pct'], '')

    def test_no_delivered_orders_exports_empty_reports_and_undefined_rate(self):
        path = self.source / 'orders.csv'
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        for row in rows:
            row['status'] = 'shipped'
            row['delivered_at'] = ''
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        build_database(self.source, self.db)
        output = self.root / 'reports'
        export_reports(self.db, output)
        for name in ('monthly_sales', 'category_sales', 'delivery_performance'):
            with self.subTest(report=name):
                with (output / f'{name}.csv').open(newline='') as handle:
                    reader = csv.DictReader(handle)
                    self.assertTrue(reader.fieldnames)
                    self.assertEqual(list(reader), [])
        with (output / 'repeat_customers.csv').open(newline='') as handle:
            self.assertEqual(list(csv.DictReader(handle)), [{
                'purchasing_customers': '0',
                'repeat_customers': '0',
                'repeat_customer_pct': '',
            }])
        with (output / 'order_summary.csv').open(newline='') as handle:
            exported = list(csv.DictReader(handle))
        self.assertEqual(len(exported), len(rows))
        self.assertTrue(all(row['is_late'] == '' and row['delivery_days'] == ''
                            for row in exported))

    def test_zero_value_month_growth_boundaries(self):
        path = self.source / 'order_items.csv'
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            original = list(reader)
        cases = [
            ({'O001', 'O002'}, [0.0, 115.0], ''),
            ({'O003', 'O006'}, [180.0, 0.0], '-100.0'),
        ]
        for free_orders, expected_values, expected_growth in cases:
            with self.subTest(free_orders=sorted(free_orders)):
                rows = [dict(row) for row in original]
                for row in rows:
                    if row['order_id'] in free_orders:
                        row['unit_price_cents'] = '0'
                with path.open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                report = self.report('monthly_sales')
                self.assertEqual([r['month'] for r in report], ['2025-01', '2025-02'])
                self.assertEqual([int(r['delivered_orders']) for r in report], [2, 2])
                self.assertEqual([float(r['merchandise_value']) for r in report],
                                 expected_values)
                self.assertEqual(report[0]['month_over_month_pct'], '')
                self.assertEqual(report[1]['month_over_month_pct'], expected_growth)

    def test_export_missing_database_does_not_create_file(self):
        with self.assertRaises(sqlite3.OperationalError):
            export_reports(self.db, self.root / 'reports')
        self.assertFalse(self.db.exists())
        self.assertEqual(list((self.root / 'reports').glob('*.csv')), [])

    def test_export_special_character_path_preserves_database(self):
        database = self.root / 'sales # 100%.sqlite'
        build_database(self.source, database)
        original = database.read_bytes()
        output = self.root / 'reports'
        export_reports(str(database), output)
        self.assertEqual(database.read_bytes(), original)
        with (output / 'monthly_sales.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([float(row['merchandise_value']) for row in rows], [180, 115])
        self.assertEqual(
            {path.name for path in output.glob('*.csv')},
            {'monthly_sales.csv', 'category_sales.csv', 'delivery_performance.csv',
             'repeat_customers.csv', 'order_summary.csv'},
        )

    def test_rerun_does_not_duplicate_data(self):
        first = self.report('monthly_sales')
        self.assertEqual(first, self.report('monthly_sales'))


if __name__ == '__main__':
    unittest.main()
