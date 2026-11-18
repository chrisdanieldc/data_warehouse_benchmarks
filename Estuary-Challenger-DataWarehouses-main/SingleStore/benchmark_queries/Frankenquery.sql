-- Query F
-- Description: Analyzes supplier delivery performance, transaction frequency, and seasonal ordering patterns using advanced window and statistical functions
-- Difficulty: Hard

-- Step 1: Analyze Supplier Delivery Performance
WITH supplier_delivery_metrics AS (
    SELECT
        s.S_SUPPKEY,
        s.S_NAME,
        s.S_NATIONKEY,
        s.S_ACCTBAL,
        s.S_ADDRESS,
        s.S_PHONE,
        COUNT(DISTINCT l.L_ORDERKEY) AS total_ORDERS,
        AVG(DATEDIFF(l.L_RECEIPTDATE, l.L_COMMITDATE)) AS avg_delivery_delay,
        AVG(DATEDIFF(l.L_RECEIPTDATE, l.L_COMMITDATE)) AS median_delivery_delay,
        AVG(DATEDIFF(l.L_RECEIPTDATE, l.L_COMMITDATE)) + 1.28 * STDDEV(DATEDIFF(l.L_RECEIPTDATE, l.L_COMMITDATE)) AS p90_delivery_delay,
        SUM(CASE WHEN l.L_RECEIPTDATE > l.L_COMMITDATE THEN 1 ELSE 0 END) AS late_deliveries,
        SUM(CASE WHEN l.L_RECEIPTDATE <= l.L_COMMITDATE THEN 1 ELSE 0 END) AS on_time_deliveries,
        SUM(CASE WHEN DATEDIFF(l.L_RECEIPTDATE, l.L_COMMITDATE) > 7 THEN 1 ELSE 0 END) AS severely_late_deliveries,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT) * l.L_TAX) AS total_tax,
        SUM(l.L_QUANTITY) AS total_quantity,
        AVG(l.L_DISCOUNT) AS avg_discount_rate,
        MAX(l.L_DISCOUNT) AS max_discount_offered,
        STDDEV(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS revenue_volatility,
        VARIANCE(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS revenue_variance,
        MIN(l.L_SHIPDATE) AS first_shipment_date,
        MAX(l.L_SHIPDATE) AS last_shipment_date,
        DATEDIFF(MAX(l.L_SHIPDATE), MIN(l.L_SHIPDATE)) AS active_days,
        COUNT(DISTINCT l.L_PARTKEY) AS unique_PARTs_shipped
    FROM SUPPLIER s
    JOIN LINEITEM l ON s.S_SUPPKEY = l.L_SUPPKEY
    GROUP BY s.S_SUPPKEY, s.S_NAME, s.S_NATIONKEY, s.S_ACCTBAL, s.S_ADDRESS, s.S_PHONE
),

-- Step 2: Calculate Supplier Transaction Frequency Patterns
supplier_transaction_frequency AS (
    SELECT
        L_SUPPKEY,
        DATE_FORMAT(L_SHIPDATE, '%Y-%m-01') AS ship_month,
        COUNT(*) AS transactions_per_month,
        SUM(L_QUANTITY) AS quantity_per_month,
        SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) AS revenue_per_month,
        LAG(COUNT(*)) OVER (PARTITION BY L_SUPPKEY ORDER BY DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')) AS prev_month_transactions,
        LAG(SUM(L_QUANTITY)) OVER (PARTITION BY L_SUPPKEY ORDER BY DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')) AS prev_month_quantity,
        LAG(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT))) OVER (PARTITION BY L_SUPPKEY ORDER BY DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')) AS prev_month_revenue,
        TIMESTAMPDIFF(MONTH,
            LAG(DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')) OVER (PARTITION BY L_SUPPKEY ORDER BY DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')),
            DATE_FORMAT(L_SHIPDATE, '%Y-%m-01')
        ) AS months_since_last_activity
    FROM LINEITEM
    GROUP BY L_SUPPKEY, ship_month
),

