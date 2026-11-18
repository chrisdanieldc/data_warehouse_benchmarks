-- Query 8
-- Description: Extracts and ranks up to 5 of each customer’s longest comments containing “final”, showing comment type and total comment count
-- Difficulty: Medium
WITH order_comments AS (
    SELECT 
        c.c_custkey,
        c.c_name,
        LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE 
            WHEN LENGTH(o.o_comment) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM ORDERS o
    JOIN CUSTOMER c ON o.o_custkey = c.c_custkey
),
LINEITEM_comments AS (
    SELECT 
        c.c_custkey,
        c.c_name,
        LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
        CASE ...             WHEN LENGTH(l.l_comment) > 100 THEN 'LONG_COMMENT'
            ELSE 'SHORT_COMMENT'
        END AS comment_type
    FROM LINEITEM l
    JOIN ORDERS o ON l.l_orderkey = o.o_orderkey
    JOIN CUSTOMER c ON o.o_custkey = c.c_custkey
),
combined_comments AS (
    SELECT * FROM order_comments
    UNION ALL
    SELECT * FROM LINEITEM_comments
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
        total_comments,...         ROW_NUMBER() OVER (PARTITION BY c_custkey ORDER BY LENGTH(cleaned_comment) DESC) AS comment_rank
    FROM filtered_comments
)
SELECT 
    rc.c_custkey, 
    rc.c_name, 
    GROUP_CONCAT(rc.cleaned_comment || ' (' || rc.comment_type || ')' ORDER BY rc.comment_rank SEPARATOR ' | ') AS customer_comments,
    MAX(rc.total_comments) AS total_comments_per_customer
FROM ranked_comments rc
WHERE rc.comment_rank <= 5 
GROUP BY rc.c_custkey, rc.c_name
ORDER BY total_comments_per_customer DESC LIMIT 1000;
