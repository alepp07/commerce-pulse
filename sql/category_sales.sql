WITH categories AS (
    SELECT p.category, SUM(i.quantity) AS units,
           COUNT(DISTINCT o.order_id) AS delivered_orders,
           SUM(i.quantity * i.unit_price_cents) / 100.0 AS merchandise_value
    FROM order_items i
    JOIN products p USING (product_id)
    JOIN orders o USING (order_id)
    WHERE o.status = 'delivered'
    GROUP BY p.category
)
SELECT *, DENSE_RANK() OVER (ORDER BY merchandise_value DESC) AS value_rank
FROM categories ORDER BY value_rank, category;