-- Step 3: Calculate Seasonal Ordering Patterns (Quarterly)
seasonal_patterns_quarterly AS (
    SELECT
        l.L_SUPPKEY,
        QUARTER(o.O_ORDERDATE) AS quarter,
        YEAR(o.O_ORDERDATE) AS year,
        COUNT(DISTINCT o.O_ORDERKEY) AS quarterly_ORDERS,
        COUNT(DISTINCT MONTH(o.O_ORDERDATE)) AS active_months_in_quarter,
        SUM(l.L_QUANTITY) AS quarterly_quantity,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS quarterly_revenue,
        AVG(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS avg_order_value_in_quarter,
        COUNT(DISTINCT l.L_PARTKEY) AS unique_PARTs_in_quarter,
        LAG(SUM(l.L_QUANTITY)) OVER (PARTITION BY l.L_SUPPKEY, QUARTER(o.O_ORDERDATE) ORDER BY YEAR(o.O_ORDERDATE)) AS prev_year_quarterly_quantity,
        LAG(SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT))) OVER (PARTITION BY l.L_SUPPKEY, QUARTER(o.O_ORDERDATE) ORDER BY YEAR(o.O_ORDERDATE)) AS prev_year_quarterly_revenue
    FROM LINEITEM l
    JOIN ORDERS o ON l.L_ORDERKEY = o.O_ORDERKEY
    GROUP BY l.L_SUPPKEY, quarter, year
),

-- Step 4: Calculate Seasonal Ordering Patterns (Monthly)
seasonal_patterns_monthly AS (
    SELECT
        l.L_SUPPKEY,
        MONTH(o.O_ORDERDATE) AS month,
        YEAR(o.O_ORDERDATE) AS year,
        COUNT(DISTINCT o.O_ORDERKEY) AS monthly_ORDERS,
        SUM(l.L_QUANTITY) AS monthly_quantity,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS monthly_revenue,
        LAG(SUM(l.L_QUANTITY)) OVER (PARTITION BY l.L_SUPPKEY, MONTH(o.O_ORDERDATE) ORDER BY YEAR(o.O_ORDERDATE)) AS prev_year_monthly_quantity,
        LAG(SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT))) OVER (PARTITION BY l.L_SUPPKEY, MONTH(o.O_ORDERDATE) ORDER BY YEAR(o.O_ORDERDATE)) AS prev_year_monthly_revenue
    FROM LINEITEM l
    JOIN ORDERS o ON l.L_ORDERKEY = o.O_ORDERKEY
    GROUP BY l.L_SUPPKEY, month, year
),

-- Step 5: Calculate YoY Growth and Seasonality Scores (Quarterly)
supplier_seasonality_quarterly AS (
    SELECT
        L_SUPPKEY,
        quarter,
        year,
        quarterly_quantity,
        quarterly_revenue,
        unique_PARTs_in_quarter,
        active_months_in_quarter,
        CASE
            WHEN prev_year_quarterly_quantity > 0 THEN (quarterly_quantity - prev_year_quarterly_quantity) / prev_year_quarterly_quantity * 100
            ELSE NULL
        END AS yoy_quantity_growth,
        CASE
            WHEN prev_year_quarterly_revenue > 0 THEN (quarterly_revenue - prev_year_quarterly_revenue) / prev_year_quarterly_revenue * 100
            ELSE NULL
        END AS yoy_revenue_growth,
        DENSE_RANK() OVER (PARTITION BY L_SUPPKEY ORDER BY quarterly_quantity DESC) AS quantity_quarter_rank,
        DENSE_RANK() OVER (PARTITION BY L_SUPPKEY ORDER BY quarterly_revenue DESC) AS revenue_quarter_rank,
        quarterly_quantity / NULLIF(quarterly_ORDERS, 0) AS avg_quantity_per_order,
        quarterly_revenue / NULLIF(quarterly_ORDERS, 0) AS avg_revenue_per_order
    FROM seasonal_patterns_quarterly
),

-- Step 6: Calculate YoY Growth and Seasonality Scores (Monthly)
supplier_seasonality_monthly AS (
    SELECT
        L_SUPPKEY,
        month,
        year,
        monthly_quantity,
        monthly_revenue,
        CASE
            WHEN prev_year_monthly_quantity > 0 THEN (monthly_quantity - prev_year_monthly_quantity) / prev_year_monthly_quantity * 100
            ELSE NULL
        END AS yoy_quantity_growth_monthly,
        CASE
            WHEN prev_year_monthly_revenue > 0 THEN (monthly_revenue - prev_year_monthly_revenue) / prev_year_monthly_revenue * 100
            ELSE NULL
        END AS yoy_revenue_growth_monthly,
        DENSE_RANK() OVER (PARTITION BY L_SUPPKEY ORDER BY monthly_quantity DESC) AS quantity_month_rank,
        DENSE_RANK() OVER (PARTITION BY L_SUPPKEY ORDER BY monthly_revenue DESC) AS revenue_month_rank
    FROM seasonal_patterns_monthly
),

