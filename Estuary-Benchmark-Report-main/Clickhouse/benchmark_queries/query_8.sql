-- Query 8
-- Description: Analyze customer comments from orders and lineitems, filtering for comments containing 'final', ranking them, and aggregating the top comments per customer
-- Difficulty: Hard

WITH order_comments AS (
    SELECT
        c.C_CUSTKEY,
        c.C_NAME,
        lower(trim(replaceRegexpAll(o.O_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE
            WHEN length(o.O_COMMENT) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM snowflake_sample_data.tpch_sf1000.orders o
    JOIN snowflake_sample_data.tpch_sf1000.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
),
lineitem_comments AS (
    SELECT
        c.C_CUSTKEY,
        c.C_NAME,
        lower(trim(replaceRegexpAll(l.L_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE
            WHEN length(l.L_COMMENT) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM snowflake_sample_data.tpch_sf1000.lineitem l
    JOIN snowflake_sample_data.tpch_sf1000.orders o ON l.L_ORDERKEY = o.O_ORDERKEY
    JOIN snowflake_sample_data.tpch_sf1000.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
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
    WHERE position('final', cc.cleaned_comment) > 0
),
ranked_comments AS (
    SELECT
        C_CUSTKEY,
        C_NAME,
        cleaned_comment,
        comment_type,
        total_comments,
        row_number() OVER (PARTITION BY C_CUSTKEY ORDER BY length(cleaned_comment) DESC) AS comment_rank
    FROM filtered_comments
)
SELECT
    rc.C_CUSTKEY,
    rc.C_NAME,
    groupArray(concat(rc.cleaned_comment, ' (', rc.comment_type, ')')) AS customer_comments,
    MAX(rc.total_comments) AS total_comments_per_customer
FROM ranked_comments rc
WHERE rc.comment_rank <= 5
GROUP BY rc.C_CUSTKEY, rc.C_NAME
ORDER BY total_comments_per_customer DESC
LIMIT 1000;