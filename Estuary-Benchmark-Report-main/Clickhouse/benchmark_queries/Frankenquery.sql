-- Query F
-- Description: Comprehensive supply chain analysis combining supplier delivery performance, transaction frequency, seasonality, part diversification, geographic performance, customer satisfaction, and calculating supplier risk scores
-- Difficulty: Very Hard

 --step-1 Analyze Supplier Delivery Performance
WITH supplier_delivery_metrics AS (
SELECT
    s.S_SUPPKEY,
    s.S_NAME,
    s.S_NATIONKEY,
    s.S_ACCTBAL,
    s.S_ADDRESS,
    s.S_PHONE,
    COUNT(DISTINCT l.L_ORDERKEY) AS total_orders,
    avg(dateDiff('day', l.L_COMMITDATE, l.L_RECEIPTDATE)) AS avg_delivery_delay,
    median(dateDiff('day', l.L_COMMITDATE, l.L_RECEIPTDATE)) AS median_delivery_delay,
    quantile(0.9)(dateDiff('day', l.L_COMMITDATE, l.L_RECEIPTDATE)) AS p90_delivery_delay,
    SUM(if(L_RECEIPTDATE > L_COMMITDATE, 1, 0)) AS late_deliveries,
    SUM(if(L_RECEIPTDATE <= L_COMMITDATE, 1, 0)) AS on_time_deliveries,
    SUM(if(dateDiff('day', L_COMMITDATE, L_RECEIPTDATE) > 7, 1, 0)) AS severely_late_deliveries,
    SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) AS total_revenue,
    SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * L_TAX) AS total_tax,
    SUM(L_QUANTITY) AS total_quantity,
    avg(L_DISCOUNT) AS avg_discount_rate,
    max(L_DISCOUNT) AS max_discount_offered,
    stddevPop(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) AS revenue_volatility,
    varPop(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) AS revenue_variance,
    min(L_SHIPDATE) AS first_shipment_date,
    max(L_SHIPDATE) AS last_shipment_date,
    dateDiff('day', min(L_SHIPDATE), max(L_SHIPDATE)) AS active_days,
    COUNT(DISTINCT L_PARTKEY) AS unique_parts_shipped
FROM snowflake_sample_data.tpch_sf1000.SUPPLIER s
JOIN snowflake_sample_data.tpch_sf1000.LINEITEM l ON s.S_SUPPKEY = l.L_SUPPKEY
GROUP BY s.S_SUPPKEY, s.S_NAME, s.S_NATIONKEY, s.S_ACCTBAL, s.S_ADDRESS, s.S_PHONE
),

-- Step 2: Calculate Supplier Transaction Frequency Patterns
    supplier_transaction_frequency AS (
        SELECT
        l.L_SUPPKEY,
        toStartOfMonth(l.L_SHIPDATE) AS ship_month,
        COUNT(*) AS transactions_per_month,
        SUM(l.L_QUANTITY) AS quantity_per_month,
        SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS revenue_per_month,
        lagInFrame(COUNT(*)) OVER (
            PARTITION BY l.L_SUPPKEY
            ORDER BY toStartOfMonth(l.L_SHIPDATE)
        ) AS prev_month_transactions,
        lagInFrame(SUM(l.L_QUANTITY)) OVER (
            PARTITION BY l.L_SUPPKEY
            ORDER BY toStartOfMonth(l.L_SHIPDATE)
        ) AS prev_month_quantity,
        lagInFrame(SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT))) OVER (
            PARTITION BY l.L_SUPPKEY
            ORDER BY toStartOfMonth(l.L_SHIPDATE)
        ) AS prev_month_revenue,
        dateDiff(
            'month',
            lagInFrame(toStartOfMonth(l.L_SHIPDATE)) OVER (
                PARTITION BY l.L_SUPPKEY
                ORDER BY toStartOfMonth(l.L_SHIPDATE)
            ),
            toStartOfMonth(l.L_SHIPDATE)
        ) AS months_since_last_activity
        FROM snowflake_sample_data.tpch_sf1000.LINEITEM l
        GROUP BY l.L_SUPPKEY, ship_month
    ),

