-- Query-5
-- Description: Identify top 3 customers by total spent and total quantity within each order month, limited to 1000 rows.
-- Difficulty: Medium
WITH customer_sales AS (
    SELECT 
        STRFTIME(o.o_orderdate, '%Y - %B') AS order_month,
        c.c_name,
        SUM(o.o_totalprice) AS total_spent,
        SUM(l.l_quantity) AS total_quantity,
        RANK() OVER (PARTITION BY STRFTIME(o.o_orderdate, '%Y - %B') ORDER BY SUM(o.o_totalprice) DESC) AS price_rank,
        RANK() OVER (PARTITION BY STRFTIME(o.o_orderdate, '%Y - %B') ORDER BY SUM(l.l_quantity) DESC) AS quantity_rank
    FROM {database}.{schema}.orders o
    JOIN {database}.{schema}.lineitem l ON o.o_orderkey = l.l_orderkey
    JOIN {database}.{schema}.customer c ON o.o_custkey = c.c_custkey
    GROUP BY STRFTIME(o.o_orderdate, '%Y - %B'), c.c_name
)
SELECT order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
FROM customer_sales
WHERE price_rank <= 3 OR quantity_rank <= 3
ORDER BY order_month, price_rank, quantity_rank LIMIT 1000;