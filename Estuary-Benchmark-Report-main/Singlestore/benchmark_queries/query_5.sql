-- Query 5
-- Description: Ranks customers by total spent and quantity per month, returning top 3 by each metric
-- Difficulty: Medium
WITH customer_sales AS (...         SELECT 
        DATE_FORMAT(o.o_orderdate, '%Y - %M') AS order_month,
        c.c_name,
        SUM(o.o_totalprice) AS total_spent,
        SUM(l.l_quantity) AS total_quantity,
        RANK() OVER (PARTITION BY DATE_FORMAT(o.o_orderdate, '%Y - %M') ORDER BY SUM(o.o_totalprice) DESC) AS price_rank,
        RANK() OVER (PARTITION BY DATE_FORMAT(o.o_orderdate, '%Y - %M') ORDER BY SUM(l.l_quantity) DESC) AS quantity_rank
    FROM ORDERS o
    JOIN LINEITEM l ON o.o_orderkey = l.l_orderkey
    JOIN CUSTOMER c ON o.o_custkey = c.c_custkey
    GROUP BY order_month, c.c_name
)
SELECT order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
FROM customer_sales
WHERE price_rank <= 3 OR quantity_rank <= 3
ORDER BY order_month, price_rank, quantity_rank LIMIT 1000;
