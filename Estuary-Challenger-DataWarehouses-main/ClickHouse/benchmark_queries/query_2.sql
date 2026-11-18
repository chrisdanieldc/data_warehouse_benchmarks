-- Query 2
-- Description: Aggregate various metrics (count, sum, average, min, max) from the lineitem table
-- Difficulty: Easy

SELECT
        COUNT(*) AS count_of_line_items,
        SUM(L_EXTENDEDPRICE) AS sum,
        AVG(L_DISCOUNT) AS avg,
        MIN(L_SHIPDATE) AS min,
        MAX(L_RECEIPTDATE) AS max
FROM snowflake_sample_data.tpch_sf1000.lineitem;