-- Step 3: Calculate Seasonal Ordering Patterns (Quarterly)
    seasonal_patterns_quarterly AS (
        SELECT
            l.L_SUPPKEY,
            toQuarter(o.O_ORDERDATE) AS quarter,
            toYear(o.O_ORDERDATE) AS year,
            COUNT(DISTINCT o.O_ORDERKEY) AS quarterly_orders,
            COUNT(DISTINCT toMonth(o.O_ORDERDATE)) AS active_months_in_quarter,
            SUM(l.L_QUANTITY) AS quarterly_quantity,
            SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS quarterly_revenue,
            AVG(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS avg_order_value_in_quarter,
            COUNT(DISTINCT l.L_PARTKEY) AS unique_parts_in_quarter,
            lagInFrame(SUM(l.L_QUANTITY)) OVER (
                PARTITION BY l.L_SUPPKEY, toQuarter(o.O_ORDERDATE)
                ORDER BY toYear(o.O_ORDERDATE)
            ) AS prev_year_quarterly_quantity,
            lagInFrame(SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT))) OVER (
                PARTITION BY l.L_SUPPKEY, toQuarter(o.O_ORDERDATE)
                ORDER BY toYear(o.O_ORDERDATE)
            ) AS prev_year_quarterly_revenue
        FROM snowflake_sample_data.tpch_sf1000.LINEITEM l
        JOIN snowflake_sample_data.tpch_sf1000.ORDERS o ON l.L_ORDERKEY = o.O_ORDERKEY
        GROUP BY l.L_SUPPKEY, quarter, year
    ),
    -- Step 4: Monthly Seasonal Patterns Analysis
    seasonal_patterns_monthly AS (
        SELECT
            l.L_SUPPKEY,
            toMonth(o.O_ORDERDATE) AS month,
            toYear(o.O_ORDERDATE) AS year,
            COUNT(DISTINCT o.O_ORDERKEY) AS monthly_orders,
            SUM(l.L_QUANTITY) AS monthly_quantity,
            SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS monthly_revenue,
            lagInFrame(SUM(l.L_QUANTITY)) OVER (
                PARTITION BY l.L_SUPPKEY, toMonth(o.O_ORDERDATE)
                ORDER BY toYear(o.O_ORDERDATE)
            ) AS prev_year_monthly_quantity,
            lagInFrame(SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT))) OVER (
                PARTITION BY l.L_SUPPKEY, toMonth(o.O_ORDERDATE)
                ORDER BY toYear(o.O_ORDERDATE)
            ) AS prev_year_monthly_revenue
        FROM snowflake_sample_data.tpch_sf1000.LINEITEM l
        JOIN snowflake_sample_data.tpch_sf1000.ORDERS o ON l.L_ORDERKEY = o.O_ORDERKEY
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
            unique_parts_in_quarter,
            active_months_in_quarter,
            if(prev_year_quarterly_quantity > 0,
                (quarterly_quantity - prev_year_quarterly_quantity) / prev_year_quarterly_quantity * 100,
                NULL) AS yoy_quantity_growth,
            if(prev_year_quarterly_revenue > 0,
                (quarterly_revenue - prev_year_quarterly_revenue) / prev_year_quarterly_revenue * 100,
                NULL) AS yoy_revenue_growth,
            dense_rank() OVER (
                PARTITION BY L_SUPPKEY
                ORDER BY quarterly_quantity DESC
            ) AS quantity_quarter_rank,
            dense_rank() OVER (
                PARTITION BY L_SUPPKEY
                ORDER BY quarterly_revenue DESC
            ) AS revenue_quarter_rank,
            quarterly_quantity / nullIf(quarterly_orders, 0) AS avg_quantity_per_order,
            quarterly_revenue / nullIf(quarterly_orders, 0) AS avg_revenue_per_order
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
            if(prev_year_monthly_quantity > 0,
                (monthly_quantity - prev_year_monthly_quantity) / prev_year_monthly_quantity * 100,
                NULL) AS yoy_quantity_growth_monthly,
            if(prev_year_monthly_revenue > 0,
                (monthly_revenue - prev_year_monthly_revenue) / prev_year_monthly_revenue * 100,
                NULL) AS yoy_revenue_growth_monthly,
            dense_rank() OVER (
                PARTITION BY L_SUPPKEY
                ORDER BY monthly_quantity DESC
            ) AS quantity_month_rank,
            dense_rank() OVER (
                PARTITION BY L_SUPPKEY
                ORDER BY monthly_revenue DESC
            ) AS revenue_month_rank
        FROM seasonal_patterns_monthly
    ),
    -- Step 7: Analyze Parts Supply Chain Diversification
    part_supplier_diversity AS (
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
            max(ps.PS_SUPPLYCOST) / nullIf(min(ps.PS_SUPPLYCOST), 0) AS cost_ratio,
            max(ps.PS_SUPPLYCOST) - min(ps.PS_SUPPLYCOST) AS cost_spread,
            stddevPop(ps.PS_SUPPLYCOST) AS cost_volatility,
            avg(ps.PS_SUPPLYCOST) AS avg_cost,
            min(ps.PS_SUPPLYCOST) AS min_cost,
            max(ps.PS_SUPPLYCOST) AS max_cost,
            avg(ps.PS_AVAILQTY) AS avg_availability,
            sum(ps.PS_AVAILQTY) AS total_availability,
            min(ps.PS_AVAILQTY) AS min_availability,
            max(ps.PS_AVAILQTY) AS max_availability,
            varPop(ps.PS_AVAILQTY) AS availability_variance
        FROM snowflake_sample_data.tpch_sf1000.PART p
        JOIN snowflake_sample_data.tpch_sf1000.PARTSUPP ps ON p.P_PARTKEY = ps.PS_PARTKEY
        GROUP BY
            p.P_PARTKEY,
            p.P_NAME,
            p.P_MFGR,
            p.P_BRAND,
            p.P_TYPE,
            p.P_SIZE,
            p.P_CONTAINER,
            p.P_RETAILPRICE
        HAVING COUNT(DISTINCT ps.PS_SUPPKEY) > 1
    ),
    -- Step 8: Analyze Part Categories and Their Supply Chain Characteristics
    part_category_analysis AS (
        SELECT
            splitByString(' ', p.P_TYPE)[1] AS part_category,
            COUNT(DISTINCT p.P_PARTKEY) AS category_part_count,
            avg(psd.supplier_count) AS avg_suppliers_per_part,
            min(psd.supplier_count) AS min_suppliers_per_part,
            max(psd.supplier_count) AS max_suppliers_per_part,
            avg(psd.cost_ratio) AS avg_cost_ratio,
            avg(psd.cost_volatility) AS avg_cost_volatility,
            sum(p.P_RETAILPRICE * psd.total_availability) AS category_inventory_value,
            COUNT(DISTINCT ps.PS_SUPPKEY) AS unique_suppliers_in_category
        FROM snowflake_sample_data.tpch_sf1000.PART p
        JOIN part_supplier_diversity psd
            ON p.P_PARTKEY = psd.P_PARTKEY
        JOIN snowflake_sample_data.tpch_sf1000.PARTSUPP ps
            ON p.P_PARTKEY = ps.PS_PARTKEY
        GROUP BY
            part_category
    ),
    -- Step 9: Geographic Performance Analysis (Nation Level)
    nation_performance AS (
        SELECT
            n.N_NATIONKEY,
            n.N_NAME AS nation,
            n.N_REGIONKEY,
            COUNT(DISTINCT s.S_SUPPKEY) AS supplier_count,
            avg(sdm.avg_delivery_delay) AS nation_avg_delay,
            median(sdm.avg_delivery_delay) AS nation_median_delay,
            avg(sdm.p90_delivery_delay) AS nation_p90_delay,
            SUM(sdm.total_revenue) AS nation_revenue,
            SUM(sdm.total_quantity) AS nation_quantity,
            SUM(sdm.late_deliveries) / nullIf(SUM(sdm.total_orders), 0) * 100 AS nation_late_delivery_pct,
            SUM(sdm.severely_late_deliveries) / nullIf(SUM(sdm.total_orders), 0) * 100 AS nation_severely_late_pct,
            avg(sdm.revenue_volatility) AS nation_avg_rev_volatility,
            SUM(sdm.unique_parts_shipped) AS nation_unique_parts,
            COUNT(DISTINCT l.L_PARTKEY) AS nation_distinct_parts
        FROM snowflake_sample_data.tpch_sf1000.SUPPLIER s
        JOIN supplier_delivery_metrics sdm
            ON s.S_SUPPKEY = sdm.s_suppkey
        JOIN snowflake_sample_data.tpch_sf1000.NATION n
            ON s.S_NATIONKEY = n.N_NATIONKEY
        JOIN snowflake_sample_data.tpch_sf1000.LINEITEM l
            ON s.S_SUPPKEY = l.L_SUPPKEY
        GROUP BY
            n.N_NATIONKEY,
            n.N_NAME,
            n.N_REGIONKEY
    ),
    -- Step 10: Geographic Performance Analysis (Region Level)
    region_performance AS (
        SELECT
            r.R_REGIONKEY,
            r.R_NAME AS region,
            COUNT(DISTINCT s.S_SUPPKEY) AS supplier_count,
            COUNT(DISTINCT n.N_NATIONKEY) AS nations_count,
            avg(np.nation_avg_delay) AS region_avg_delay,
            avg(np.nation_median_delay) AS region_median_delay,
            SUM(np.nation_revenue) AS region_revenue,
            SUM(np.nation_quantity) AS region_quantity,
            SUM(np.nation_unique_parts) AS region_unique_parts,
            avg(np.nation_late_delivery_pct) AS region_late_delivery_pct,
            avg(np.nation_severely_late_pct) AS region_severely_late_pct,
            avg(np.nation_avg_rev_volatility) AS region_avg_rev_volatility,
            max(np.nation_revenue) / nullIf(min(np.nation_revenue), 0) AS nation_revenue_disparity,
            stddevPop(np.nation_late_delivery_pct) AS late_delivery_pct_stddev
        FROM snowflake_sample_data.tpch_sf1000.REGION r
        JOIN nation_performance np ON r.R_REGIONKEY = np.N_REGIONKEY
        JOIN snowflake_sample_data.tpch_sf1000.NATION n ON np.N_NATIONKEY = n.N_NATIONKEY
        JOIN snowflake_sample_data.tpch_sf1000.SUPPLIER s ON n.N_NATIONKEY = s.S_NATIONKEY
        GROUP BY r.R_REGIONKEY, r.R_NAME
    ),
    -- Step 11: Customer Satisfaction Metrics via Order Lifecycle Analysis
    customer_satisfaction AS (
        SELECT
            l.L_SUPPKEY,
            o.O_CUSTKEY,
            COUNT(DISTINCT o.O_ORDERKEY) AS order_count,
            avg(dateDiff('day', o.O_ORDERDATE, l.L_RECEIPTDATE)) AS avg_order_to_receipt,
            avg(o.O_TOTALPRICE) AS avg_order_value,
            COUNT(DISTINCT if(l.L_RETURNFLAG = 'R', l.L_ORDERKEY, NULL)) AS returned_orders,
            COUNT(DISTINCT if(l.L_RETURNFLAG = 'R', l.L_ORDERKEY, NULL)) /
                nullIf(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS return_rate,
            avg(if(l.L_RETURNFLAG = 'R',
                l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT),
                NULL)) AS avg_return_value,
            COUNT(DISTINCT if(o.O_ORDERSTATUS = 'F', o.O_ORDERKEY, NULL)) /
                nullIf(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS fulfillment_rate,
            COUNT(DISTINCT if(startsWith(o.O_ORDERPRIORITY, '1-') OR
                startsWith(o.O_ORDERPRIORITY, '2-'), o.O_ORDERKEY, NULL)) AS high_priority_orders,
            COUNT(DISTINCT if(startsWith(o.O_ORDERPRIORITY, '1-') OR
                startsWith(o.O_ORDERPRIORITY, '2-'), o.O_ORDERKEY, NULL)) /
                nullIf(COUNT(DISTINCT o.O_ORDERKEY), 0) * 100 AS high_priority_percentage
        FROM snowflake_sample_data.tpch_sf1000.LINEITEM l
        JOIN snowflake_sample_data.tpch_sf1000.ORDERS o
            ON l.L_ORDERKEY = o.O_ORDERKEY
        GROUP BY
            l.L_SUPPKEY,
            o.O_CUSTKEY
    ),
    -- Step 12: Supplier Customer Diversity and Loyalty Analysis
    supplier_customer_analysis AS (
        SELECT
            cs.L_SUPPKEY,
            COUNT(DISTINCT cs.O_CUSTKEY) AS unique_customers,
            avg(cs.order_count) AS avg_orders_per_customer,
            max(cs.order_count) AS max_orders_from_customer,
            min(cs.order_count) AS min_orders_from_customer,
            stddevPop(cs.order_count) AS order_count_stddev,
            COUNT(DISTINCT if(cs.order_count > 5, cs.O_CUSTKEY, NULL)) AS loyal_customers,
            COUNT(DISTINCT if(cs.order_count > 5, cs.O_CUSTKEY, NULL)) /
                nullIf(COUNT(DISTINCT cs.O_CUSTKEY), 0) * 100 AS loyal_customer_percentage,
            avg(cs.return_rate) AS avg_return_rate,
            max(cs.return_rate) AS max_return_rate,
            avg(cs.avg_order_value) AS avg_customer_order_value,
            max(cs.avg_order_value) AS max_customer_order_value,
            min(cs.avg_order_value) AS min_customer_order_value,
            COUNT(DISTINCT if(cs.high_priority_percentage > 50, cs.O_CUSTKEY, NULL)) AS high_priority_customers,
            COUNT(DISTINCT if(cs.high_priority_percentage > 50, cs.O_CUSTKEY, NULL)) /
                nullIf(COUNT(DISTINCT cs.O_CUSTKEY), 0) * 100 AS high_priority_customer_percentage
        FROM customer_satisfaction cs
        GROUP BY cs.L_SUPPKEY
    ),
    -- Step 13: Calculate Risk Scores for Each Supplier
    supplier_risk_scores AS (
        SELECT
            sdm.S_SUPPKEY,
            sdm.S_NAME,
            sdm.S_ACCTBAL,
            sdm.total_orders,
            sdm.total_revenue,
            sdm.total_quantity,
            sdm.late_deliveries / nullIf(sdm.total_orders, 0) * 100 AS late_delivery_pct,
            sdm.severely_late_deliveries / nullIf(sdm.total_orders, 0) * 100 AS severely_late_pct,
            sdm.on_time_deliveries / nullIf(sdm.total_orders, 0) * 100 AS on_time_delivery_pct,
            sdm.avg_delivery_delay,
            sdm.median_delivery_delay,
            sdm.p90_delivery_delay,
            sdm.revenue_volatility,
            sdm.revenue_volatility / nullIf(sdm.total_revenue / sdm.total_orders, 0) AS normalized_volatility,
            sdm.active_days,
            sdm.unique_parts_shipped,
            sdm.avg_discount_rate,
            sdm.max_discount_offered,
            sca.unique_customers,
            sca.loyal_customer_percentage,
            sca.avg_return_rate,
            -- Risk Score Calculations
            (sdm.late_deliveries / nullIf(sdm.total_orders, 0) * 40) +
            (sdm.severely_late_deliveries / nullIf(sdm.total_orders, 0) * 60) +
            (if(sdm.avg_delivery_delay > 0, log(sdm.avg_delivery_delay + 1) * 10, 0)) +
            (if(sdm.p90_delivery_delay > 10, log(sdm.p90_delivery_delay) * 5, 0)) AS delivery_risk_score,

            (sdm.revenue_volatility / nullIf(sdm.total_revenue / sdm.total_orders, 0) * 20) +
            (if(sdm.S_ACCTBAL < 0, abs(sdm.S_ACCTBAL) / 1000 * 5, 0)) +
            (if(sdm.total_orders < 10, 20, 0)) +
            (if(sdm.active_days < 365, (365 - sdm.active_days) / 3.65, 0)) +
            (if(stf.recent_activity IS NULL OR stf.recent_activity > 6,
                30, stf.recent_activity * 5)) AS financial_risk_score,

            (if(sdm.unique_parts_shipped < 5, (5 - sdm.unique_parts_shipped) * 10, 0)) +
            (if(sca.unique_customers < 5, (5 - sca.unique_customers) * 10, 0)) +
            (if(sca.loyal_customer_percentage < 30, (30 - sca.loyal_customer_percentage), 0))
            AS diversification_risk_score
        FROM supplier_delivery_metrics sdm
        LEFT JOIN supplier_customer_analysis sca ON sdm.S_SUPPKEY = sca.L_SUPPKEY
        LEFT JOIN (
            SELECT
                L_SUPPKEY,
                max(months_since_last_activity) as recent_activity -- Find the max months since last activity per supplier
            FROM supplier_transaction_frequency
            GROUP BY L_SUPPKEY
        ) stf ON sdm.S_SUPPKEY = stf.L_SUPPKEY
    )
SELECT
    S_SUPPKEY,
    S_NAME,
    S_ACCTBAL,
    total_orders,
    total_revenue,
    late_delivery_pct,
    severely_late_pct,
    avg_delivery_delay,
    p90_delivery_delay,
    revenue_volatility,
    unique_customers,
    loyal_customer_percentage,
    avg_return_rate,
    delivery_risk_score,
    financial_risk_score,
    diversification_risk_score,
    delivery_risk_score + financial_risk_score + diversification_risk_score AS total_risk_score
FROM supplier_risk_scores
ORDER BY total_risk_score DESC
LIMIT 1000;