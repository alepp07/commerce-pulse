PRAGMA foreign_keys = ON;
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY NOT NULL,
    region TEXT NOT NULL
);
CREATE TABLE products (
    product_id TEXT PRIMARY KEY NOT NULL,
    category TEXT NOT NULL
);
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL CHECK (status IN ('delivered', 'shipped', 'cancelled')),
    ordered_at TEXT NOT NULL,
    estimated_delivery_at TEXT NOT NULL,
    delivered_at TEXT
);
CREATE TABLE order_items (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    item_id INTEGER NOT NULL CHECK (item_id > 0),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    PRIMARY KEY (order_id, item_id)
);
CREATE INDEX orders_customer_idx ON orders(customer_id);
-- Aggregate items before joining to orders to avoid counting multi-item orders twice.
CREATE VIEW order_summary AS
SELECT o.*, c.region, totals.item_value_cents,
       CASE WHEN o.status = 'delivered' THEN
           CASE WHEN date(o.delivered_at) > date(o.estimated_delivery_at) THEN 1 ELSE 0 END
       END AS is_late,
       CASE WHEN o.status = 'delivered' THEN
           julianday(o.delivered_at) - julianday(o.ordered_at)
       END AS delivery_days
FROM orders o
JOIN customers c USING (customer_id)
JOIN (
    SELECT order_id, SUM(quantity * unit_price_cents) AS item_value_cents
    FROM order_items GROUP BY order_id
) totals USING (order_id);
