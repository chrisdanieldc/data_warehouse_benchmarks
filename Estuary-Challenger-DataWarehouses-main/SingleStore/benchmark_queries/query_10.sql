-- Query 10
-- Description: Computes customer order and revenue stats, average revenue per order, and percent of orders shipped within 30 days, filtering for >50% shipped
-- Difficulty: Medium
WITH customer_ORDERS AS (
    SELECT 
        c.C_CUSTKEY,
        c.C_NAME,
        o.O_ORDERDATE,
        COUNT(*) AS total_ORDERS,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        SUM(CASE WHEN l.L_SHIPDATE <= DATE_ADD(o.O_ORDERDATE, INTERVAL 30 DAY) THEN 1 ELSE 0 END) AS shipped_ORDERS 
    FROM CUSTOMER c
    JOIN ORDERS o ON c.C_CUSTKEY = o.O_CUSTKEY
    JOIN LINEITEM l ON o.O_ORDERKEY = l.L_ORDERKEY
    WHERE o.O_ORDERDATE >= DATE_SUB(CURRENT_DATE, INTERVAL 30 YEAR) ...         GROUP BY c.C_CUSTKEY, c.C_NAME, o.O_ORDERDATE
),
customer_metrics AS (
    SELECT 
        C_CUSTKEY,
        C_NAME,
        SUM(total_ORDERS) AS total_ORDERS_per_customer,
        SUM(total_revenue) AS total_revenue_per_customer,
        SUM(shipped_ORDERS) AS total_shipped_ORDERS_per_customer,
        AVG(total_revenue / NULLIF(total_ORDERS, 0)) AS avg_revenue_per_order 
    FROM customer_ORDERS
    GROUP BY C_CUSTKEY, C_NAME
),
customer_ratios AS (
    SELECT 
        C_CUSTKEY,
        C_NAME,
        total_ORDERS_per_customer,
        total_revenue_per_customer,
        total_shipped_ORDERS_per_customer,
        avg_revenue_per_order,
        1.0 * total_shipped_ORDERS_per_customer / NULLIF(total_ORDERS_per_customer, 0) AS shipped_ratio 
    FROM customer_metrics
)
SELECT 
    C_CUSTKEY,
    C_NAME,
    total_ORDERS_per_customer,
    total_revenue_per_customer,...         avg_revenue_per_order,
    shipped_ratio * 100 AS shipped_percentage 
FROM customer_ratios
WHERE shipped_ratio > 0.5 
ORDER BY avg_revenue_per_order DESC 
LIMIT 1000;
