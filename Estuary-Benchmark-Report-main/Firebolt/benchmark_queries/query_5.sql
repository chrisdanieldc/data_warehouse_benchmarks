
-- Query-5
-- Description: Analyze customer sales, ranking customers by total spending and total quantity ordered within each order month.
-- Difficulty: Hard
WITH customer_sales AS (
    SELECT
        EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)) || ' - ' ||
        TO_CHAR(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE), 'Month') AS order_month,
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path') AS C_NAME,
        SUM(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_TOTALPRICE', path_syntax => 'json_path') AS FLOAT)) AS total_spent,
        SUM(CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_QUANTITY', path_syntax => 'json_path') AS INT)) AS total_quantity,
        RANK() OVER (
            PARTITION BY EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)) || ' - ' ||
                       TO_CHAR(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE), 'Month')
            ORDER BY SUM(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_TOTALPRICE', path_syntax => 'json_path') AS FLOAT)) DESC
        ) AS price_rank,
        RANK() OVER (
            PARTITION BY EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)) || ' - ' ||
                       TO_CHAR(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE), 'Month')
            ORDER BY SUM(CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_QUANTITY', path_syntax => 'json_path') AS INT)) DESC
        ) AS quantity_rank
    FROM {firebolt_database}.{firebolt_schema}.jorders o
    JOIN {firebolt_database}.{firebolt_schema}.jlineitem l
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT)
    JOIN {firebolt_database}.{firebolt_schema}.jcustomer c
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_CUSTKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT)
    GROUP BY order_month, C_NAME
)
SELECT order_month, C_NAME, total_spent, total_quantity, price_rank, quantity_rank
FROM customer_sales
WHERE price_rank <= 3 OR quantity_rank <= 3
ORDER BY order_month, price_rank, quantity_rank LIMIT 1000;