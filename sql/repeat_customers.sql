-- Repeat purchase is measured across the supplied observation window.
WITH purchases AS (
    SELECT customer_id, COUNT(*) AS delivered_orders
    FROM orders WHERE status = 'delivered' GROUP BY customer_id
)
SELECT COUNT(*) AS purchasing_customers,
       COALESCE(SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END), 0) AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 2) AS repeat_customer_pct
FROM purchases;
