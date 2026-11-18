
-- Query-2
-- Description: Calculate the count, sum of extended prices, average discount, minimum ship date, and maximum receipt date from the jlineitem table.
-- Difficulty: Medium
SELECT
    COUNT(*) AS count_of_line_items,
    SUM(CAST(JSON_EXTRACT(json => json_data, path => '$.L_EXTENDEDPRICE', path_syntax => 'json_path') AS FLOAT)) AS sum,
    AVG(CAST(JSON_EXTRACT(json => json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT)) AS avg,
    MIN(CAST(JSON_EXTRACT(json => json_data, path => '$.L_SHIPDATE', path_syntax => 'json_path') AS DATE)) AS min,
    MAX(CAST(JSON_EXTRACT(json => json_data, path => '$.L_RECEIPTDATE', path_syntax => 'json_path') AS DATE)) AS max
FROM {firebolt_database}.{firebolt_schema}.jlineitem;