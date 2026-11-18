-- Query-8
-- Description: Aggregate and display the top 5 longest cleaned comments (from orders and line items) containing 'final' for each customer, along with their total comment count, limited to 1000 customers.
-- Difficulty: Hard
WITH order_comments AS (
    SELECT 
        c.c_custkey,
        c.c_name,
        LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE 
            WHEN LENGTH(o.o_comment) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM {database}.{schema}.orders o
    JOIN {database}.{schema}.customer c ON o.o_custkey = c.c_custkey
),
lineitem_comments AS (
    SELECT 
        c.c_custkey,
        c.c_name,
        LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE 
            WHEN LENGTH(l.l_comment) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM {database}.{schema}.lineitem l
    JOIN {database}.{schema}.orders o ON l.l_orderkey = o.o_orderkey
    JOIN {database}.{schema}.customer c ON o.o_custkey = c.c_custkey
),
combined_comments AS (
    SELECT * FROM order_comments
    UNION ALL
    SELECT * FROM lineitem_comments
),
comment_counts AS (
    SELECT 
        c_custkey,
        COUNT(*) AS total_comments
    FROM combined_comments
    GROUP BY c_custkey
),
filtered_comments AS (
    SELECT 
        cc.c_custkey,
        cc.c_name,
        cc.cleaned_comment,
        cc.comment_type,
        COALESCE(ccc.total_comments, 0) AS total_comments
    FROM combined_comments cc
    LEFT JOIN comment_counts ccc ON cc.c_custkey = ccc.c_custkey
    WHERE cc.cleaned_comment LIKE '%final%' 
),
ranked_comments AS (
    SELECT 
        c_custkey,
        c_name,
        cleaned_comment,
        comment_type,
        total_comments,
        ROW_NUMBER() OVER (PARTITION BY c_custkey ORDER BY LENGTH(cleaned_comment) DESC) AS comment_rank
    FROM filtered_comments
)
SELECT 
    rc.c_custkey, 
    rc.c_name, 
    STRING_AGG(rc.cleaned_comment || ' (' || rc.comment_type || ')', ' | ') AS customer_comments,
    MAX(rc.total_comments) AS total_comments_per_customer
FROM ranked_comments rc
WHERE rc.comment_rank <= 5 
GROUP BY rc.c_custkey, rc.c_name
ORDER BY total_comments_per_customer DESC LIMIT 1000;