-- Query 3
-- Description: Uses window functions to show each line’s price, the next line’s price, previous ship date, and first line price per order
-- Difficulty: Medium
SELECT 
    L_ORDERKEY, 
    L_LINENUMBER, 
    L_SHIPDATE, 
    L_EXTENDEDPRICE, 
    LEAD(L_EXTENDEDPRICE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS next_line_price,
    LAG(L_SHIPDATE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS prev_ship_date,
    FIRST_VALUE(L_EXTENDEDPRICE) OVER (PARTITION BY L_ORDERKEY ORDER BY L_LINENUMBER) AS first_line_price
FROM LINEITEM
ORDER BY L_ORDERKEY, L_LINENUMBER LIMIT 1000;
