-- Query 9
-- Description: Calculates each customer’s monthly order and revenue summary, with cumulative revenue and a formatted monthly summary string
-- Difficulty: Medium
WITH customer_ORDERS AS (
    SELECT 
        c.C_CUSTKEY,
        c.C_NAME,
        o.O_ORDERDATE,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        COUNT(*) AS order_count,
        ROW_NUMBER() OVER (PARTITION BY c.C_CUSTKEY ORDER BY o.O_ORDERDATE ASC) AS order_rank
    FROM CUSTOMER c
    JOIN ORDERS o ON c.C_CUSTKEY = o.O_CUSTKEY
    JOIN LINEITEM l ON o.O_ORDERKEY = l.L_ORDERKEY...         WHERE o.O_ORDERDATE >= DATE_SUB(CURRENT_DATE, INTERVAL 30 YEAR)
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
        SUM(total_revenue) OVER (PARTITION BY C_CUSTKEY ORDER BY order_rank ASC) AS cumulative_revenue 
    FROM customer_ORDERS
),
monthly_analysis AS (
    SELECT 
        C_CUSTKEY,
        C_NAME,
        DATE_FORMAT(O_ORDERDATE, '%Y-%m-01') AS order_month,
        COUNT(*) AS monthly_ORDERS,
        SUM(total_revenue) AS monthly_revenue
    FROM cumulative_revenue
    GROUP BY C_CUSTKEY, C_NAME, DATE_FORMAT(O_ORDERDATE, '%Y-%m-01')
)
SELECT 
    m.C_CUSTKEY,
    m.C_NAME,
    GROUP_CONCAT(
        CONCAT('Month: ', DATE_FORMAT(order_month, '%Y-%m'), ...             ', ORDERS: ', monthly_ORDERS, 
        ', Revenue: ', FORMAT(monthly_revenue, 2))
        ORDER BY order_month SEPARATOR ' | '
    ) AS monthly_summary,
    MAX(c.cumulative_revenue) AS lifetime_revenue 
FROM monthly_analysis m
JOIN cumulative_revenue c ON m.C_CUSTKEY = c.C_CUSTKEY
GROUP BY m.C_CUSTKEY, m.C_NAME
ORDER BY lifetime_revenue DESC 
LIMIT 1000;