-- Step 7: Analyze PARTs Supply Chain Diversification
PART_supplier_diversity AS (
    SELECT
        p.P_PARTKEY,
        p.P_NAME,
        p.P_MFGR,
        p.P_BRAND,
        p.P_TYPE,
        p.P_SIZE,
        p.P_CONTAINER,
        p.P_RETAILPRICE,
        COUNT(DISTINCT ps.PS_SUPPKEY) AS supplier_count,
        MAX(ps.PS_SUPPLYCOST) / NULLIF(MIN(ps.PS_SUPPLYCOST), 0) AS cost_ratio,
        MAX(ps.PS_SUPPLYCOST) - MIN(ps.PS_SUPPLYCOST) AS cost_spread,
        STDDEV(ps.PS_SUPPLYCOST) AS cost_volatility,
        AVG(ps.PS_SUPPLYCOST) AS avg_cost,
        MIN(ps.PS_SUPPLYCOST) AS min_cost,
        MAX(ps.PS_SUPPLYCOST) AS max_cost,
        AVG(ps.PS_AVAILQTY) AS avg_availability,
        SUM(ps.PS_AVAILQTY) AS total_availability,
        MIN(ps.PS_AVAILQTY) AS min_availability,
        MAX(ps.PS_AVAILQTY) AS max_availability,
        VARIANCE(ps.PS_AVAILQTY) AS availability_variance
    FROM PART p
    JOIN PARTSUPP ps ON p.P_PARTKEY = ps.PS_PARTKEY
    GROUP BY p.P_PARTKEY, p.P_NAME, p.P_MFGR, p.P_BRAND, p.P_TYPE, p.P_SIZE, p.P_CONTAINER, p.P_RETAILPRICE
    HAVING COUNT(DISTINCT ps.PS_SUPPKEY) > 1
),

-- Step 8: Analyze PART Categories and Their Supply Chain Characteristics
PART_category_analysis AS (
    SELECT
        SUBSTRING_INDEX(p.P_TYPE, ' ', 1) AS PART_category,
        COUNT(DISTINCT p.P_PARTKEY) AS category_PART_count,
        AVG(psd.supplier_count) AS avg_suppliers_per_PART,
        MIN(psd.supplier_count) AS min_suppliers_per_PART,
        MAX(psd.supplier_count) AS max_suppliers_per_PART,
        AVG(psd.cost_ratio) AS avg_cost_ratio,
        AVG(psd.cost_volatility) AS avg_cost_volatility,
        SUM(p.P_RETAILPRICE * psd.total_availability) AS category_inventory_value,
        COUNT(DISTINCT ps.PS_SUPPKEY) AS unique_suppliers_in_category
    FROM PART p
    JOIN PART_supplier_diversity psd ON p.P_PARTKEY = psd.P_PARTKEY
    JOIN PARTSUPP ps ON p.P_PARTKEY = ps.PS_PARTKEY
    GROUP BY PART_category
),

