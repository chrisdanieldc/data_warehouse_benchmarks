-- Query 9
-- Description: Analyze customer order history over the last 30 years, calculating monthly revenue and order counts, cumulative revenue, and aggregating monthly summaries
-- Difficulty: Hard

WITH customer_orders AS (
    SELECT
        c.C_CUSTKEY,
        c.C_NAME,
        o.O_ORDERDATE,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        COUNT(*) AS order_count,
        row_number() OVER (PARTITION BY c.C_CUSTKEY ORDER BY o.O_ORDERDATE) AS order_rank
    FROM snowflake_sample_data.tpch_sf1000.customer c
    JOIN snowflake_sample_data.tpch_sf1000.orders o ON c.C_CUSTKEY = o.O_CUSTKEY
    JOIN snowflake_sample_data.tpch_sf1000.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
    WHERE O_ORDERDATE >= subtractYears(today(), 30)
    AND l.L_SHIPDATE > o.O_ORDERDATE
    GROUP BY c.C_CUSTKEY, c.C_NAME, o.O_ORDERDATE
),
cumulative_revenue AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        order_rank,
        O_ORDERDATE,
        total_revenue,
        sum(total_revenue) OVER (PARTITION BY C_CUSTKEY ORDER BY order_rank) AS cumulative_revenue
    FROM customer_orders
),
monthly_analysis AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        toStartOfMonth(O_ORDERDATE) AS order_month,
        COUNT(*) AS monthly_orders,
        SUM(total_revenue) AS monthly_revenue
    FROM cumulative_revenue
    GROUP BY C_CUSTKEY, C_NAME, toStartOfMonth(O_ORDERDATE)
)
SELECT
    m.C_CUSTKEY,
    m.C_NAME,
    groupArray(
        concat(
            'Month: ', formatDateTime(order_month, '%Y-%m'),
            ', Orders: ', toString(monthly_orders),
            ', Revenue: ', toString(round(monthly_revenue, 2))
        )
    ) AS monthly_summary,
    MAX(cumulative_revenue) AS lifetime_revenue
FROM monthly_analysis m
JOIN cumulative_revenue c ON m.C_CUSTKEY = c.C_CUSTKEY AND toStartOfMonth(m.O_ORDERDATE) = toStartOfMonth(c.O_ORDERDATE) -- Added join condition for month
GROUP BY m.C_CUSTKEY, m.C_NAME
ORDER BY lifetime_revenue DESC
LIMIT 1000;