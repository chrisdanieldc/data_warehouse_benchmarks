-- Query 7
-- Description: Filters top 3 customers per month by spending or quantity, only including those whose customer number digits sum to an odd number
-- Difficulty: Medium
WITH customer_sales AS (
    SELECT 
        DATE_FORMAT(o.o_orderdate, '%Y - %M') AS order_month,
        c.c_name,
        SUM(o.o_totalprice) AS total_spent,
        SUM(l.l_quantity) AS total_quantity,
        RANK() OVER (PARTITION BY DATE_FORMAT(o.o_orderdate, '%Y - %M') ORDER BY SUM(o.o_totalprice) DESC) AS price_rank,...         RANK() OVER (PARTITION BY DATE_FORMAT(o.o_orderdate, '%Y - %M') ORDER BY SUM(l.l_quantity) DESC) AS quantity_rank
    FROM ORDERS o
    JOIN LINEITEM l ON o.o_orderkey = l.l_orderkey
    JOIN CUSTOMER c ON o.o_custkey = c.c_custkey
    GROUP BY order_month, c.c_name
),
number_extraction AS (
    SELECT *,
           REGEXP_REPLACE(c_name, '[^0-9]', '') AS customer_number
    FROM customer_sales
),
numbers AS (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
    SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
),
digit_sum_calc AS (
    SELECT 
        ne.order_month, ne.c_name, ne.total_spent, ne.total_quantity, ne.price_rank, ne.quantity_rank, ne.customer_number,
        SUM(CAST(SUBSTRING(ne.customer_number, n.n + 1, 1) AS SIGNED)) AS number_sum 
    FROM number_extraction ne
    JOIN numbers n
    ON n.n < LENGTH(ne.customer_number)...     GROUP BY ne.order_month, ne.c_name, ne.total_spent, ne.total_quantity, ne.price_rank, ne.quantity_rank, ne.customer_number
)
SELECT order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
FROM digit_sum_calc
WHERE (price_rank <= 3 OR quantity_rank <= 3)  
AND MOD(number_sum, 2) = 1  
ORDER BY order_month, price_rank, quantity_rank 
LIMIT 1000;