-- Step 9: Geographic Performance Analysis (Nation Level)
nation_performance AS (
    SELECT
        n.N_NATIONKEY,
        n.N_NAME AS nation,
        n.N_REGIONKEY,
        COUNT(DISTINCT s.S_SUPPKEY) AS supplier_count,
        AVG(sdm.avg_delivery_delay) AS nation_avg_delay,
        AVG(sdm.median_delivery_delay) AS nation_median_delay,
        AVG(sdm.p90_delivery_delay) AS nation_p90_delay,
        SUM(sdm.total_revenue) AS nation_revenue,
        SUM(sdm.total_quantity) AS nation_quantity,
        SUM(sdm.late_deliveries) / NULLIF(SUM(sdm.total_ORDERS), 0) * 100 AS nation_late_delivery_pct,
        SUM(sdm.severely_late_deliveries) / NULLIF(SUM(sdm.total_ORDERS), 0) * 100 AS nation_severely_late_pct,
        AVG(sdm.revenue_volatility) AS nation_avg_rev_volatility,
        SUM(sdm.unique_PARTs_shipped) AS nation_unique_PARTs,
        COUNT(DISTINCT l.L_PARTKEY) AS nation_distinct_PARTs
    FROM SUPPLIER s
    JOIN supplier_delivery_metrics sdm ON s.S_SUPPKEY = sdm.S_SUPPKEY
    JOIN NATION n ON s.S_NATIONKEY = n.N_NATIONKEY
    JOIN LINEITEM l ON s.S_SUPPKEY = l.L_SUPPKEY
    GROUP BY n.N_NATIONKEY, n.N_NAME, n.N_REGIONKEY
),

-- Step 10: Geographic Performance Analysis (Region Level)
region_performance AS (
    SELECT
        r.R_REGIONKEY,
        r.R_NAME AS region,
        COUNT(DISTINCT s.S_SUPPKEY) AS supplier_count,
        COUNT(DISTINCT n.N_NATIONKEY) AS nations_count,
        AVG(np.nation_avg_delay) AS region_avg_delay,
        AVG(np.nation_median_delay) AS region_median_delay,
        SUM(np.nation_revenue) AS region_revenue,
        SUM(np.nation_quantity) AS region_quantity,
        SUM(np.nation_unique_PARTs) AS region_unique_PARTs,
        AVG(np.nation_late_delivery_pct) AS region_late_delivery_pct,
        AVG(np.nation_severely_late_pct) AS region_severely_late_pct,
        AVG(np.nation_avg_rev_volatility) AS region_avg_rev_volatility,
        MAX(np.nation_revenue) / NULLIF(MIN(np.nation_revenue), 0) AS nation_revenue_disparity,
        STDDEV(np.nation_late_delivery_pct) AS late_delivery_pct_stddev
    FROM REGION r
    JOIN nation_performance np ON r.R_REGIONKEY = np.N_REGIONKEY
    JOIN NATION n ON np.N_NATIONKEY = n.N_NATIONKEY
    JOIN SUPPLIER s ON n.N_NATIONKEY = s.S_NATIONKEY
    GROUP BY r.R_REGIONKEY, r.R_NAME
),

