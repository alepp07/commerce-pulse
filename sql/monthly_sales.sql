-- Delivered merchandise value by purchase month, not recognised accounting revenue.
WITH monthly AS (
    SELECT substr(ordered_at, 1, 7) AS month,
           COUNT(*) AS delivered_orders,
           SUM(item_value_cents) / 100.0 AS merchandise_value,
           SUM(item_value_cents) / 100.0 / COUNT(*) AS average_order_value
    FROM order_summary WHERE status = 'delivered'
    GROUP BY substr(ordered_at, 1, 7)
), previous AS (
    SELECT *, LAG(merchandise_value) OVER (ORDER BY month) AS previous_value,
           LAG(month) OVER (ORDER BY month) AS previous_month
    FROM monthly
)
SELECT month, delivered_orders, merchandise_value, ROUND(average_order_value, 2) AS average_order_value,
       CASE WHEN previous_month = strftime('%Y-%m', date(month || '-01', '-1 month'))
            THEN ROUND(100.0 * (merchandise_value - previous_value) / NULLIF(previous_value, 0), 2)
       END AS month_over_month_pct
FROM previous ORDER BY month;
