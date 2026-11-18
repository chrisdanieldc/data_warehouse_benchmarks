-- Query-4
-- Description: Calculate aggregated line item metrics (count, sum, average) grouped by ship year-month, ship mode, and order priority, and then apply row numbering based on sum and average within partitions, limited to 1000 rows.
-- Difficulty: Medium
WITH base_table AS (
    SELECT 
        STRFTIME(l_shipdate, '%Y-%m') AS ship_year_month,
        l_shipmode AS L_SHIPMODE,
        o_orderpriority AS order_priority,
        COUNT(*) AS count_of_line_items,
        SUM(l_extendedprice::FLOAT) AS sum,
        AVG(l_discount::FLOAT) AS avg
    FROM {database}.{schema}.lineitem li
    LEFT JOIN {database}.{schema}.orders ord 
        ON li.l_orderkey::INT = ord.o_orderkey::INT
    GROUP BY ship_year_month, L_SHIPMODE, order_priority
)
SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
    ROW_NUMBER() OVER (PARTITION BY L_SHIPMODE ORDER BY avg) AS row_number_by_ship_mode
FROM base_table LIMIT 1000;