-- Step 11: Customer Satisfaction Metrics via Order Lifecycle Analysis
customer_satisfaction AS (
    SELECT
        l.L_SUPPKEY,
        o.O_CUSTKEY,
        COUNT(DISTINCT o.O_ORDERKEY) AS order_count,
        AVG(DATEDIFF(l.L_RECEIPTDATE, o.O_ORDERDATE)) AS avg_order_to_receipt,
        AVG(o.O_TOTALPRICE) AS avg_order_value,
        COUNT(DISTINCT CASE WHEN l.L_RETURNFLAG = 'R' THEN l.L_ORDERKEY END) AS returned_ORDERS,
        COUNT(DISTINCT CASE WHEN l.L_RETURNFLAG = 'R' THEN l.L_ORDERKEY END) / NULLIF(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS return_rate,
        AVG(CASE WHEN l.L_RETURNFLAG = 'R' THEN l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT) ELSE NULL END) AS avg_return_value,
        COUNT(DISTINCT CASE WHEN o.O_ORDERSTATUS = 'F' THEN o.O_ORDERKEY END) / NULLIF(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS fulfillment_rate,
        COUNT(DISTINCT CASE WHEN o.O_ORDERPRIORITY LIKE '1-%' OR o.O_ORDERPRIORITY LIKE '2-%' THEN o.O_ORDERKEY END) AS high_priority_ORDERS,
        COUNT(DISTINCT CASE WHEN o.O_ORDERPRIORITY LIKE '1-%' OR o.O_ORDERPRIORITY LIKE '2-%' THEN o.O_ORDERKEY END) / NULLIF(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS high_priority_percentage
    FROM LINEITEM l
    JOIN ORDERS o ON l.L_ORDERKEY = o.O_ORDERKEY
    GROUP BY l.L_SUPPKEY, o.O_CUSTKEY
),

-- Step 12: Supplier Customer Diversity and Loyalty Analysis
supplier_customer_analysis AS (
    SELECT
        cs.L_SUPPKEY,
        COUNT(DISTINCT cs.O_CUSTKEY) AS unique_customers,
        AVG(cs.order_count) AS avg_ORDERS_per_customer,
        MAX(cs.order_count) AS max_ORDERS_from_customer,
        MIN(cs.order_count) AS min_ORDERS_from_customer,
        STDDEV(cs.order_count) AS order_count_stddev,
        COUNT(DISTINCT CASE WHEN cs.order_count > 5 THEN cs.O_CUSTKEY ELSE NULL END) AS loyal_customers,
        COUNT(DISTINCT CASE WHEN cs.order_count > 5 THEN cs.O_CUSTKEY ELSE NULL END) / NULLIF(COUNT(DISTINCT cs.O_CUSTKEY), 0) * 100 AS loyal_customer_percentage,
        AVG(cs.return_rate) AS avg_return_rate,
        MAX(cs.return_rate) AS max_return_rate,
        AVG(cs.avg_order_value) AS avg_customer_order_value,
        MAX(cs.avg_order_value) AS max_customer_order_value,
        MIN(cs.avg_order_value) AS min_customer_order_value,
        COUNT(DISTINCT CASE WHEN cs.high_priority_percentage > 50 THEN cs.O_CUSTKEY ELSE NULL END) AS high_priority_customers,
        COUNT(DISTINCT CASE WHEN cs.high_priority_percentage > 50 THEN cs.O_CUSTKEY ELSE NULL END) / NULLIF(COUNT(DISTINCT cs.O_CUSTKEY), 0) * 100 AS high_priority_customer_percentage
    FROM customer_satisfaction cs
    GROUP BY cs.L_SUPPKEY
),

-- Step 13: Calculate Risk Scores for Each Supplier
supplier_risk_scores AS (
    SELECT
        sdm.S_SUPPKEY,
        sdm.S_NAME,
        sdm.S_ACCTBAL,
        sdm.total_ORDERS,
        sdm.total_revenue,
        sdm.total_quantity,
        sdm.late_deliveries / NULLIF(sdm.total_ORDERS, 0) * 100 AS late_delivery_pct,
        sdm.severely_late_deliveries / NULLIF(sdm.total_ORDERS, 0) * 100 AS severely_late_pct,
        sdm.on_time_deliveries / NULLIF(sdm.total_ORDERS, 0) * 100 AS on_time_delivery_pct,
        sdm.avg_delivery_delay,
        sdm.median_delivery_delay,
        sdm.p90_delivery_delay,
        sdm.revenue_volatility,
        sdm.revenue_volatility / NULLIF(sdm.total_revenue / sdm.total_ORDERS, 0) AS normalized_volatility,
        sdm.active_days,
        sdm.unique_PARTs_shipped,
        sdm.avg_discount_rate,
        sdm.max_discount_offered,
        sca.unique_customers,
        sca.loyal_customer_percentage,
        sca.avg_return_rate,

        -- Risk Components:

        -- Delivery Risk Score (higher is worse): 0-100
        (sdm.late_deliveries / NULLIF(sdm.total_ORDERS, 0) * 40) +
        (sdm.severely_late_deliveries / NULLIF(sdm.total_ORDERS, 0) * 60) +
        (CASE WHEN sdm.avg_delivery_delay > 0 THEN LOG10(sdm.avg_delivery_delay + 1) * 10 ELSE 0 END) +
        (CASE WHEN sdm.p90_delivery_delay > 10 THEN LOG10(sdm.p90_delivery_delay) * 5 ELSE 0 END) AS delivery_risk_score,

        -- Financial Risk Score (higher is worse): 0-100
        (sdm.revenue_volatility / NULLIF(sdm.total_revenue / sdm.total_ORDERS, 0) * 20) +
        (CASE WHEN sdm.S_ACCTBAL < 0 THEN ABS(sdm.S_ACCTBAL) / 1000 * 5 ELSE 0 END) +
        (CASE WHEN sdm.total_ORDERS < 10 THEN 20 ELSE 0 END) +
        (CASE WHEN sdm.active_days < 365 THEN (365 - sdm.active_days) / 3.65 ELSE 0 END) +
        (CASE WHEN stf.months_since_last_activity IS NULL OR stf.months_since_last_activity > 6 THEN 30 ELSE stf.months_since_last_activity * 5 END) AS financial_risk_score,

        -- Diversification Risk Score (higher is worse): 0-100
        (CASE WHEN sdm.unique_PARTs_shipped < 5 THEN (5 - sdm.unique_PARTs_shipped) * 10 ELSE 0 END) +
        (CASE WHEN sca.unique_customers < 5 THEN (5 - sca.unique_customers) * 10 ELSE 0 END) +
        (CASE WHEN sca.loyal_customer_percentage < 30 THEN (30 - sca.loyal_customer_percentage) ELSE 0 END) AS diversification_risk_score,

        -- Quality Risk Score (higher is worse): 0-100
        (sca.avg_return_rate * 5) +
        (CASE WHEN sca.max_return_rate > 30 THEN (sca.max_return_rate - 30) * 2 ELSE 0 END) AS quality_risk_score
    FROM supplier_delivery_metrics sdm
    JOIN supplier_customer_analysis sca ON sdm.S_SUPPKEY = sca.L_SUPPKEY
    LEFT JOIN (
        SELECT
            L_SUPPKEY,
            MIN(months_since_last_activity) AS months_since_last_activity
        FROM supplier_transaction_frequency
        WHERE months_since_last_activity IS NOT NULL
        GROUP BY L_SUPPKEY
    ) stf ON sdm.S_SUPPKEY = stf.L_SUPPKEY
),

-- Step 14: Aggregate Seasonal Insights per Supplier (Quarterly)
supplier_seasonality_quarterly_agg AS (
    SELECT
        ssq.L_SUPPKEY,
        MAX(CASE WHEN ssq.quantity_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_quantity_quarter,
        MAX(CASE WHEN ssq.revenue_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_revenue_quarter,
        AVG(CASE WHEN ssq.yoy_quantity_growth IS NOT NULL THEN ABS(ssq.yoy_quantity_growth) ELSE NULL END) AS avg_quantity_volatility,
        AVG(CASE WHEN ssq.yoy_revenue_growth IS NOT NULL THEN ABS(ssq.yoy_revenue_growth) ELSE NULL END) AS avg_revenue_volatility,
        MAX(ssq.yoy_revenue_growth) AS max_revenue_growth,
        MIN(ssq.yoy_revenue_growth) AS min_revenue_growth,
        AVG(ssq.unique_PARTs_in_quarter) AS avg_unique_PARTs_per_quarter,
        MAX(ssq.active_months_in_quarter) AS max_active_months_in_quarter,
        AVG(ssq.avg_quantity_per_order) AS overall_avg_quantity_per_order,
        AVG(ssq.avg_revenue_per_order) AS overall_avg_revenue_per_order,
        STDDEV(ssq.quarterly_revenue) / NULLIF(AVG(ssq.quarterly_revenue), 0) * 100 AS revenue_coefficient_of_variation
    FROM supplier_seasonality_quarterly ssq
    GROUP BY ssq.L_SUPPKEY
),

-- Step 15: Aggregate Seasonal Insights per Supplier (Monthly)
supplier_seasonality_monthly_agg AS (
    SELECT
        ssm.L_SUPPKEY,
        MAX(CASE WHEN ssm.quantity_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_quantity_month,
        MAX(CASE WHEN ssm.revenue_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_revenue_month,
        AVG(CASE WHEN ssm.yoy_quantity_growth_monthly IS NOT NULL THEN ABS(ssm.yoy_quantity_growth_monthly) ELSE NULL END) AS avg_monthly_quantity_volatility,
        AVG(CASE WHEN ssm.yoy_revenue_growth_monthly IS NOT NULL THEN ABS(ssm.yoy_revenue_growth_monthly) ELSE NULL END) AS avg_monthly_revenue_volatility,
        MAX(ssm.yoy_revenue_growth_monthly) AS max_monthly_revenue_growth,
        MIN(ssm.yoy_revenue_growth_monthly) AS min_monthly_revenue_growth,
        STDDEV(ssm.monthly_revenue) / NULLIF(AVG(ssm.monthly_revenue), 0) * 100 AS monthly_revenue_coefficient_of_variation
    FROM supplier_seasonality_monthly ssm
    GROUP BY ssm.L_SUPPKEY
),

-- Step 16: PARTs Supplied Analysis
supplier_PARTs_profile AS (
    SELECT
        ps.PS_SUPPKEY,
        COUNT(DISTINCT ps.PS_PARTKEY) AS unique_PARTs_supplied,
        COUNT(DISTINCT p.P_MFGR) AS manufacturer_count,
        COUNT(DISTINCT p.P_BRAND) AS brand_count,
        COUNT(DISTINCT SUBSTRING_INDEX(p.P_TYPE, ' ', 1)) AS PART_category_count,
        AVG(ps.PS_SUPPLYCOST) AS avg_supply_cost,
        MIN(ps.PS_SUPPLYCOST) AS min_supply_cost,
        MAX(ps.PS_SUPPLYCOST) AS max_supply_cost,
        STDDEV(ps.PS_SUPPLYCOST) AS supply_cost_stddev,
        SUM(ps.PS_AVAILQTY) AS total_availability,
        MIN(ps.PS_AVAILQTY) AS min_availability,
        MAX(ps.PS_AVAILQTY) AS max_availability,
        AVG(ps.PS_AVAILQTY) AS avg_availability,
        STDDEV(ps.PS_AVAILQTY) AS availability_stddev,
        AVG(ps.PS_AVAILQTY * p.P_RETAILPRICE) AS avg_inventory_value,
        SUM(ps.PS_AVAILQTY * p.P_RETAILPRICE) AS total_inventory_value,
        -- PARTs category diversity
        COUNT(DISTINCT SUBSTRING(p.P_TYPE, 1, LOCATE(' ', p.P_TYPE))) AS category_diversity,
        -- Average supply chain redundancy for PARTs supplied
        AVG(CASE WHEN psd.supplier_count IS NOT NULL THEN psd.supplier_count ELSE 1 END) AS avg_supply_chain_redundancy,
        -- Premium category percentage
        SUM(CASE WHEN p.P_RETAILPRICE > 1000 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS premium_PART_percentage,
        -- Inventory turnover potential (based on historic LINEITEM volume)
        SUM(ps.PS_AVAILQTY) / NULLIF((SELECT SUM(L_QUANTITY) FROM LINEITEM WHERE L_SUPPKEY = ps.PS_SUPPKEY), 0) AS inventory_turnover_ratio
    FROM PARTSUPP ps
    JOIN PART p ON ps.PS_PARTKEY = p.P_PARTKEY
    LEFT JOIN PART_supplier_diversity psd ON p.P_PARTKEY = psd.P_PARTKEY
    GROUP BY ps.PS_SUPPKEY
),

-- Step 17: Text Analysis of Supplier Comments
supplier_comment_analysis AS (
    SELECT
        S_SUPPKEY,
        S_COMMENT,
        LENGTH(S_COMMENT) AS comment_length,
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'quality', ''))) / LENGTH('quality') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'reliable', ''))) / LENGTH('reliable') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'good', ''))) / LENGTH('good') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'excellent', ''))) / LENGTH('excellent') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'best', ''))) / LENGTH('best') AS positive_mentions,
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'problem', ''))) / LENGTH('problem') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'complaint', ''))) / LENGTH('complaint') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'late', ''))) / LENGTH('late') AS negative_mentions,
        CASE
            WHEN ((LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'quality', ''))) / LENGTH('quality') +
                 (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'reliable', ''))) / LENGTH('reliable')) >
                 ((LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'delay', ''))) / LENGTH('delay') +
                 (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'issue', ''))) / LENGTH('issue'))
            THEN 'Positive'
            WHEN ((LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'quality', ''))) / LENGTH('quality') +
                 (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'reliable', ''))) / LENGTH('reliable')) <
                 ((LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'delay', ''))) / LENGTH('delay') +
                 (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'issue', ''))) / LENGTH('issue'))
            THEN 'Negative'
            ELSE 'Neutral'
        END AS sentiment,
        -- Additional text analytics
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'price', ''))) / LENGTH('price') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'cost', ''))) / LENGTH('cost') AS financial_mentions,
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'ship', ''))) / LENGTH('ship') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'deliver', ''))) / LENGTH('deliver') AS logistics_mentions,
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'part', ''))) / LENGTH('part') +
        (LENGTH(S_COMMENT) - LENGTH(REPLACE(LOWER(S_COMMENT), 'item', ''))) / LENGTH('item') AS product_mentions
    FROM SUPPLIER
),

