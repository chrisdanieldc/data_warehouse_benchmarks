-- Query 11
-- Description: Joins orders and line items (JSON), selecting orders with high revenue and low average discount
-- Difficulty: Medium
SELECT 
    JSON_EXTRACT_JSON(o.ORDERS, '$.o_orderkey') AS orderkey, 
    JSON_EXTRACT_JSON(o.ORDERS, '$.o_orderdate') AS orderdate, 
    JSON_EXTRACT_JSON(o.ORDERS, '$.o_totalprice') AS totalprice, 
    li.total_revenue, 
    li.avg_discount
FROM (
    SELECT 
        JSON_EXTRACT_JSON(LINEITEM, '$.l_orderkey') AS orderkey, 
        SUM(JSON_EXTRACT_JSON(LINEITEM, '$.l_extendedprice') * 
            (1 - JSON_EXTRACT_JSON(LINEITEM, '$.l_discount'))) AS total_revenue,
        AVG(JSON_EXTRACT_JSON(LINEITEM, '$.l_discount')) AS avg_discount
    FROM JLINEITEM
    GROUP BY JSON_EXTRACT_JSON(LINEITEM, '$.l_orderkey')
) AS li
JOIN JORDERS AS o...         ON li.orderkey = JSON_EXTRACT_JSON(o.ORDERS, '$.o_orderkey')
WHERE li.total_revenue > 50000
AND li.avg_discount < 0.05
ORDER BY li.total_revenue DESC 
LIMIT 1000;
