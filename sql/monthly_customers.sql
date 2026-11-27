-- A buyer counts once per purchase month, even with multiple delivered orders.
WITH customer_months AS (
    SELECT DISTINCT customer_id, substr(ordered_at, 1, 7) AS month
    FROM orders
    WHERE status = 'delivered'
), purchase_history AS (
    SELECT month, MIN(month) OVER (PARTITION BY customer_id) AS first_month
    FROM customer_months
)
SELECT month,
       COUNT(*) AS purchasing_customers,
       COUNT(CASE WHEN month = first_month THEN 1 END) AS first_observed_customers,
       COUNT(CASE WHEN month > first_month THEN 1 END) AS returning_customers
FROM purchase_history
GROUP BY month
ORDER BY month;