-- Step 18: Final Supplier Performance Report
final_supplier_report AS (
    SELECT
        sdm.S_SUPPKEY,
        sdm.S_NAME,
        sdm.S_NATIONKEY,
        sdm.S_ACCTBAL,
        sdm.S_ADDRESS,
        sdm.S_PHONE,
        sdm.total_ORDERS,
        sdm.avg_delivery_delay,
        sdm.median_delivery_delay,
        sdm.p90_delivery_delay,
        sdm.late_deliveries,
        sdm.on_time_deliveries,
        sdm.severely_late_deliveries,
        sdm.total_revenue,
        sdm.total_tax,
        sdm.total_quantity,
        sdm.avg_discount_rate,
        sdm.max_discount_offered,
        sdm.revenue_volatility,
        sdm.revenue_variance,
        sdm.first_shipment_date,
        sdm.last_shipment_date,
        sdm.active_days,
        sdm.unique_PARTs_shipped,
        stf.transactions_per_month,
        stf.quantity_per_month,
        stf.revenue_per_month,
        stf.prev_month_transactions,
        stf.prev_month_quantity,
        stf.prev_month_revenue,
        stf.months_since_last_activity,
        ssq_agg.peak_quantity_quarter,
        ssq_agg.peak_revenue_quarter,
        ssq_agg.avg_quantity_volatility,
        ssq_agg.avg_revenue_volatility,
        ssq_agg.max_revenue_growth,
        ssq_agg.min_revenue_growth,
        ssq_agg.avg_unique_PARTs_per_quarter,
        ssq_agg.max_active_months_in_quarter,
        ssq_agg.overall_avg_quantity_per_order,
        ssq_agg.overall_avg_revenue_per_order,
        ssq_agg.revenue_coefficient_of_variation,
        ssm_agg.peak_quantity_month,
        ssm_agg.peak_revenue_month,
        ssm_agg.avg_monthly_quantity_volatility,
        ssm_agg.avg_monthly_revenue_volatility,
        ssm_agg.max_monthly_revenue_growth,
        ssm_agg.min_monthly_revenue_growth,
        ssm_agg.monthly_revenue_coefficient_of_variation,
        srs.delivery_risk_score,
        srs.financial_risk_score,
        srs.diversification_risk_score,
        srs.quality_risk_score,
        spp.unique_PARTs_supplied,
        spp.manufacturer_count,
        spp.brand_count,
        spp.PART_category_count,
        spp.avg_supply_cost,
        spp.min_supply_cost,
        spp.max_supply_cost,
        spp.supply_cost_stddev,
        spp.total_availability,
        spp.min_availability,
        spp.max_availability,
        spp.avg_availability,
        spp.availability_stddev,
        spp.avg_inventory_value,
        spp.total_inventory_value,
        spp.category_diversity,
        spp.avg_supply_chain_redundancy,
        spp.premium_PART_percentage,
        spp.inventory_turnover_ratio,
        sca.sentiment,
        sca.comment_length,
        sca.positive_mentions,
        sca.negative_mentions,
        sca.financial_mentions,
        sca.logistics_mentions,
        sca.product_mentions
    FROM supplier_delivery_metrics sdm
    LEFT JOIN supplier_transaction_frequency stf ON sdm.S_SUPPKEY = stf.L_SUPPKEY
    LEFT JOIN supplier_seasonality_quarterly_agg ssq_agg ON sdm.S_SUPPKEY = ssq_agg.L_SUPPKEY
    LEFT JOIN supplier_seasonality_monthly_agg ssm_agg ON sdm.S_SUPPKEY = ssm_agg.L_SUPPKEY
    LEFT JOIN supplier_risk_scores srs ON sdm.S_SUPPKEY = srs.S_SUPPKEY
    LEFT JOIN supplier_PARTs_profile spp ON sdm.S_SUPPKEY = spp.PS_SUPPKEY
    LEFT JOIN supplier_comment_analysis sca ON sdm.S_SUPPKEY = sca.S_SUPPKEY
)

SELECT * FROM final_supplier_report
LIMIT 1000;