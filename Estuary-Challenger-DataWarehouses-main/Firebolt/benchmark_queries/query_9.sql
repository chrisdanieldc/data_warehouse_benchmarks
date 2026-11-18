
-- Query-9
-- Description: Analyze customer order history to calculate total orders, total revenue, and the percentage of orders shipped within 30 days for customers in the last 30 years.
-- Difficulty: Hard
WITH customer_orders AS (
    SELECT
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) AS C_CUSTKEY,
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path') AS C_NAME,
        CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) AS O_ORDERDATE,
        COUNT(*) AS total_orders,
        SUM(CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_EXTENDEDPRICE', path_syntax => 'json_path') AS FLOAT) *
            (1 - CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT))) AS total_revenue,
        SUM(CASE
            WHEN CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_SHIPDATE', path_syntax => 'json_path') AS DATE) <=
                 DATE_ADD('day', 30, CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE))
            THEN 1 ELSE 0 END) AS shipped_orders
    FROM {firebolt_database}.{firebolt_schema}.jcustomer c
    JOIN {firebolt_database}.{firebolt_schema}.jorders o
        ON CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_CUSTKEY', path_syntax => 'json_path') AS INT)
    JOIN {firebolt_database}.{firebolt_schema}.jlineitem l
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT)
    WHERE CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) >= DATE_ADD('year', -30, CURRENT_DATE)
    GROUP BY
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT),
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path'),
        CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)
),
customer_metrics AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        SUM(total_orders) AS total_orders_per_customer,
        SUM(total_revenue) AS total_revenue_per_customer,
        SUM(shipped_orders) AS total_shipped_orders_per_customer,
        AVG(total_revenue / NULLIF(total_orders, 0)) AS avg_revenue_per_order
    FROM customer_orders
    GROUP BY C_CUSTKEY, C_NAME
),
customer_ratios AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        total_orders_per_customer,
        total_revenue_per_customer,
        total_shipped_orders_per_customer,
        avg_revenue_per_order,
        CAST(total_shipped_orders_per_customer AS FLOAT) / NULLIF(total_orders_per_customer, 0) AS shipped_ratio
    FROM customer_metrics
)
SELECT
    C_CUSTKEY,
    C_NAME,
    total_orders_per_customer,
    total_revenue_per_customer,
    avg_revenue_per_order,
    shipped_ratio * 100 AS shipped_percentage
FROM customer_ratios
WHERE shipped_ratio > 0.5
ORDER BY avg_revenue_per_order DESC LIMIT 1000;