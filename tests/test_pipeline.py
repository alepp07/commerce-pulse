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

    def test_nonconsecutive_month_has_no_growth_rate(self):
        path = self.source / 'orders.csv'
        path.write_text(path.read_text().replace('2025-02', '2025-03'))
        self.assertEqual(self.report('monthly_sales')[1]['month_over_month_pct'], '')

    def test_rerun_does_not_duplicate_data(self):
        first = self.report('monthly_sales')
        self.assertEqual(first, self.report('monthly_sales'))


if __name__ == '__main__':
    unittest.main()
