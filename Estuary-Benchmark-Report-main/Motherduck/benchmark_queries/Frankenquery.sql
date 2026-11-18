-- Query-F
-- Description: A comprehensive analysis of supplier performance covering delivery metrics, transaction frequency, seasonal patterns (quarterly and monthly), part supply chain diversification, geographic performance at nation and region levels, customer satisfaction via order lifecycle, supplier-customer diversity, and calculated supplier risk scores, aggregating various metrics at different granularities.
-- Difficulty: Hard
WITH supplier_delivery_metrics AS (
    SELECT
        s.s_suppkey,
        s.s_name,
        s.s_nationkey,
        s.s_acctbal,
        s.s_address,
        s.s_phone,
        COUNT(DISTINCT l.l_orderkey) AS total_orders,
        AVG(DATE_DIFF('day', l.l_commitdate, l.l_receiptdate)) AS avg_delivery_delay,
        PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY DATE_DIFF('day', l.l_commitdate, l.l_receiptdate)) AS median_delivery_delay,
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY DATE_DIFF('day', l.l_commitdate, l.l_receiptdate)) AS p90_delivery_delay,
        SUM(CASE WHEN l.l_receiptdate > l.l_commitdate THEN 1 ELSE 0 END) AS late_deliveries,
        SUM(CASE WHEN l.l_receiptdate <= l.l_commitdate THEN 1 ELSE 0 END) AS on_time_deliveries,
        SUM(CASE WHEN DATE_DIFF('day', l.l_commitdate, l.l_receiptdate) > 7 THEN 1 ELSE 0 END) AS severely_late_deliveries,
        SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue,
        SUM(l.l_extendedprice * (1 - l.l_discount) * l.l_tax) AS total_tax,
        SUM(l.l_quantity) AS total_quantity,
        AVG(l.l_discount) AS avg_discount_rate,
        MAX(l.l_discount) AS max_discount_offered,
        STDDEV(l.l_extendedprice * (1 - l.l_discount)) AS revenue_volatility,
        VARIANCE(l.l_extendedprice * (1 - l.l_discount)) AS revenue_variance,
        MIN(l.l_shipdate) AS first_shipment_date,
        MAX(l.l_shipdate) AS last_shipment_date,
        DATE_DIFF('day', MIN(l.l_shipdate), MAX(l.l_shipdate)) AS active_days,
        COUNT(DISTINCT l.l_partkey) AS unique_parts_shipped
    FROM {database}.{schema}.supplier s
    JOIN {database}.{schema}.lineitem l ON s.s_suppkey = l.l_suppkey
    GROUP BY s.s_suppkey, s.s_name, s.s_nationkey, s.s_acctbal, s.s_address, s.s_phone
),
supplier_transaction_frequency AS (
    SELECT
        l_suppkey,
        DATE_TRUNC('month', l_shipdate) AS ship_month,
        COUNT(*) AS transactions_per_month,
        SUM(l_quantity) AS quantity_per_month,
        SUM(l_extendedprice * (1 - l_discount)) AS revenue_per_month,
        LAG(COUNT(*)) OVER (PARTITION BY l_suppkey ORDER BY DATE_TRUNC('month', l_shipdate)) AS prev_month_transactions,
        LAG(SUM(l_quantity)) OVER (PARTITION BY l_suppkey ORDER BY DATE_TRUNC('month', l_shipdate)) AS prev_month_quantity,
        LAG(SUM(l_extendedprice * (1 - l_discount))) OVER (PARTITION BY l_suppkey ORDER BY DATE_TRUNC('month', l_shipdate)) AS prev_month_revenue,
        DATE_DIFF('month', LAG(DATE_TRUNC('month', l_shipdate)) OVER (PARTITION BY l_suppkey ORDER BY DATE_TRUNC('month', l_shipdate)), DATE_TRUNC('month', l_shipdate)) AS months_since_last_activity
    FROM {database}.{schema}.lineitem
    GROUP BY l_suppkey, ship_month
),
seasonal_patterns_quarterly AS (
    SELECT
        l.l_suppkey,
        EXTRACT(QUARTER FROM o.o_orderdate) AS quarter,
        EXTRACT(YEAR FROM o.o_orderdate) AS year,
        COUNT(DISTINCT o.o_orderkey) AS quarterly_orders,
        COUNT(DISTINCT EXTRACT(MONTH FROM o.o_orderdate)) AS active_months_in_quarter,
        SUM(l.l_quantity) AS quarterly_quantity,
        SUM(l.l_extendedprice * (1 - l.l_discount)) AS quarterly_revenue,
        AVG(l.l_extendedprice * (1 - l.l_discount)) AS avg_order_value_in_quarter,
        COUNT(DISTINCT l.l_partkey) AS unique_parts_in_quarter,
        LAG(SUM(l.l_quantity)) OVER (
            PARTITION BY l.l_suppkey, EXTRACT(QUARTER FROM o.o_orderdate) 
            ORDER BY EXTRACT(YEAR FROM o.o_orderdate)
        ) AS prev_year_quarterly_quantity,
        LAG(SUM(l.l_extendedprice * (1 - l.l_discount))) OVER (
            PARTITION BY l.l_suppkey, EXTRACT(QUARTER FROM o.o_orderdate) 
            ORDER BY EXTRACT(YEAR FROM o.o_orderdate)
        ) AS prev_year_quarterly_revenue
    FROM {database}.{schema}.lineitem l
    JOIN {database}.{schema}.orders o ON l.l_orderkey = o.o_orderkey
    GROUP BY l.l_suppkey, quarter, year
),
seasonal_patterns_monthly AS (
    SELECT
        l.l_suppkey,
        EXTRACT(MONTH FROM o.o_orderdate) AS month,
        EXTRACT(YEAR FROM o.o_orderdate) AS year,
        COUNT(DISTINCT o.o_orderkey) AS monthly_orders,
        SUM(l.l_quantity) AS monthly_quantity,
        SUM(l.l_extendedprice * (1 - l.l_discount)) AS monthly_revenue,
        LAG(SUM(l.l_quantity)) OVER (
            PARTITION BY l.l_suppkey, EXTRACT(MONTH FROM o.o_orderdate) 
            ORDER BY EXTRACT(YEAR FROM o.o_orderdate)
        ) AS prev_year_monthly_quantity,
        LAG(SUM(l.l_extendedprice * (1 - l.l_discount))) OVER (
            PARTITION BY l.l_suppkey, EXTRACT(MONTH FROM o.o_orderdate) 
            ORDER BY EXTRACT(YEAR FROM o.o_orderdate)
        ) AS prev_year_monthly_revenue
    FROM {database}.{schema}.lineitem l
    JOIN {database}.{schema}.orders o ON l.l_orderkey = o.o_orderkey
    GROUP BY l.l_suppkey, month, year
),
supplier_seasonality_quarterly AS (
    SELECT
        ssq.l_suppkey,
        quarter,
        year,
        quarterly_quantity,
        quarterly_revenue,
        unique_parts_in_quarter,
        active_months_in_quarter,
        CASE
            WHEN prev_year_quarterly_quantity > 0 THEN 
                (quarterly_quantity - prev_year_quarterly_quantity) / prev_year_quarterly_quantity * 100
            ELSE NULL
        END AS yoy_quantity_growth,
        CASE
            WHEN prev_year_quarterly_revenue > 0 THEN 
                (quarterly_revenue - prev_year_quarterly_revenue) / prev_year_quarterly_revenue * 100
            ELSE NULL
        END AS yoy_revenue_growth,
        DENSE_RANK() OVER (
            PARTITION BY l_suppkey 
            ORDER BY quarterly_quantity DESC
        ) AS quantity_quarter_rank,
        DENSE_RANK() OVER (
            PARTITION BY l_suppkey 
            ORDER BY quarterly_revenue DESC
        ) AS revenue_quarter_rank,
        quarterly_quantity / NULLIF(quarterly_orders, 0) AS avg_quantity_per_order,
        quarterly_revenue / NULLIF(quarterly_orders, 0) AS avg_revenue_per_order
    FROM seasonal_patterns_quarterly
),
supplier_seasonality_monthly AS (
    SELECT
        l_suppkey,
        month,
        year,
        monthly_quantity,
        monthly_revenue,
        CASE
            WHEN prev_year_monthly_quantity > 0 THEN 
                (monthly_quantity - prev_year_monthly_quantity) / prev_year_monthly_quantity * 100
            ELSE NULL
        END AS yoy_quantity_growth_monthly,
        CASE
            WHEN prev_year_monthly_revenue > 0 THEN 
                (monthly_revenue - prev_year_monthly_revenue) / prev_year_monthly_revenue * 100
            ELSE NULL
        END AS yoy_revenue_growth_monthly,
        DENSE_RANK() OVER (
            PARTITION BY l_suppkey 
            ORDER BY monthly_quantity DESC
        ) AS quantity_month_rank,
        DENSE_RANK() OVER (
            PARTITION BY l_suppkey 
            ORDER BY monthly_revenue DESC
        ) AS revenue_month_rank
    FROM seasonal_patterns_monthly
),
part_supplier_diversity AS (
    SELECT
        p.p_partkey,
        p.p_name,
        p.p_mfgr,
        p.p_brand,
        p.p_type,
        p.p_size,
        p.p_container,
        p.p_retailprice,
        COUNT(DISTINCT ps.ps_suppkey) AS supplier_count,
        MAX(ps.ps_supplycost) / NULLIF(MIN(ps.ps_supplycost), 0) AS cost_ratio,
        MAX(ps.ps_supplycost) - MIN(ps.ps_supplycost) AS cost_spread,
        STDDEV(ps.ps_supplycost) AS cost_volatility,
        AVG(ps.ps_supplycost) AS avg_cost,
        MIN(ps.ps_supplycost) AS min_cost,
        MAX(ps.ps_supplycost) AS max_cost,
        AVG(ps.ps_availqty) AS avg_availability,
        SUM(ps.ps_availqty) AS total_availability,
        MIN(ps.ps_availqty) AS min_availability,
        MAX(ps.ps_availqty) AS max_availability,
        VAR_POP(ps.ps_availqty) AS availability_variance
    FROM {database}.{schema}.part p
    JOIN {database}.{schema}.partsupp ps ON p.p_partkey = ps.ps_partkey
    GROUP BY 
        p.p_partkey, 
        p.p_name, 
        p.p_mfgr, 
        p.p_brand, 
        p.p_type, 
        p.p_size, 
        p.p_container, 
        p.p_retailprice
    HAVING COUNT(DISTINCT ps.ps_suppkey) > 1
),
part_category_analysis AS (
    SELECT
        SPLIT_PART(p.p_type, ' ', 1) AS part_category,
        COUNT(DISTINCT p.p_partkey) AS category_part_count,
        AVG(psd.supplier_count) AS avg_suppliers_per_part,
        MIN(psd.supplier_count) AS min_suppliers_per_part,
        MAX(psd.supplier_count) AS max_suppliers_per_part,
        AVG(psd.cost_ratio) AS avg_cost_ratio,
        AVG(psd.cost_volatility) AS avg_cost_volatility,
        SUM(p.p_retailprice * psd.total_availability) AS category_inventory_value,
        COUNT(DISTINCT ps.ps_suppkey) AS unique_suppliers_in_category
    FROM {database}.{schema}.part p
    JOIN part_supplier_diversity psd 
        ON p.p_partkey = psd.p_partkey
    JOIN {database}.{schema}.partsupp ps 
        ON p.p_partkey = ps.ps_partkey
    GROUP BY 
        part_category
),
nation_performance AS (
    SELECT
        n.n_nationkey,
        n.n_name AS nation,
        n.n_regionkey,
        COUNT(DISTINCT s.s_suppkey) AS supplier_count,
        AVG(sdm.avg_delivery_delay) AS nation_avg_delay,
        MEDIAN(sdm.avg_delivery_delay) AS nation_median_delay,
        AVG(sdm.p90_delivery_delay) AS nation_p90_delay,
        SUM(sdm.total_revenue) AS nation_revenue,
        SUM(sdm.total_quantity) AS nation_quantity,
        SUM(sdm.late_deliveries) / NULLIF(SUM(sdm.total_orders), 0) * 100 AS nation_late_delivery_pct,
        SUM(sdm.severely_late_deliveries) / NULLIF(SUM(sdm.total_orders), 0) * 100 AS nation_severely_late_pct,
        AVG(sdm.revenue_volatility) AS nation_avg_rev_volatility,
        SUM(sdm.unique_parts_shipped) AS nation_unique_parts,
        COUNT(DISTINCT l.l_partkey) AS nation_distinct_parts
    FROM {database}.{schema}.supplier s
    JOIN supplier_delivery_metrics sdm 
        ON s.s_suppkey = sdm.s_suppkey
    JOIN {database}.{schema}.nation n 
        ON s.s_nationkey = n.n_nationkey
    JOIN {database}.{schema}.lineitem l 
        ON s.s_suppkey = l.l_suppkey
    GROUP BY 
        n.n_nationkey, 
        n.n_name, 
        n.n_regionkey
),
region_performance AS (
    SELECT
        r.r_regionkey,
        r.r_name AS region,
        COUNT(DISTINCT s.s_suppkey) AS supplier_count,
        COUNT(DISTINCT n.n_nationkey) AS nations_count,
        AVG(np.nation_avg_delay) AS region_avg_delay,
        AVG(np.nation_median_delay) AS region_median_delay,
        SUM(np.nation_revenue) AS region_revenue,
        SUM(np.nation_quantity) AS region_quantity,
        SUM(np.nation_unique_parts) AS region_unique_parts,
        AVG(np.nation_late_delivery_pct) AS region_late_delivery_pct,
        AVG(np.nation_severely_late_pct) AS region_severely_late_pct,
        AVG(np.nation_avg_rev_volatility) AS region_avg_rev_volatility,
        MAX(np.nation_revenue) / NULLIF(MIN(np.nation_revenue), 0) AS nation_revenue_disparity,
        STDDEV(np.nation_late_delivery_pct) AS late_delivery_pct_stddev
    FROM {database}.{schema}.region r
    JOIN nation_performance np ON r.r_regionkey = np.n_regionkey
    JOIN {database}.{schema}.nation n ON np.n_nationkey = n.n_nationkey
    JOIN {database}.{schema}.supplier s ON n.n_nationkey = s.s_nationkey
    GROUP BY r.r_regionkey, r.r_name
),
customer_satisfaction AS (
    SELECT
        l.l_suppkey,
        o.o_custkey,
        COUNT(DISTINCT o.o_orderkey) AS order_count,
        AVG(DATE_DIFF('day', o.o_orderdate, l.l_receiptdate)) AS avg_order_to_receipt,
        AVG(o.o_totalprice) AS avg_order_value,
        COUNT(DISTINCT CASE WHEN l.l_returnflag = 'R' THEN l.l_orderkey END) AS returned_orders,
        COUNT(DISTINCT CASE WHEN l.l_returnflag = 'R' THEN l.l_orderkey END) / NULLIF(COUNT(DISTINCT o.o_orderkey), 0) * 100 AS return_rate,
        AVG(CASE WHEN l.l_returnflag = 'R' THEN l.l_extendedprice * (1 - l.l_discount) ELSE NULL END) AS avg_return_value,
        COUNT(DISTINCT CASE WHEN o.o_orderstatus = 'F' THEN o.o_orderkey END) / NULLIF(COUNT(DISTINCT o.o_orderkey), 0) * 100 AS fulfillment_rate,
        COUNT(DISTINCT CASE WHEN o.o_orderpriority LIKE '1-%' OR o.o_orderpriority LIKE '2-%' THEN o.o_orderkey END) AS high_priority_orders,
        COUNT(DISTINCT CASE WHEN o.o_orderpriority LIKE '1-%' OR o.o_orderpriority LIKE '2-%' THEN o.o_orderkey END) / NULLIF(COUNT(DISTINCT o.o_orderkey), 0) * 100 AS high_priority_percentage
    FROM {database}.{schema}.lineitem l
    JOIN {database}.{schema}.orders o 
        ON l.l_orderkey = o.o_orderkey
    GROUP BY 
        l.l_suppkey, 
        o.o_custkey
),
supplier_customer_analysis AS (
    SELECT
        cs.l_suppkey,
        COUNT(DISTINCT cs.o_custkey) AS unique_customers,
        AVG(cs.order_count) AS avg_orders_per_customer,
        MAX(cs.order_count) AS max_orders_from_customer,
        MIN(cs.order_count) AS min_orders_from_customer,
        STDDEV(cs.order_count) AS order_count_stddev,
        COUNT(DISTINCT CASE WHEN cs.order_count > 5 THEN cs.o_custkey ELSE NULL END) AS loyal_customers,
        COUNT(DISTINCT CASE WHEN cs.order_count > 5 THEN cs.o_custkey ELSE NULL END) / NULLIF(COUNT(DISTINCT cs.o_custkey), 0) * 100 AS loyal_customer_percentage,
        AVG(cs.return_rate) AS avg_return_rate,
        MAX(cs.return_rate) AS max_return_rate,
        AVG(cs.avg_order_value) AS avg_customer_order_value,
        MAX(cs.avg_order_value) AS max_customer_order_value,
        MIN(cs.avg_order_value) AS min_customer_order_value,
        COUNT(DISTINCT CASE WHEN cs.high_priority_percentage > 50 THEN cs.o_custkey ELSE NULL END) AS high_priority_customers,
        COUNT(DISTINCT CASE WHEN cs.high_priority_percentage > 50 THEN cs.o_custkey ELSE NULL END) / NULLIF(COUNT(DISTINCT cs.o_orderkey), 0) * 100 AS high_priority_customer_percentage
    FROM customer_satisfaction cs
    GROUP BY cs.l_suppkey
),
supplier_risk_scores AS (
    SELECT
            sdm.s_suppkey,
            sdm.s_name,
            sdm.s_acctbal,
            sdm.total_orders,
            sdm.total_revenue,
            sdm.total_quantity,
            sdm.late_deliveries / NULLIF(sdm.total_orders, 0) * 100 AS late_delivery_pct,
            sdm.severely_late_deliveries / NULLIF(sdm.total_orders, 0) * 100 AS severely_late_pct,
            sdm.on_time_deliveries / NULLIF(sdm.total_orders, 0) * 100 AS on_time_delivery_pct,
            sdm.avg_delivery_delay,
            sdm.median_delivery_delay,
            sdm.p90_delivery_delay,
            sdm.revenue_volatility,
            sdm.revenue_volatility / NULLIF(sdm.total_revenue / sdm.total_orders, 0) AS normalized_volatility,
            sdm.active_days,
            sdm.unique_parts_shipped,
            sdm.avg_discount_rate,
            sdm.max_discount_offered,
            sca.unique_customers,
            sca.loyal_customer_percentage,
            sca.avg_return_rate,
            -- Delivery Risk Score
            (sdm.late_deliveries / NULLIF(sdm.total_orders, 0) * 40) +
            (sdm.severely_late_deliveries / NULLIF(sdm.total_orders, 0) * 60) +
            (CASE WHEN sdm.avg_delivery_delay > 0 THEN LN(sdm.avg_delivery_delay + 1) * 10 ELSE 0 END) +
            (CASE WHEN sdm.p90_delivery_delay > 10 THEN LN(sdm.p90_delivery_delay) * 5 ELSE 0 END) AS delivery_risk_score,
            -- Financial Risk Score
            (sdm.revenue_volatility / NULLIF(sdm.total_revenue / sdm.total_orders, 0) * 20) +
            (CASE WHEN sdm.s_acctbal < 0 THEN ABS(sdm.s_acctbal) / 1000 * 5 ELSE 0 END) +
            (CASE WHEN sdm.total_orders < 10 THEN 20 ELSE 0 END) +
            (CASE WHEN sdm.active_days < 365 THEN (365 - sdm.active_days) / 3.65 ELSE 0 END) +
            (CASE WHEN stf.months_since_last_activity IS NULL OR stf.months_since_last_activity > 6 
            THEN 30 ELSE stf.months_since_last_activity * 5 END) AS financial_risk_score,
            -- Diversification Risk Score
            (CASE WHEN sdm.unique_parts_shipped < 5 THEN (5 - sdm.unique_parts_shipped) * 10 ELSE 0 END) +
            (CASE WHEN sca.unique_customers < 5 THEN (5 - sca.unique_customers) * 10 ELSE 0 END) +
            (CASE WHEN sca.loyal_customer_percentage < 30 THEN (30 - sca.loyal_customer_percentage) ELSE 0 END) 
            AS diversification_risk_score,
            -- Quality Risk Score
            (sca.avg_return_rate * 5) +
            (CASE WHEN sca.max_return_rate > 30 THEN (sca.max_return_rate - 30) * 2 ELSE 0 END) AS quality_risk_score
        FROM supplier_delivery_metrics sdm
        JOIN supplier_customer_analysis sca ON sdm.s_suppkey = sca.l_suppkey
        LEFT JOIN (
            SELECT
                l_suppkey,
                MIN(months_since_last_activity) AS months_since_last_activity
            FROM supplier_transaction_frequency
            WHERE months_since_last_activity IS NOT NULL
            GROUP BY l_suppkey
        ) stf ON sdm.s_suppkey = stf.l_suppkey
),
supplier_seasonality_quarterly_agg AS (
    SELECT
        ssq.l_suppkey,
        MAX(CASE WHEN ssq.quantity_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_quantity_quarter,
        MAX(CASE WHEN ssq.revenue_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_revenue_quarter,
        AVG(CASE WHEN ssq.yoy_quantity_growth IS NOT NULL THEN ABS(ssq.yoy_quantity_growth) ELSE NULL END) AS avg_quantity_volatility,
        AVG(CASE WHEN ssq.yoy_revenue_growth IS NOT NULL THEN ABS(ssq.yoy_revenue_growth) ELSE NULL END) AS avg_revenue_volatility,
        MAX(ssq.yoy_revenue_growth) AS max_revenue_growth,
        MIN(ssq.yoy_revenue_growth) AS min_revenue_growth,
        AVG(ssq.unique_parts_in_quarter) AS avg_unique_parts_quarterly,
        AVG(ssq.active_months_in_quarter) AS avg_active_months_quarterly,
        AVG(ssq.avg_quantity_per_order) AS avg_quarterly_order_quantity,
        AVG(ssq.avg_revenue_per_order) AS avg_quarterly_order_revenue
    FROM supplier_seasonality_quarterly ssq
    GROUP BY ssq.l_suppkey
),
supplier_seasonality_monthly_agg AS (
    SELECT
        ssm.l_suppkey,
        MAX(CASE WHEN ssm.quantity_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_quantity_month,
        MAX(CASE WHEN ssm.revenue_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_revenue_month,
        AVG(CASE WHEN ssm.yoy_quantity_growth_monthly IS NOT NULL THEN ABS(ssm.yoy_quantity_growth_monthly) ELSE NULL END) AS avg_quantity_volatility_monthly,
        AVG(CASE WHEN ssm.yoy_revenue_growth_monthly IS NOT NULL THEN ABS(ssm.yoy_revenue_growth_monthly) ELSE NULL END) AS avg_revenue_volatility_monthly,
        MAX(ssm.yoy_revenue_growth_monthly) AS max_revenue_growth_monthly,
        MIN(ssm.yoy_revenue_growth_monthly) AS min_revenue_growth_monthly
    FROM supplier_seasonality_monthly ssm
    GROUP BY ssm.l_suppkey
)
SELECT
    srs.s_suppkey,
    srs.s_name,
    srs.s_acctbal,
    srs.total_orders,
    srs.total_revenue,
    srs.late_delivery_pct,
    srs.severely_late_pct,
    srs.avg_delivery_delay,
    srs.p90_delivery_delay,
    srs.revenue_volatility,
    srs.unique_parts_shipped,
    srs.avg_discount_rate,
    srs.unique_customers,
    srs.loyal_customer_percentage,
    srs.avg_return_rate,
    srs.delivery_risk_score,
    srs.financial_risk_score,
    srs.diversification_risk_score,
    srs.quality_risk_score,
    (srs.delivery_risk_score * 0.3 + srs.financial_risk_score * 0.3 + srs.diversification_risk_score * 0.2 + srs.quality_risk_score * 0.2) AS overall_risk_score,
    ssqa.peak_quantity_quarter,
    ssqa.peak_revenue_quarter,
    ssqa.avg_quantity_volatility AS quarterly_quantity_volatility,
    ssqa.avg_revenue_volatility AS quarterly_revenue_volatility,
    ssqa.max_revenue_growth AS max_quarterly_revenue_growth,
    ssqa.min_revenue_growth AS min_quarterly_revenue_growth,
    ssqa.avg_unique_parts_quarterly,
    ssqa.avg_active_months_quarterly,
    ssqa.avg_quarterly_order_quantity,
    ssqa.avg_quarterly_order_revenue,
    ssma.peak_quantity_month,
    ssma.peak_revenue_month,
    ssma.avg_quantity_volatility_monthly AS monthly_quantity_volatility,
    ssma.avg_revenue_volatility_monthly AS monthly_revenue_volatility,
    ssma.max_revenue_growth_monthly AS max_monthly_revenue_growth,
    ssma.min_revenue_growth_monthly AS min_monthly_revenue_growth
FROM supplier_risk_scores srs
LEFT JOIN supplier_seasonality_quarterly_agg ssqa ON srs.s_suppkey = ssqa.l_suppkey
LEFT JOIN supplier_seasonality_monthly_agg ssma ON srs.s_suppkey = ssma.l_suppkey
ORDER BY overall_risk_score DESC LIMIT 1000;