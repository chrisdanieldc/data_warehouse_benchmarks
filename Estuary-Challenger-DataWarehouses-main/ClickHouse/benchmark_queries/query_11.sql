-- Query 11
-- Description: Join orders with aggregated lineitem data to find orders with high total revenue and low average discount
-- Difficulty: Medium

SELECT
    o.O_ORDERKEY AS orderkey,
    o.O_ORDERDATE AS orderdate,
    o.O_TOTALPRICE AS totalprice,
    lineitems.total_revenue,
    lineitems.avg_discount
FROM (
    SELECT
        l.L_ORDERKEY AS orderkey,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        AVG(l.L_DISCOUNT) AS avg_discount
    FROM snowflake_sample_data.tpch_sf1000.lineitem l
    GROUP BY l.L_ORDERKEY
) AS lineitems
JOIN snowflake_sample_data.tpch_sf1000.orders o
    ON lineitems.orderkey = o.O_ORDERKEY
WHERE lineitems.total_revenue > 50000
AND lineitems.avg_discount < 0.05
ORDER BY lineitems.total_revenue DESC
LIMIT 1000;