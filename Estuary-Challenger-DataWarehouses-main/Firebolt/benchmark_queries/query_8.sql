-- Query-8
-- Description: Analyze comments from orders and line items for each customer, categorizing them by length and finding customers with the most "final" keyword mentions.
-- Difficulty: Hard
WITH order_comments AS (
    SELECT
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) AS C_CUSTKEY,
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path') AS C_NAME,
        LOWER(REGEXP_REPLACE(JSON_EXTRACT(json => o.json_data, path => '$.O_COMMENT', path_syntax => 'json_path'), '[^a-zA-Z0-9 ]', '')) AS cleaned_comment,
        CASE
            WHEN LENGTH(JSON_EXTRACT(json => o.json_data, path => '$.O_COMMENT', path_syntax => 'json_path')) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM {firebolt_database}.{firebolt_schema}.jorders o
    JOIN {firebolt_database}.{firebolt_schema}.jcustomer c
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_CUSTKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT)
),
lineitem_comments AS (
    SELECT
        CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT) AS C_CUSTKEY,
        JSON_EXTRACT(json => c.json_data, path => '$.C_NAME', path_syntax => 'json_path') AS C_NAME,
        LOWER(REGEXP_REPLACE(JSON_EXTRACT(json => l.json_data, path => '$.L_COMMENT', path_syntax => 'json_path'), '[^a-zA-Z0-9 ]', '')) AS cleaned_comment,
        CASE
            WHEN LENGTH(JSON_EXTRACT(json => l.json_data, path => '$.L_COMMENT', path_syntax => 'json_path')) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM {firebolt_database}.{firebolt_schema}.jlineitem l
    JOIN {firebolt_database}.{firebolt_schema}.jorders o
        ON CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT)
    JOIN {firebolt_database}.{firebolt_schema}.jcustomer c
        ON CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_CUSTKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => c.json_data, path => '$.C_CUSTKEY', path_syntax => 'json_path') AS INT)
),
combined_comments AS (
    SELECT * FROM order_comments
    UNION ALL
    SELECT * FROM lineitem_comments
),
comment_counts AS (
    SELECT
        C_CUSTKEY,
        COUNT(*) AS total_comments
    FROM combined_comments
    GROUP BY C_CUSTKEY
),
filtered_comments AS (
    SELECT
        cc.C_CUSTKEY,
        cc.C_NAME,
        cc.cleaned_comment,
        cc.comment_type,
        COALESCE(ccc.total_comments, 0) AS total_comments
    FROM combined_comments cc
    LEFT JOIN comment_counts ccc ON cc.C_CUSTKEY = ccc.C_CUSTKEY
    WHERE cc.cleaned_comment LIKE '%final%'
),
ranked_comments AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        cleaned_comment,
        comment_type,
        total_comments,
        ROW_NUMBER() OVER (PARTITION BY C_CUSTKEY ORDER BY LENGTH(cleaned_comment) DESC) AS comment_rank
    FROM filtered_comments
)
SELECT
    rc.C_CUSTKEY,
    rc.C_NAME,
    ARRAY_AGG(CONCAT(rc.cleaned_comment, ' (', rc.comment_type, ')')) AS customer_comments,
    MAX(rc.total_comments) AS total_comments_per_customer
FROM ranked_comments rc
WHERE rc.comment_rank <= 5
GROUP BY rc.C_CUSTKEY, rc.C_NAME
ORDER BY total_comments_per_customer DESC LIMIT 1000;