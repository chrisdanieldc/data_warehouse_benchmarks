
-- Query-6
-- Description: Analyze comments from orders and line items to find the top 5 most frequent words (excluding common English words) for each order month.
-- Difficulty: Hard
WITH combined_comments AS (
    SELECT
        EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)) || ' - ' ||
        TO_CHAR(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE), 'Month') AS order_month,
        LOWER(REGEXP_REPLACE(JSON_EXTRACT(json => o.json_data, path => '$.O_COMMENT', path_syntax => 'json_path'), '[^a-zA-Z0-9 ]', '')) AS cleaned_comment
    FROM {firebolt_database}.{firebolt_schema}.jorders o

    UNION ALL

    SELECT
        EXTRACT(YEAR FROM CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE)) || ' - ' ||
        TO_CHAR(CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERDATE', path_syntax => 'json_path') AS DATE), 'Month') AS order_month,
        LOWER(REGEXP_REPLACE(JSON_EXTRACT(json => l.json_data, path => '$.L_COMMENT', path_syntax => 'json_path'), '[^a-zA-Z0-9 ]', '')) AS cleaned_comment
    FROM {firebolt_database}.{firebolt_schema}.jlineitem l
    JOIN {firebolt_database}.{firebolt_schema}.jorders o
        ON CAST(JSON_EXTRACT(json => l.json_data, path => '$.L_ORDERKEY', path_syntax => 'json_path') AS INT) =
           CAST(JSON_EXTRACT(json => o.json_data, path => '$.O_ORDERKEY', path_syntax => 'json_path') AS INT)
),
tokenized_words AS (
    SELECT
        order_month,
        TRIM(word) AS word
    FROM combined_comments,
    UNNEST(STRING_TO_ARRAY(cleaned_comment, ' ')) AS word
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