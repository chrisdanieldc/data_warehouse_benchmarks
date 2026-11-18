-- Query-2
-- Description: Get basic aggregate statistics (count, sum, average, min, max) for line items.
-- Difficulty: Easy
SELECT 
    COUNT(*) AS count_of_line_items,
    SUM(l_extendedprice::FLOAT) AS sum,
    AVG(l_discount::FLOAT) AS avg,
    MIN(l_shipdate::DATE) AS min,
    MAX(l_receiptdate::DATE) AS max
FROM {database}.{schema}.lineitem;