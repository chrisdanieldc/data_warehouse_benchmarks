-- Query-11
-- Description: Retrieve order details and aggregated line item revenue and discount for orders with a total line item revenue greater than 50000 and an average line item discount less than 0.05, limited to 1000 orders.
-- Difficulty: Medium
SELECT 
    o.o_orderkey::INT AS orderkey, 
    o.o_orderdate::DATE AS orderdate, 
    o.o_totalprice::DECIMAL AS totalprice, 
    lineitems.total_revenue, 
    lineitems.avg_discount
FROM (
    SELECT 
        l.l_orderkey::INT AS orderkey, 
        SUM(l.l_extendedprice::DECIMAL * (1 - l.l_discount::DECIMAL)) AS total_revenue,
        AVG(l.l_discount::DECIMAL) AS avg_discount
    FROM {database}.{schema}.lineitem l
    GROUP BY l.l_orderkey
) AS lineitems
JOIN {database}.{schema}.orders o
    ON lineitems.orderkey = o.o_orderkey::INT
WHERE lineitems.total_revenue > 50000
AND lineitems.avg_discount < 0.05
ORDER BY lineitems.total_revenue DESC LIMIT 1000;