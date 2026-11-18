-- Query 4
-- Description: Groups line items by ship month, ship mode, and order priority, then ranks by sum and average discount using window functions
-- Difficulty: Medium
WITH base_table AS (
    SELECT ...         DATE_FORMAT(CAST(li.LINEITEM::$l_shipdate AS DATETIME), '%Y-%m') AS ship_year_month,
        li.LINEITEM::$l_shipmode AS L_SHIPMODE,
        ord.ORDERS::$o_orderpriority AS order_priority,
        COUNT(*) AS count_of_line_items,
        SUM(li.LINEITEM::%l_extendedprice) AS sum,
        AVG(li.LINEITEM::%l_discount) AS avg
    FROM JLINEITEM li
    LEFT JOIN JORDERS ord 
        ON JSON_EXTRACT_BIGINT(li.LINEITEM, '$.l_orderkey') = JSON_EXTRACT_BIGINT(ord.ORDERS, '$.o_orderkey')
    GROUP BY 
        DATE_FORMAT(CAST(li.LINEITEM::$l_shipdate AS DATETIME), '%Y-%m'),
        li.LINEITEM::$l_shipmode,
        ord.ORDERS::$o_orderpriority
)
SELECT 
    base_table.*,
    ROW_NUMBER() OVER (PARTITION BY base_table.order_priority ORDER BY base_table.sum) AS row_number_by_order_priority,
    ROW_NUMBER() OVER (PARTITION BY base_table.L_SHIPMODE ORDER BY base_table.avg) AS row_number_by_ship_mode
FROM base_table
LIMIT 1000;
