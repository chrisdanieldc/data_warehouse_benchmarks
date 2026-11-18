-- Query 7
-- Description: Rank customers by spending and quantity per month, extract numbers from customer names, sum the digits, and filter for top ranks with odd digit sums
-- Difficulty: Hard

WITH customer_sales AS (
    SELECT
        formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
        C_NAME,
        SUM(O_TOTALPRICE) AS total_spent,
        SUM(L_QUANTITY) AS total_quantity,
        rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M')
                    ORDER BY SUM(O_TOTALPRICE) DESC) AS price_rank,
        rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M')
                    ORDER BY SUM(L_QUANTITY) DESC) AS quantity_rank
    FROM snowflake_sample_data.tpch_sf1000.orders o
    JOIN snowflake_sample_data.tpch_sf1000.lineitem l
        ON o.O_ORDERKEY = l.L_ORDERKEY
    JOIN snowflake_sample_data.tpch_sf1000.customer c
        ON o.O_CUSTKEY = c.C_CUSTKEY
    GROUP BY order_month, C_NAME
),
number_extraction AS (
    SELECT *,
        replaceRegexpAll(C_NAME, '[^0-9]', '') AS customer_number
    FROM customer_sales
),
digit_sum_calc AS (
    SELECT
        order_month,
        C_NAME,
        total_spent,
        total_quantity,
        price_rank,
        quantity_rank,
        customer_number,
        sum(toInt32(arrayJoin(splitByString('', customer_number)))) AS number_sum
    FROM number_extraction
    GROUP BY
        order_month,
        C_NAME,
        total_spent,
        total_quantity,
        price_rank,
        quantity_rank,
        customer_number
)
SELECT
    order_month,
    C_NAME,
    total_spent,
    total_quantity,
    price_rank,
    quantity_rank
FROM digit_sum_calc
WHERE (price_rank <= 3 OR quantity_rank <= 3)
AND modulo(number_sum, 2) = 1
ORDER BY order_month, price_rank, quantity_rank
LIMIT 1000;