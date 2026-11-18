-- Query 5
-- Description: Rank customers by total spent and total quantity per month using window functions and filter for top ranks
-- Difficulty: Medium

WITH customer_sales AS (
    SELECT
        formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
        C_NAME,
        SUM(O_TOTALPRICE) AS total_spent,
        SUM(L_QUANTITY) AS total_quantity,
        rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M') ORDER BY SUM(O_TOTALPRICE) DESC) AS price_rank,
        rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M') ORDER BY SUM(L_QUANTITY) DESC) AS quantity_rank
    FROM snowflake_sample_data.tpch_sf1000.orders o
    JOIN snowflake_sample_data.tpch_sf1000.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
    JOIN snowflake_sample_data.tpch_sf1000.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
    GROUP BY formatDateTime(O_ORDERDATE, '%Y - %M'), C_NAME
)
SELECT
    order_month,
    C_NAME,
    total_spent,
    total_quantity,
    price_rank,
    quantity_rank
FROM customer_sales
WHERE price_rank <= 3 OR quantity_rank <= 3
ORDER BY order_month, price_rank, quantity_rank
LIMIT 1000;