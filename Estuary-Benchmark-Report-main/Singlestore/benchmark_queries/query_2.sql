-- Query 2
-- Description: Aggregates count, sum, average discount, earliest ship date, and latest receipt date from the JLINEITEM table
-- Difficulty: Easy
SELECT 
    COUNT(*) AS count_of_line_items,
    SUM(LINEITEM::%l_extendedprice) AS sum,
    AVG(LINEITEM::%l_discount) AS avg,
    MIN(CAST(LINEITEM::$l_shipdate AS DATETIME)) AS min,
    MAX(CAST(LINEITEM::$l_receiptdate AS DATETIME)) AS max
FROM JLINEITEM;
