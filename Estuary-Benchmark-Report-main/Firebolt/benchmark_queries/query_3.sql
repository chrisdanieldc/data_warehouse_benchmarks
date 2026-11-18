
-- Query-3
-- Description: Retrieve order key, line number, ship date, extended price, the next extended price, the previous ship date, and the first extended price for each order.
-- Difficulty: Medium
SELECT
    L_ORDERKEY,
    L_LINENUMBER,
    L_SHIPDATE,
    L_EXTENDEDPRICE,
    LEAD(L_EXTENDEDPRICE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS next_line_price,
    LAG(L_SHIPDATE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS prev_ship_date,
    FIRST_VALUE(L_EXTENDEDPRICE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS first_line_price
FROM {firebolt_database}.{firebolt_schema}.lineitem
ORDER BY L_ORDERKEY, L_LINENUMBER LIMIT 1000;