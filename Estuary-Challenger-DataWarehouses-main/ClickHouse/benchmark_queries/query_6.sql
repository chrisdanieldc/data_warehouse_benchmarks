-- Query 6
-- Description: Extract, clean, and count words from order and lineitem comments, ranking the most frequent words per month
-- Difficulty: Hard

WITH combined_comments AS (
    SELECT
        formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
        lower(trim(replaceRegexpAll(O_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM snowflake_sample_data.tpch_sf1000.orders o

    UNION ALL

    SELECT
        formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
        lower(trim(replaceRegexpAll(L_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM snowflake_sample_data.tpch_sf1000.lineitem l
    JOIN snowflake_sample_data.tpch_sf1000.orders o
    ON l.L_ORDERKEY = o.O_ORDERKEY
),
tokenized_words AS (
    SELECT
        order_month,
        splitByString(' ', cleaned_comment) AS words
    FROM combined_comments
),
flattened_words AS (
    SELECT
        order_month,
        arrayJoin(words) AS word
    FROM tokenized_words
    WHERE word NOT IN ('the', 'is', 'and', 'or', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at')
),
word_counts AS (
    SELECT
        order_month,
        word,
        COUNT(*) AS word_count,
        rank() OVER (PARTITION BY order_month ORDER BY COUNT(*) DESC) AS rank
    FROM flattened_words
    GROUP BY order_month, word
)
SELECT
    order_month,
    word,
    word_count
FROM word_counts
WHERE rank <= 5
ORDER BY order_month, word_count DESC
LIMIT 1000;