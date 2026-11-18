
-- Query-4
-- Description: Analyze line items and orders, grouping by ship year-month, ship mode, and order priority, calculating counts, sums, and averages, and then ranking results.
-- Difficulty: Hard
WITH base_table AS (
    SELECT
        EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => li.json_data, path => '$.L_SHIPDATE', path_syntax => 'json_path') AS DATE)) || '-' ||
        LPAD(EXTRACT(MONTH FROM CAST(JSON_EXTRACT(json => li.json_data, path => '$.L_SHIPDATE', path_syntax => 'json_path') AS DATE))::STRING, 2, '0') AS ship_year_month,
        JSON_EXTRACT(json => li.json_data, path => '$.L_SHIPMODE', path_syntax => 'json_path') AS L_SHIPMODE,
        JSON_EXTRACT(json => ord.json_data, path => '$.O_ORDERPRIORITY', path_syntax => 'json_path') AS order_priority,
        COUNT(*) AS count_of_line_items,
        SUM(CAST(JSON_EXTRACT(json => li.json_data, path => '$.L_EXTENDEDPRICE', path_syntax => 'json_path') AS FLOAT)) AS sum,
        AVG(CAST(JSON_EXTRACT(json => li.json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT)) AS avg
    FROM {firebolt_database}.{firebolt_schema}.jlineitem li
    LEFT JOIN {firebolt_database}.{firebolt_schema}.jorders ord
        ON CAST(JSON_EXTRACT(json => li.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => ord.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT)
    GROUP BY ship_year_month, L_SHIPMODE, order_priority
)
SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
    ROW_NUMBER() OVER (PARTITION BY L_SHIPMODE ORDER BY avg) AS row_number_by_ship_mode
FROM base_table LIMIT 1000;