from dotenv import load_dotenv

import os

load_dotenv()

database = os.getenv("DATABASE")
schema = os.getenv("SCHEMA")

queries = [
    
    ("Query-1", f"""
    SELECT 
        SUM(L_EXTENDEDPRICE) AS sum
    FROM {database}.{schema}.lineitem;
    """),

    ("Query-2", f"""
    SELECT 
    COUNT(*) AS count_of_line_items,
    SUM(CAST(JSON_EXTRACT(l.data, '$.l_extendedprice') AS FLOAT)) AS sum,
    AVG(CAST(JSON_EXTRACT(l.data, '$.l_discount') AS FLOAT)) AS avg,
    MIN(CAST(JSON_EXTRACT(l.data, '$.l_shipdate') AS DATE)) AS min,
    MAX(CAST(JSON_EXTRACT(l.data, '$.l_receiptdate') AS DATE)) AS max
    FROM {database}.{schema}.jlineitem l
    """),

    ("Query-3", f"""
    SELECT 
        l_orderkey, 
        l_linenumber, 
        l_shipdate, 
        l_extendedprice, 
        LEAD(l_extendedprice) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS next_line_price,
        LAG(l_shipdate) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS prev_ship_date,
        FIRST_VALUE(l_extendedprice) OVER (PARTITION BY l_orderkey ORDER BY l_linenumber) AS first_line_price
    FROM {database}.{schema}.lineitem
    ORDER BY l_orderkey, l_linenumber LIMIT 1000;
    """),
    
    ("Query-4", f"""
     
     WITH base_table AS (
        SELECT 
            STRFTIME(CAST(JSON_EXTRACT(li.data, '$.l_shipdate') AS DATE), '%Y-%m') AS ship_year_month,
            JSON_EXTRACT(li.data, '$.l_shipmode') AS L_SHIPMODE,
            JSON_EXTRACT(ord.data, '$.o_orderpriority') AS order_priority,
            COUNT(*) AS count_of_line_items,
            SUM(CAST(JSON_EXTRACT(li.data, '$.l_extendedprice') AS FLOAT)) AS sum,
            AVG(CAST(JSON_EXTRACT(li.data, '$.l_discount') AS FLOAT)) AS avg
        FROM {database}.{schema}.jlineitem li
        LEFT JOIN {database}.{schema}.jorders ord 
            ON CAST(JSON_EXTRACT(li.data, '$.l_orderkey') AS INT) = CAST(JSON_EXTRACT(ord.data, '$.o_orderkey') AS INT)
        GROUP BY ship_year_month, L_SHIPMODE, order_priority
    )
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
        ROW_NUMBER() OVER (PARTITION BY L_SHIPMODE ORDER BY avg) AS row_number_by_ship_mode
    FROM base_table 
    LIMIT 1000;

    """),

    ("Query-5", f"""
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
        """),

    ("Query-6", f"""
    WITH combined_comments AS (
        SELECT 
            STRFTIME(o.o_orderdate, '%Y - %B') AS order_month,
            LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
        FROM {database}.{schema}.orders o

        UNION ALL

        SELECT 
            STRFTIME(o.o_orderdate, '%Y - %B') AS order_month,
            LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
        FROM {database}.{schema}.lineitem l
        JOIN {database}.{schema}.orders o 
        ON l.l_orderkey = o.o_orderkey
    ),
    tokenized_words AS (
        SELECT 
            cc.order_month,
            word
        FROM combined_comments cc,
            UNNEST(STRING_SPLIT(cc.cleaned_comment, ' ')) AS word(word)
    ),
    word_counts AS (
        SELECT 
            order_month,
            word,
            COUNT(*) AS word_count,
            RANK() OVER (PARTITION BY order_month ORDER BY COUNT(*) DESC) AS rank
        FROM tokenized_words
        WHERE word NOT IN ('the', 'is', 'and', 'or', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at')
        GROUP BY order_month, word
    )
    SELECT order_month, word, word_count
    FROM word_counts
    WHERE rank <= 5  
    ORDER BY order_month, word_count DESC LIMIT 1000;
    """),
    
    ("Query-7", f"""
    WITH customer_sales AS (
    SELECT 
        strftime(CAST(JSON_EXTRACT(jo.data, '$.o_orderdate') AS DATE), '%Y - %B') AS order_month,
        JSON_EXTRACT(jc.data, '$.c_name') AS c_name,
        SUM(CAST(JSON_EXTRACT(jo.data, '$.o_totalprice') AS FLOAT)) AS total_spent,
        SUM(CAST(JSON_EXTRACT(jl.data, '$.l_quantity') AS FLOAT)) AS total_quantity,
        RANK() OVER (PARTITION BY strftime(CAST(JSON_EXTRACT(jo.data, '$.o_orderdate') AS DATE), '%Y - %B')
                    ORDER BY SUM(CAST(JSON_EXTRACT(jo.data, '$.o_totalprice') AS FLOAT)) DESC) AS price_rank,
        RANK() OVER (PARTITION BY strftime(CAST(JSON_EXTRACT(jo.data, '$.o_orderdate') AS DATE), '%Y - %B')
                    ORDER BY SUM(CAST(JSON_EXTRACT(jl.data, '$.l_quantity') AS FLOAT)) DESC) AS quantity_rank
    FROM {database}.{schema}.jorders jo
    JOIN {database}.{schema}.jlineitem jl 
        ON CAST(JSON_EXTRACT(jo.data, '$.o_orderkey') AS INT) = CAST(JSON_EXTRACT(jl.data, '$.l_orderkey') AS INT)
    JOIN {database}.{schema}.jcustomer jc 
        ON CAST(JSON_EXTRACT(jo.data, '$.o_custkey') AS INT) = CAST(JSON_EXTRACT(jc.data, '$.c_custkey') AS INT)
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
                SUM(CAST(value AS INTEGER)) AS number_sum 
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
        
    """),
    
    ("Query-8", f"""
        WITH order_comments AS (
        SELECT 
            c.c_custkey,
            c.c_name,
            LOWER(TRIM(REGEXP_REPLACE(o.o_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
            CASE 
                WHEN LENGTH(o.o_comment) > 100 THEN 'LONG_COMMENT'
                ELSE 'SHORT_COMMENT'
            END AS comment_type
        FROM {database}.{schema}.orders o
        JOIN {database}.{schema}.customer c ON o.o_custkey = c.c_custkey
        ),
        lineitem_comments AS (
            SELECT 
                c.c_custkey,
                c.c_name,
                LOWER(TRIM(REGEXP_REPLACE(l.l_comment, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
                CASE 
                    WHEN LENGTH(l.l_comment) > 100 THEN 'LONG_COMMENT'
                    ELSE 'SHORT_COMMENT'
                END AS comment_type
            FROM {database}.{schema}.lineitem l
            JOIN {database}.{schema}.orders o ON l.l_orderkey = o.o_orderkey
            JOIN {database}.{schema}.customer c ON o.o_custkey = c.c_custkey
        ),
        combined_comments AS (
            SELECT * FROM order_comments
            UNION ALL
            SELECT * FROM lineitem_comments
        ),
        comment_counts AS (
            SELECT 
                c_custkey,
                COUNT(*) AS total_comments
            FROM combined_comments
            GROUP BY c_custkey
        ),
        filtered_comments AS (
            SELECT 
                cc.c_custkey,
                cc.c_name,
                cc.cleaned_comment,
                cc.comment_type,
                COALESCE(ccc.total_comments, 0) AS total_comments
            FROM combined_comments cc
            LEFT JOIN comment_counts ccc ON cc.c_custkey = ccc.c_custkey
            WHERE cc.cleaned_comment LIKE '%final%' 
        ),
        ranked_comments AS (
            SELECT 
                c_custkey,
                c_name,
                cleaned_comment,
                comment_type,
                total_comments,
                ROW_NUMBER() OVER (PARTITION BY c_custkey ORDER BY LENGTH(cleaned_comment) DESC) AS comment_rank
            FROM filtered_comments
        )
        SELECT 
            rc.c_custkey, 
            rc.c_name, 
            STRING_AGG(rc.cleaned_comment || ' (' || rc.comment_type || ')', ' | ') AS customer_comments,
            MAX(rc.total_comments) AS total_comments_per_customer
        FROM ranked_comments rc
        WHERE rc.comment_rank <= 5 
        GROUP BY rc.c_custkey, rc.c_name
        ORDER BY total_comments_per_customer DESC LIMIT 1000;
    """),
        ("Query-9", f"""
            WITH customer_orders AS (
            SELECT 
                c.c_custkey,
                c.c_name,
                o.o_orderdate,
                SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue,
                COUNT(*) AS order_count,
                ROW_NUMBER() OVER (PARTITION BY c.c_custkey ORDER BY o.o_orderdate ASC) AS order_rank
            FROM {database}.{schema}.customer c
            JOIN {database}.{schema}.orders o ON c.c_custkey = o.o_custkey
            JOIN {database}.{schema}.lineitem l ON o.o_orderkey = l.l_orderkey
            WHERE o.o_orderdate >= CURRENT_DATE - INTERVAL '30 years'
            AND l.l_shipdate > o.o_orderdate 
            GROUP BY c.c_custkey, c.c_name, o.o_orderdate
        ),
        cumulative_revenue AS (
            SELECT 
                c_custkey,
                c_name,
                order_rank,
                o_orderdate,
                total_revenue,
                SUM(total_revenue) OVER (PARTITION BY c_custkey ORDER BY order_rank ASC) AS cumulative_revenue 
            FROM customer_orders
        ),
        monthly_analysis AS (
            SELECT 
                c_custkey,
                c_name,
                DATE_TRUNC('month', o_orderdate) AS order_month,
                COUNT(*) AS monthly_orders,
                SUM(total_revenue) AS monthly_revenue
            FROM cumulative_revenue
            GROUP BY c_custkey, c_name, DATE_TRUNC('month', o_orderdate)
        )
        SELECT 
            m.c_custkey,
            m.c_name,
            STRING_AGG(
                'Month: ' || STRFTIME(order_month, '%Y-%m') ||
                ', Orders: ' || monthly_orders || 
                ', Revenue: ' || FORMAT(monthly_revenue::VARCHAR, '999,999.99'),
                ' | ' ORDER BY order_month
            ) AS monthly_summary,
            MAX(cumulative_revenue) AS lifetime_revenue 
        FROM monthly_analysis m
        JOIN cumulative_revenue c ON m.c_custkey = c.c_custkey
        GROUP BY m.c_custkey, m.c_name
        ORDER BY lifetime_revenue DESC LIMIT 1000;
    """
        ),
    ("Query-10", f"""
        WITH customer_orders AS (
        SELECT 
            c.c_custkey,
            c.c_name,
            o.o_orderdate,
            COUNT(*) AS total_orders,
            SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue,
            SUM(CASE WHEN l.l_shipdate <= o.o_orderdate + INTERVAL '30' DAY THEN 1 ELSE 0 END) AS shipped_orders 
        FROM {database}.{schema}.customer c
        JOIN {database}.{schema}.orders o ON c.c_custkey = o.o_custkey
        JOIN {database}.{schema}.lineitem l ON o.o_orderkey = l.l_orderkey
        WHERE o.o_orderdate >= CURRENT_DATE - INTERVAL '30' YEAR 
        GROUP BY c.c_custkey, c.c_name, o.o_orderdate
    ),
    customer_metrics AS (
        SELECT 
            c_custkey,
            c_name,
            SUM(total_orders) AS total_orders_per_customer,
            SUM(total_revenue) AS total_revenue_per_customer,
            SUM(shipped_orders) AS total_shipped_orders_per_customer,
            AVG(total_revenue / NULLIF(total_orders, 0)) AS avg_revenue_per_order 
        FROM customer_orders
        GROUP BY c_custkey, c_name
    ),
    customer_ratios AS (
        SELECT 
            c_custkey,
            c_name,
            total_orders_per_customer,
            total_revenue_per_customer,
            total_shipped_orders_per_customer,
            avg_revenue_per_order,
            CAST(total_shipped_orders_per_customer AS FLOAT) / NULLIF(total_orders_per_customer, 0) AS shipped_ratio 
        FROM customer_metrics
    )
    SELECT 
        c_custkey,
        c_name,
        total_orders_per_customer,
        total_revenue_per_customer,
        avg_revenue_per_order,
        shipped_ratio * 100 AS shipped_percentage 
    FROM customer_ratios
    WHERE shipped_ratio > 0.5 
    ORDER BY avg_revenue_per_order DESC LIMIT 1000;
    """),
    ("Query-11", f"""
                SELECT 
        CAST(JSON_EXTRACT(jo.data, '$.o_orderkey') AS INT) AS orderkey, 
        CAST(JSON_EXTRACT(jo.data, '$.o_orderdate') AS DATE) AS orderdate, 
        CAST(JSON_EXTRACT(jo.data, '$.o_totalprice') AS DECIMAL) AS totalprice, 
        lineitems.total_revenue, 
        lineitems.avg_discount
    FROM (
        SELECT 
            CAST(JSON_EXTRACT(jl.data, '$.l_orderkey') AS INT) AS orderkey, 
            SUM(CAST(JSON_EXTRACT(jl.data, '$.l_extendedprice') AS DECIMAL) * 
                (1 - CAST(JSON_EXTRACT(jl.data, '$.l_discount') AS DECIMAL))) AS total_revenue,
            AVG(CAST(JSON_EXTRACT(jl.data, '$.l_discount') AS DECIMAL)) AS avg_discount
        FROM {database}.{schema}.jlineitem jl
        GROUP BY CAST(JSON_EXTRACT(jl.data, '$.l_orderkey') AS INT)
    ) AS lineitems
    JOIN {database}.{schema}.jorders jo
        ON lineitems.orderkey = CAST(JSON_EXTRACT(jo.data, '$.o_orderkey') AS INT)
    WHERE lineitems.total_revenue > 50000
    AND lineitems.avg_discount < 0.05
    ORDER BY lineitems.total_revenue DESC 
    LIMIT 1000;
    """),
    ("Query-F", f"""
    -- Step 1: Analyze Supplier Delivery Performance
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

-- Step 2: Calculate Supplier Transaction Frequency Patterns
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

-- Step 3: Calculate Seasonal Ordering Patterns (Quarterly)
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

-- Step 4: Calculate Seasonal Ordering Patterns (Monthly)
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

-- Step 5: Calculate YoY Growth and Seasonality Scores (Quarterly)
supplier_seasonality_quarterly AS (
    SELECT
        l_suppkey,
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

-- Step 6: Calculate YoY Growth and Seasonality Scores (Monthly)
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

-- Step 7: Analyze Parts Supply Chain Diversification
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

-- Step 8: Analyze Part Categories and Their Supply Chain Characteristics
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

-- Step 9: Geographic Performance Analysis (Nation Level)
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

-- Step 10: Geographic Performance Analysis (Region Level)
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

-- Step 11: Customer Satisfaction Metrics via Order Lifecycle Analysis
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

-- Step 12: Supplier Customer Diversity and Loyalty Analysis
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
        COUNT(DISTINCT CASE WHEN cs.high_priority_percentage > 50 THEN cs.o_custkey ELSE NULL END) / NULLIF(COUNT(DISTINCT cs.o_custkey), 0) * 100 AS high_priority_customer_percentage
    FROM customer_satisfaction cs
    GROUP BY cs.l_suppkey
),

-- Step 13: Calculate Risk Scores for Each Supplier
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

-- Step 14: Aggregate Seasonal Insights per Supplier (Quarterly)
supplier_seasonality_quarterly_agg AS (
    SELECT
        ssq.l_suppkey,
        MAX(CASE WHEN ssq.quantity_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_quantity_quarter,
        MAX(CASE WHEN ssq.revenue_quarter_rank = 1 THEN ssq.quarter ELSE NULL END) AS peak_revenue_quarter,
        AVG(CASE WHEN ssq.yoy_quantity_growth IS NOT NULL THEN ABS(ssq.yoy_quantity_growth) ELSE NULL END) AS avg_quantity_volatility,
        AVG(CASE WHEN ssq.yoy_revenue_growth IS NOT NULL THEN ABS(ssq.yoy_revenue_growth) ELSE NULL END) AS avg_revenue_volatility,
        MAX(ssq.yoy_revenue_growth) AS max_revenue_growth,
        MIN(ssq.yoy_revenue_growth) AS min_revenue_growth,
        AVG(ssq.unique_parts_in_quarter) AS avg_unique_parts_per_quarter,
        MAX(ssq.active_months_in_quarter) AS max_active_months_in_quarter,
        AVG(ssq.avg_quantity_per_order) AS overall_avg_quantity_per_order,
        AVG(ssq.avg_revenue_per_order) AS overall_avg_revenue_per_order,
        STDDEV(ssq.quarterly_revenue) / NULLIF(AVG(ssq.quarterly_revenue), 0) * 100 AS revenue_coefficient_of_variation
    FROM supplier_seasonality_quarterly ssq
    GROUP BY ssq.l_suppkey
),

-- Step 15: Aggregate Seasonal Insights per Supplier (Monthly)
supplier_seasonality_monthly_agg AS (
    SELECT
        ssm.l_suppkey,
        MAX(CASE WHEN ssm.quantity_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_quantity_month,
        MAX(CASE WHEN ssm.revenue_month_rank = 1 THEN ssm.month ELSE NULL END) AS peak_revenue_month,
        AVG(CASE 
            WHEN ssm.yoy_quantity_growth_monthly IS NOT NULL 
            THEN ABS(CAST(ssm.yoy_quantity_growth_monthly AS FLOAT)) 
            ELSE NULL 
        END) AS avg_monthly_quantity_volatility,
        AVG(CASE 
            WHEN ssm.yoy_revenue_growth_monthly IS NOT NULL 
            THEN ABS(CAST(ssm.yoy_revenue_growth_monthly AS FLOAT)) 
            ELSE NULL 
        END) AS avg_monthly_revenue_volatility,
        MAX(ssm.yoy_revenue_growth_monthly) AS max_monthly_revenue_growth,
        MIN(ssm.yoy_revenue_growth_monthly) AS min_monthly_revenue_growth,
        STDDEV(CAST(ssm.monthly_revenue AS FLOAT)) / 
        NULLIF(AVG(CAST(ssm.monthly_revenue AS FLOAT)), 0) * 100 AS monthly_revenue_coefficient_of_variation
    FROM supplier_seasonality_monthly ssm
    GROUP BY ssm.l_suppkey
),

-- Step 16: Parts Supplied Analysis
supplier_parts_profile AS (
    SELECT
        ps.ps_suppkey,
        COUNT(DISTINCT ps.ps_partkey) AS unique_parts_supplied,
        COUNT(DISTINCT p.p_mfgr) AS manufacturer_count,
        COUNT(DISTINCT p.p_brand) AS brand_count,
        COUNT(DISTINCT SUBSTR(p.p_type, 1, INSTR(p.p_type, ' ')-1)) AS part_category_count,
        AVG(CAST(ps.ps_supplycost AS FLOAT)) AS avg_supply_cost,
        MIN(CAST(ps.ps_supplycost AS FLOAT)) AS min_supply_cost,
        MAX(CAST(ps.ps_supplycost AS FLOAT)) AS max_supply_cost,
        STDDEV(CAST(ps.ps_supplycost AS FLOAT)) AS supply_cost_stddev,
        SUM(ps.ps_availqty) AS total_availability,
        MIN(ps.ps_availqty) AS min_availability,
        MAX(ps.ps_availqty) AS max_availability,
        AVG(CAST(ps.ps_availqty AS FLOAT)) AS avg_availability,
        STDDEV(CAST(ps.ps_availqty AS FLOAT)) AS availability_stddev,
        AVG(CAST(ps.ps_availqty AS FLOAT) * CAST(p.p_retailprice AS FLOAT)) AS avg_inventory_value,
        SUM(ps.ps_availqty * CAST(p.p_retailprice AS FLOAT)) AS total_inventory_value,
        -- Parts category diversity
        COUNT(DISTINCT SUBSTR(p.p_type, 1, INSTR(p.p_type, ' ')-1)) AS category_diversity,
        -- Average supply chain redundancy for parts supplied
        AVG(CASE 
            WHEN psd.supplier_count IS NOT NULL 
            THEN CAST(psd.supplier_count AS FLOAT) 
            ELSE 1.0 
        END) AS avg_supply_chain_redundancy,
        -- Premium category percentage
        SUM(CASE 
            WHEN CAST(p.p_retailprice AS FLOAT) > 1000 THEN 1 
            ELSE 0 
        END) * 100.0 / NULLIF(COUNT(*), 0) AS premium_part_percentage,
        -- Inventory turnover potential
        CAST(SUM(ps.ps_availqty) AS FLOAT) / NULLIF(
            (SELECT SUM(l_quantity) 
            FROM {database}.{schema}.lineitem 
            WHERE l_suppkey = ps.ps_suppkey), 0
        ) AS inventory_turnover_ratio
    FROM {database}.{schema}.partsupp ps
    JOIN {database}.{schema}.part p 
        ON ps.ps_partkey = p.p_partkey
    LEFT JOIN part_supplier_diversity psd 
        ON p.p_partkey = psd.p_partkey
    GROUP BY ps.ps_suppkey
),

-- Step 17: Text Analysis of Supplier Comments
supplier_comment_analysis AS (
    SELECT
        s_suppkey,
        s_comment,
        LENGTH(s_comment) AS comment_length,
        -- Positive mentions using string operations
        (
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quality', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'reliable', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'good', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'excellent', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'best', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quick', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'fast', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'prompt', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'timely', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'superior', ''))
        ) / CAST(LENGTH('quality') AS FLOAT) AS positive_mentions,
        
        -- Negative mentions using string operations
        (
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'delay', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'issue', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'problem', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'complaint', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'late', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'bad', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'slow', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'poor', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'dissatisfied', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'disappointed', ''))
        ) / CAST(LENGTH('delay') AS FLOAT) AS negative_mentions,
        
        -- Sentiment analysis based on mention counts
        CASE
            WHEN (
                (LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quality', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'reliable', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'good', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'excellent', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'best', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quick', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'fast', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'prompt', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'timely', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'superior', ''))) >
                (LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'delay', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'issue', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'problem', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'complaint', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'late', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'bad', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'slow', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'poor', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'dissatisfied', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'disappointed', '')))
            ) THEN 'Positive'
            WHEN (
                (LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quality', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'reliable', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'good', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'excellent', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'best', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'quick', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'fast', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'prompt', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'timely', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'superior', ''))) <
                (LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'delay', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'issue', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'problem', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'complaint', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'late', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'bad', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'slow', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'poor', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'dissatisfied', '')) +
                LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'disappointed', '')))
            ) THEN 'Negative'
            ELSE 'Neutral'
        END AS sentiment,
        
        -- Financial mentions
        (
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'price', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'cost', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'discount', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'rate', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'value', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'expense', ''))
        ) / CAST(LENGTH('price') AS FLOAT) AS financial_mentions,
        
        -- Logistics mentions
        (
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'ship', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'deliver', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'transport', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'carry', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'move', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'logistics', ''))
        ) / CAST(LENGTH('ship') AS FLOAT) AS logistics_mentions,
        
        -- Product mentions
        (
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'part', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'item', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'product', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'stock', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'component', '')) +
            LENGTH(LOWER(s_comment)) - LENGTH(REPLACE(LOWER(s_comment), 'material', ''))
        ) / CAST(LENGTH('part') AS FLOAT) AS product_mentions
    FROM {database}.{schema}.supplier
),
-- Step 18: Final Supplier Performance Report
final_supplier_report AS (
        SELECT
            sdm.s_suppkey,
            sdm.s_name,
            sdm.s_nationkey,
            CAST(sdm.s_acctbal AS FLOAT) AS s_acctbal,
            sdm.s_address,
            sdm.s_phone,
            CAST(sdm.total_orders AS INTEGER) AS total_orders,
            CAST(sdm.avg_delivery_delay AS FLOAT) AS avg_delivery_delay,
            CAST(sdm.median_delivery_delay AS FLOAT) AS median_delivery_delay,
            CAST(sdm.p90_delivery_delay AS FLOAT) AS p90_delivery_delay,
            CAST(sdm.late_deliveries AS INTEGER) AS late_deliveries,
            CAST(sdm.on_time_deliveries AS INTEGER) AS on_time_deliveries,
            CAST(sdm.severely_late_deliveries AS INTEGER) AS severely_late_deliveries,
            CAST(sdm.total_revenue AS FLOAT) AS total_revenue,
            CAST(sdm.total_tax AS FLOAT) AS total_tax,
            CAST(sdm.total_quantity AS INTEGER) AS total_quantity,
            CAST(sdm.avg_discount_rate AS FLOAT) AS avg_discount_rate,
            CAST(sdm.max_discount_offered AS FLOAT) AS max_discount_offered,
            CAST(sdm.revenue_volatility AS FLOAT) AS revenue_volatility,
            CAST(sdm.revenue_variance AS FLOAT) AS revenue_variance,
            sdm.first_shipment_date,
            sdm.last_shipment_date,
            CAST(sdm.active_days AS INTEGER) AS active_days,
            CAST(sdm.unique_parts_shipped AS INTEGER) AS unique_parts_shipped,
            CAST(stf.transactions_per_month AS INTEGER) AS transactions_per_month,
            CAST(stf.quantity_per_month AS INTEGER) AS quantity_per_month,
            CAST(stf.revenue_per_month AS FLOAT) AS revenue_per_month,
            CAST(stf.prev_month_transactions AS INTEGER) AS prev_month_transactions,
            CAST(stf.prev_month_quantity AS INTEGER) AS prev_month_quantity,
            CAST(stf.prev_month_revenue AS FLOAT) AS prev_month_revenue,
            CAST(stf.months_since_last_activity AS INTEGER) AS months_since_last_activity,
            CAST(ssq_agg.peak_quantity_quarter AS INTEGER) AS peak_quantity_quarter,
            CAST(ssq_agg.peak_revenue_quarter AS INTEGER) AS peak_revenue_quarter,
            CAST(ssq_agg.avg_quantity_volatility AS FLOAT) AS avg_quantity_volatility,
            CAST(ssq_agg.avg_revenue_volatility AS FLOAT) AS avg_revenue_volatility,
            CAST(ssq_agg.max_revenue_growth AS FLOAT) AS max_revenue_growth,
            CAST(ssq_agg.min_revenue_growth AS FLOAT) AS min_revenue_growth,
            CAST(ssq_agg.avg_unique_parts_per_quarter AS FLOAT) AS avg_unique_parts_per_quarter,
            CAST(ssq_agg.max_active_months_in_quarter AS INTEGER) AS max_active_months_in_quarter,
            CAST(ssq_agg.overall_avg_quantity_per_order AS FLOAT) AS overall_avg_quantity_per_order,
            CAST(ssq_agg.overall_avg_revenue_per_order AS FLOAT) AS overall_avg_revenue_per_order,
            CAST(ssq_agg.revenue_coefficient_of_variation AS FLOAT) AS revenue_coefficient_of_variation,
            CAST(ssm_agg.peak_quantity_month AS INTEGER) AS peak_quantity_month,
            CAST(ssm_agg.peak_revenue_month AS INTEGER) AS peak_revenue_month,
            CAST(ssm_agg.avg_monthly_quantity_volatility AS FLOAT) AS avg_monthly_quantity_volatility,
            CAST(ssm_agg.avg_monthly_revenue_volatility AS FLOAT) AS avg_monthly_revenue_volatility,
            CAST(ssm_agg.max_monthly_revenue_growth AS FLOAT) AS max_monthly_revenue_growth,
            CAST(ssm_agg.min_monthly_revenue_growth AS FLOAT) AS min_monthly_revenue_growth,
            CAST(ssm_agg.monthly_revenue_coefficient_of_variation AS FLOAT) AS monthly_revenue_coefficient_of_variation,
            CAST(srs.delivery_risk_score AS FLOAT) AS delivery_risk_score,
            CAST(srs.financial_risk_score AS FLOAT) AS financial_risk_score,
            CAST(srs.diversification_risk_score AS FLOAT) AS diversification_risk_score,
            CAST(srs.quality_risk_score AS FLOAT) AS quality_risk_score,
            CAST(spp.unique_parts_supplied AS INTEGER) AS unique_parts_supplied,
            CAST(spp.manufacturer_count AS INTEGER) AS manufacturer_count,
            CAST(spp.brand_count AS INTEGER) AS brand_count,
            CAST(spp.part_category_count AS INTEGER) AS part_category_count,
            CAST(spp.avg_supply_cost AS FLOAT) AS avg_supply_cost,
            CAST(spp.min_supply_cost AS FLOAT) AS min_supply_cost,
            CAST(spp.max_supply_cost AS FLOAT) AS max_supply_cost,
            CAST(spp.supply_cost_stddev AS FLOAT) AS supply_cost_stddev,
            CAST(spp.total_availability AS INTEGER) AS total_availability,
            CAST(spp.min_availability AS INTEGER) AS min_availability,
            CAST(spp.max_availability AS INTEGER) AS max_availability,
            CAST(spp.avg_availability AS FLOAT) AS avg_availability,
            CAST(spp.availability_stddev AS FLOAT) AS availability_stddev,
            CAST(spp.avg_inventory_value AS FLOAT) AS avg_inventory_value,
            CAST(spp.total_inventory_value AS FLOAT) AS total_inventory_value,
            CAST(spp.category_diversity AS INTEGER) AS category_diversity,
            CAST(spp.avg_supply_chain_redundancy AS FLOAT) AS avg_supply_chain_redundancy,
            CAST(spp.premium_part_percentage AS FLOAT) AS premium_part_percentage,
            CAST(spp.inventory_turnover_ratio AS FLOAT) AS inventory_turnover_ratio,sca.sentiment,
            CAST(sca.comment_length AS INTEGER) AS comment_length,
            CAST(sca.positive_mentions AS FLOAT) AS positive_mentions,
            CAST(sca.negative_mentions AS FLOAT) AS negative_mentions,
            CAST(sca.financial_mentions AS FLOAT) AS financial_mentions,
            CAST(sca.logistics_mentions AS FLOAT) AS logistics_mentions,
            CAST(sca.product_mentions AS FLOAT) AS product_mentions
        FROM supplier_delivery_metrics sdm
        LEFT JOIN supplier_transaction_frequency stf 
            ON sdm.s_suppkey = stf.l_suppkey
        LEFT JOIN supplier_seasonality_quarterly_agg ssq_agg 
            ON sdm.s_suppkey = ssq_agg.l_suppkey
        LEFT JOIN supplier_seasonality_monthly_agg ssm_agg 
            ON sdm.s_suppkey = ssm_agg.l_suppkey
        LEFT JOIN supplier_risk_scores srs 
            ON sdm.s_suppkey = srs.s_suppkey
        LEFT JOIN supplier_parts_profile spp 
            ON sdm.s_suppkey = spp.ps_suppkey
        LEFT JOIN supplier_comment_analysis sca 
            ON sdm.s_suppkey = sca.s_suppkey
)

SELECT * FROM final_supplier_report limit 1000;

    """)
    
    

]
