
-- Query-10
-- Description: Analyze customer order patterns to calculate cumulative revenue and monthly order summaries for customers with at least one order shipped after the order date in the last 30 years.
-- Difficulty: Hard
WITH customer_orders AS (
    SELECT
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) AS C_CUSTKEY,
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path') AS C_NAME,
        CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) AS O_ORDERDATE,
        SUM(CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_EXTENDEDPRICE', path_syntax => 'json_path') AS FLOAT) *
            (1 - CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_DISCOUNT', path_syntax => 'json_path') AS FLOAT))) AS total_revenue,
        COUNT(*) AS order_count,
        ROW_NUMBER() OVER (PARTITION BY CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT)
                         ORDER BY CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) ASC) AS order_rank
    FROM {firebolt_database}.{firebolt_schema}.jcustomer c
    JOIN {firebolt_database}.{firebolt_schema}.jorders o
        ON CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_CUSTKEY', path_syntax => 'json_path') AS INT)
    JOIN {firebolt_database}.{firebolt_schema}.jlineitem l
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT)
    WHERE CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE) >= DATE_ADD('year', -30, CURRENT_DATE)
      AND CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_SHIPDATE', path_syntax => 'json_path') AS DATE) >
          CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)
    GROUP BY
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT),
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path'),
        CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)
),
cumulative_revenue AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        order_rank,
        O_ORDERDATE,
        total_revenue,
        SUM(total_revenue) OVER (PARTITION BY C_CUSTKEY ORDER BY order_rank ASC) AS cumulative_revenue
    FROM customer_orders
),
monthly_analysis AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        DATE_TRUNC('month', O_ORDERDATE) AS order_month,
        COUNT(*) AS monthly_orders,
        SUM(total_revenue) AS monthly_revenue
    FROM cumulative_revenue
    GROUP BY C_CUSTKEY, C_NAME, DATE_TRUNC('month', O_ORDERDATE)
),
customer_lifetime AS (
    SELECT
        C_CUSTKEY,
        MAX(cumulative_revenue) AS lifetime_revenue
    FROM cumulative_revenue
    GROUP BY C_CUSTKEY
),
monthly_summary AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        ARRAY_SORT(
            ARRAY_AGG(
                CONCAT('Month: ', TO_CHAR(order_month, 'YYYY-MM'),
                      ', Orders: ', CAST(monthly_orders AS STRING),
                      ', Revenue: ', CAST(ROUND(monthly_revenue, 2) AS STRING))
            )
        ) AS monthly_summary
    FROM monthly_analysis
    GROUP BY C_CUSTKEY, C_NAME
)
SELECT
    ms.C_CUSTKEY,
    ms.C_NAME,
    ms.monthly_summary,
    cl.lifetime_revenue
FROM monthly_summary ms
JOIN customer_lifetime cl ON ms.C_CUSTKEY = cl.C_CUSTKEY
ORDER BY cl.lifetime_revenue DESC
LIMIT 1000;