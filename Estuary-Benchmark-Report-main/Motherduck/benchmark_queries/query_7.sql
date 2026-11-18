-- Query-7
-- Description: Identify top 3 customers by total spent or total quantity within each order month, filtered by customers whose extracted number from their name has an odd sum of digits, limited to 1000 rows.
-- Difficulty: Hard
WITH customer_sales AS (
    SELECT 
        strftime(o.o_orderdate, '%Y - %B') AS order_month,
        c.c_name AS c_name,
        SUM(o.o_totalprice) AS total_spent,
        SUM(l.l_quantity) AS total_quantity,
        RANK() OVER (PARTITION BY strftime(o.o_orderdate, '%Y - %B')
                    ORDER BY SUM(o.o_totalprice) DESC) AS price_rank,
        RANK() OVER (PARTITION BY strftime(o.o_orderdate, '%Y - %B')
                    ORDER BY SUM(l.l_quantity) DESC) AS quantity_rank
    FROM {database}.{schema}.orders o
    JOIN {database}.{schema}.lineitem l 
        ON o.o_orderkey = l.l_orderkey
    JOIN {database}.{schema}.customer c 
        ON o.o_custkey = c.c_custkey
    GROUP BY order_month, c_name
),
number_extraction AS (
    SELECT *,
        regexp_replace(c_name, '[^0-9]', '', 'g') AS customer_number  
    FROM customer_sales
),
digit_sum_calc AS (
    SELECT 
        order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank, customer_number,
        SUM(value::INTEGER) AS number_sum 
    FROM number_extraction,
        unnest(string_split(customer_number, '')) AS t(value)
    GROUP BY order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank, customer_number
)
SELECT order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
FROM digit_sum_calc
WHERE (price_rank <= 3 OR quantity_rank <= 3)  
AND MOD(number_sum, 2) = 1  
ORDER BY order_month, price_rank, quantity_rank 
LIMIT 1000;