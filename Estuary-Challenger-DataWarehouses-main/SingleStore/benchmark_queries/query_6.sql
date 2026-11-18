-- Query 6
-- Description: Tokenizes and counts the most common non-stopwords in order and lineitem comments per month
-- Difficulty: Medium
WITH combined_comments AS (
    SELECT 
        DATE_FORMAT(o.o_orderdate, '%Y - %M') AS order_month,...         LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM ORDERS o
    UNION ALL
    SELECT 
        DATE_FORMAT(o.o_orderdate, '%Y - %M') AS order_month,
        LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
    FROM LINEITEM l
    JOIN ORDERS o 
        ON l.l_orderkey = o.o_orderkey
),
numbers AS (
    SELECT ROW_NUMBER() OVER () - 1 AS n
    FROM (SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL 
          SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10) AS t
),
tokenized_words AS (
    SELECT 
        cc.order_month,
        TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(cc.cleaned_comment, ' ', n + 1), ' ', -1)) AS word
    FROM combined_comments cc
    JOIN numbers n
    WHERE n.n < (LENGTH(cc.cleaned_comment) - LENGTH(REPLACE(cc.cleaned_comment, ' ', '')) + 1)...         AND TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(cc.cleaned_comment, ' ', n + 1), ' ', -1)) != ''
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
