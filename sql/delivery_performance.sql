SELECT region, COUNT(*) AS delivered_orders,
       SUM(is_late) AS late_orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_delivery_pct,
       ROUND(AVG(delivery_days), 2) AS average_delivery_days
FROM order_summary WHERE status = 'delivered'
GROUP BY region ORDER BY late_delivery_pct DESC, region;
