-- Query 4
-- Description: Calculate aggregated metrics by ship date year/month, ship mode, and order priority, then apply row numbering window functions
-- Difficulty: Medium

WITH base_table AS (
    SELECT
        toYYYYMM(L_SHIPDATE) AS ship_year_month,
        L_SHIPMODE,
        O_ORDERPRIORITY AS order_priority,
        COUNT(*) AS count_of_line_items,
        SUM(L_EXTENDEDPRICE) AS sum,
        AVG(L_DISCOUNT) AS avg
    FROM snowflake_sample_data.tpch_sf1000.lineitem li
    LEFT JOIN snowflake_sample_data.tpch_sf1000.orders ord
        ON li.L_ORDERKEY = ord.O_ORDERKEY
    GROUP BY ship_year_month, L_SHIPMODE, order_priority
)
SELECT
    *,
    row_number() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
    row_number() OVER (PARTITION BY L_SHIPMODE ORDER BY avg) AS row_number_by_ship_mode
FROM base_table
LIMIT 1000;