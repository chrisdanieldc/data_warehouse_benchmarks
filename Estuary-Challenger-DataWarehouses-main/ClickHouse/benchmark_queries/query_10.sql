-- Query 10
-- Description: Calculate customer metrics like total orders, revenue, average revenue per order, and the percentage of orders shipped within 30 days, filtering for customers with a shipped ratio over 50%
-- Difficulty: Medium

WITH customer_orders AS (
    SELECT
        c.C_CUSTKEY,
        c.C_NAME,
        o.O_ORDERDATE,
        COUNT(*) AS total_orders,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        SUM(if(l.L_SHIPDATE <= addDays(o.O_ORDERDATE, 30), 1, 0)) AS shipped_orders
    FROM snowflake_sample_data.tpch_sf1000.customer c
    JOIN snowflake_sample_data.tpch_sf1000.orders o ON c.O_CUSTKEY = o.O_CUSTKEY
    JOIN snowflake_sample_data.tpch_sf1000.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
    WHERE o.O_ORDERDATE >= subtractYears(today(), 30)
    GROUP BY c.C_CUSTKEY, c.C_NAME, o.O_ORDERDATE
),
customer_metrics AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        SUM(total_orders) AS total_orders_per_customer,
        SUM(total_revenue) AS total_revenue_per_customer,
        SUM(shipped_orders) AS total_shipped_orders_per_customer,
        avg(if(total_orders = 0, NULL, total_revenue / total_orders)) AS avg_revenue_per_order
    FROM customer_orders
    GROUP BY C_CUSTKEY, C_NAME
),
customer_ratios AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        total_orders_per_customer,
        total_revenue_per_customer,
        total_shipped_orders_per_customer,
        avg_revenue_per_order,
        if(total_orders_per_customer = 0, NULL,
           toFloat64(total_shipped_orders_per_customer) / total_orders_per_customer) AS shipped_ratio
    FROM customer_metrics
)
SELECT
    C_CUSTKEY,
    C_NAME,
    total_orders_per_customer,
    total_revenue_per_customer,
    avg_revenue_per_order,
    shipped_ratio * 100 AS shipped_percentage
FROM customer_ratios
WHERE shipped_ratio > 0.5
ORDER BY avg_revenue_per_order DESC
LIMIT 1000;