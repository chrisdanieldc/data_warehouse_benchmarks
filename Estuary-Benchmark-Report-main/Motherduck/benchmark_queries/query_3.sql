-- Query-3
-- Description: Retrieve line item details along with the extended price of the next line item, the ship date of the previous line item, and the extended price of the first line item within the same order, limited to 1000 rows.
-- Difficulty: Medium
SELECT 
    l_orderkey, 
    l_linenumber, 
    l_shipdate, 
    l_extendedprice, 
    LEAD(l_extendedprice) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS next_line_price,
    LAG(l_shipdate) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS prev_ship_date,
    FIRST_VALUE(l_extendedprice) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS first_line_price
FROM {database}.{schema}.lineitem
ORDER BY l_orderkey, l_linenumber LIMIT 1000;