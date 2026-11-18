-- Query 3
-- Description: Use window functions to get preceding and following row values and the first value within a partition
-- Difficulty: Medium

SELECT
        L_ORDERKEY,
        L_LINENUMBER,
        L_SHIPDATE,
        L_EXTENDEDPRICE,
        anyOrNull(L_EXTENDEDPRICE) OVER (
            PARTITION BY L_ORDERKEY
            ORDER BY L_LINENUMBER
            ROWS BETWEEN 1 FOLLOWING AND 1 FOLLOWING
        ) AS next_line_price,
        anyOrNull(L_SHIPDATE) OVER (
            PARTITION BY L_ORDERKEY
            ORDER BY L_LINENUMBER
            ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING
        ) AS prev_ship_date,
        any(L_EXTENDEDPRICE) OVER (
            PARTITION BY L_ORDERKEY
            ORDER BY L_LINENUMBER
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_line_price
FROM snowflake_sample_data.tpch_sf1000.lineitem
ORDER BY L_ORDERKEY, L_LINENUMBER
LIMIT 1000;