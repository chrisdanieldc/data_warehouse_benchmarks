
-- Query-11
-- Description: Retrieve order details along with the total revenue and average discount for each order where the total revenue exceeds 50,000 and the average discount is less than 5%.
-- Difficulty: Medium
SELECT
    CAST(JSON_EXTRACT(json => orders.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT) AS orderkey,
    CAST(JSON_EXTRACT(json => orders.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) AS orderdate,
    CAST(JSON_EXTRACT(json => orders.json_data, path => '$.O_TOTALPRICE', path_syntax => 'json_path') AS FLOAT) AS totalprice,
    lineitems.total_revenue,
    lineitems.avg_discount
FROM (
      SELECT
        CAST(JSON_EXTRACT(json => json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT) AS orderkey,
        SUM(CAST(JSON_EXTRACT(json => json_data, path => '$.L_EXTENDEDPRICE', path_syntax => 'json_path') AS FLOAT) *
            (1 - CAST(JSON_EXTRACT(json => json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT))) AS total_revenue,
        AVG(CAST(JSON_EXTRACT(json => json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT)) AS avg_discount
    FROM {firebolt_database}.{firebolt_schema}.jlineitem
    GROUP BY CAST(JSON_EXTRACT(json => json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT)
) AS lineitems
JOIN {firebolt_database}.{firebolt_schema}.jorders AS orders
    ON lineitems.orderkey = CAST(JSON_EXTRACT(json => orders.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT)
WHERE lineitems.total_revenue > 50000
AND lineitems.avg_discount < 0.05
ORDER BY lineitems.total_revenue DESC LIMIT 1000;