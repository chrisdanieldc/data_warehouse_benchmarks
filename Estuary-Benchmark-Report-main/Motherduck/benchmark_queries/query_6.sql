-- Query-6
-- Description: Find the top 5 most frequent non-stop words in combined order and line item comments for each order month, limited to 1000 rows.
-- Difficulty: Hard
WITH combined_comments AS (
    SELECT 
        STRFTIME(o.o_orderdate, '%Y - %B') AS order_month,
        LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM {database}.{schema}.orders o
    UNION ALL
    SELECT 
        STRFTIME(o.o_orderdate, '%Y - %B') AS order_month,
        LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM {database}.{schema}.lineitem l
    JOIN {database}.{schema}.orders o 
    ON l.l_orderkey = o.o_orderkey
),
tokenized_words AS (
    SELECT 
        cc.order_month,
        word
    FROM combined_comments cc,
        UNNEST(STRING_SPLIT(cc.cleaned_comment, ' ')) AS word(word)
),
word_counts AS (
    SELECT 
        order_month,
        word,
        COUNT(*) AS word_count,
        RANK() OVER (PARTITION BY order_month ORDER BY COUNT(*) DESC) AS rank
    FROM tokenized_words
    WHERE word NOT IN ('the', 'is', 'and', 'or', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at')
    GROUP BY order_month, word
)
SELECT order_month, word, word_count
FROM word_counts
WHERE rank <= 5  
ORDER BY order_month, word_count DESC LIMIT 1000;