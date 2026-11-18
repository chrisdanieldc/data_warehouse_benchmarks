-- Query-1
-- Description: Calculate the total sum of extended prices for all line items.
-- Difficulty: Easy
SELECT 
    SUM(L_EXTENDEDPRICE) AS sum
FROM {database}.{schema}.lineitem;