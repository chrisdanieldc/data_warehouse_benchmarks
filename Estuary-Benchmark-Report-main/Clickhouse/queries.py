from dotenv import load_dotenv
import os

query_settings = """
SET max_memory_usage = 12000000000 -- 10 GB
SET max_bytes_before_external_group_by = 10000000000 -- 5 GB
SET join_use_nulls = 1
SET join_algorithm = 'partial_merge'
"""
load_dotenv()

database = os.getenv("DATABASE")

queries = [
    ("Query-1", f""" 
    SELECT 
        SUM(L_EXTENDEDPRICE) AS sum
    FROM {database}.lineitem
    """),

    ("Query-2", f""" 
    SELECT 
            COUNT(*) AS count_of_line_items,
            SUM(toFloat64(JSONExtractRaw(lineitem, 'L_EXTENDEDPRICE'))) AS sum,
            AVG(toFloat64(JSONExtractRaw(lineitem, 'L_DISCOUNT'))) AS avg,
            MIN(parseDateTimeBestEffortOrNull(JSONExtractRaw(lineitem, 'L_SHIPDATE'))) AS min,
            MAX(parseDateTimeBestEffortOrNull(JSONExtractRaw(lineitem, 'L_RECEIPTDATE'))) AS max
            FROM {database}.jlineitem
    """),

    ("Query-3", f""" 
    SELECT 
        L_ORDERKEY, 
        L_LINENUMBER, 
        L_SHIPDATE, 
        L_EXTENDEDPRICE,
        anyOrNull(L_EXTENDEDPRICE) OVER (
            PARTITION BY L_ORDERKEY 
            ORDER BY L_LINENUMBER
            ROWS BETWEEN 1 FOLLOWING AND 1 FOLLOWING
        ) AS next_line_price,
        anyOrNull(L_SHIPDATE) OVER (
            PARTITION BY L_ORDERKEY 
            ORDER BY L_LINENUMBER
            ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING
        ) AS prev_ship_date,
        any(L_EXTENDEDPRICE) OVER (
            PARTITION BY L_ORDERKEY 
            ORDER BY L_LINENUMBER
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_line_price
    FROM {database}.lineitem
    ORDER BY L_ORDERKEY, L_LINENUMBER
    LIMIT 1000
    """),

    ("Query-4", f""" 
        WITH base_table AS (
            SELECT 
                toYYYYMM(parseDateTimeBestEffortOrNull(JSONExtractRaw(lineitem, 'L_SHIPDATE'))) AS ship_year_month,
                JSONExtractRaw(lineitem, 'L_SHIPMODE') AS L_SHIPMODE,
                JSONExtractRaw(orders, 'O_ORDERPRIORITY') AS order_priority,
                COUNT(*) AS count_of_line_items,
                SUM(toFloat64(JSONExtractRaw(lineitem, 'L_EXTENDEDPRICE'))) AS sum,
                AVG(toFloat64(JSONExtractRaw(lineitem, 'L_DISCOUNT'))) AS avg
            FROM {database}.jlineitem li
            LEFT JOIN {database}.jorders ord 
                ON toInt64(JSONExtractRaw(li.lineitem, 'L_ORDERKEY')) = toInt64(JSONExtractRaw(ord.orders, 'O_ORDERKEY'))
            GROUP BY ship_year_month, L_SHIPMODE, order_priority
        )
        SELECT 
            *,
            row_number() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
            row_number() OVER (PARTITION BY L_SHIPMODE ORDER BY avg) AS row_number_by_ship_mode
        FROM base_table 
        LIMIT 1000
    """),

    ("Query-5", f""" 
    WITH customer_sales AS (
        SELECT 
            formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
            C_NAME,
            SUM(O_TOTALPRICE) AS total_spent,
            SUM(L_QUANTITY) AS total_quantity,
            rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M') ORDER BY SUM(O_TOTALPRICE) DESC) AS price_rank,
            rank() OVER (PARTITION BY formatDateTime(O_ORDERDATE, '%Y - %M') ORDER BY SUM(L_QUANTITY) DESC) AS quantity_rank
        FROM {database}.orders o
        JOIN {database}.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
        JOIN {database}.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
        GROUP BY formatDateTime(O_ORDERDATE, '%Y - %M'), C_NAME
    )
    SELECT 
        order_month, 
        C_NAME, 
        total_spent, 
        total_quantity, 
        price_rank, 
        quantity_rank
    FROM customer_sales
    WHERE price_rank <= 3 OR quantity_rank <= 3
    ORDER BY order_month, price_rank, quantity_rank 
    LIMIT 1000
    """),

    ("Query-6", f""" 
    WITH combined_comments AS (
        SELECT 
            formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
            lower(trim(replaceRegexpAll(O_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
        FROM {database}.orders o

        UNION ALL

        SELECT 
            formatDateTime(O_ORDERDATE, '%Y - %M') AS order_month,
            lower(trim(replaceRegexpAll(L_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment
        FROM {database}.lineitem l
        JOIN {database}.orders o 
        ON l.L_ORDERKEY = o.O_ORDERKEY
    ),
    tokenized_words AS (
        SELECT 
            order_month,
            splitByString(' ', cleaned_comment) AS words
        FROM combined_comments
    ),
    flattened_words AS (
        SELECT 
            order_month,
            arrayJoin(words) AS word
        FROM tokenized_words
        WHERE word NOT IN ('the', 'is', 'and', 'or', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at')
    ),
    word_counts AS (
        SELECT 
            order_month,
            word,
            COUNT(*) AS word_count,
            rank() OVER (PARTITION BY order_month ORDER BY COUNT(*) DESC) AS rank
        FROM flattened_words
        GROUP BY order_month, word
    )
    SELECT 
        order_month, 
        word, 
        word_count
    FROM word_counts
    WHERE rank <= 5
    ORDER BY order_month, word_count DESC 
    LIMIT 1000
    """),

    ("Query-7", f""" 
        WITH customer_sales AS (
        SELECT 
            formatDateTime(
                parseDateTimeBestEffortOrNull(JSONExtractRaw(o.orders, 'O_ORDERDATE')), 
                '%Y - %M'
            ) AS order_month,
            JSONExtractRaw(c.customer, 'C_NAME') AS C_NAME,
            SUM(toFloat64(JSONExtractRaw(o.orders, 'O_TOTALPRICE'))) AS total_spent,
            SUM(toFloat64(JSONExtractRaw(l.lineitem, 'L_QUANTITY'))) AS total_quantity,
            rank() OVER (
                PARTITION BY formatDateTime(parseDateTimeBestEffortOrNull(JSONExtractRaw(o.orders, 'O_ORDERDATE')), '%Y - %M')
                ORDER BY SUM(toFloat64(JSONExtractRaw(o.orders, 'O_TOTALPRICE'))) DESC
            ) AS price_rank,
            rank() OVER (
                PARTITION BY formatDateTime(parseDateTimeBestEffortOrNull(JSONExtractRaw(o.orders, 'O_ORDERDATE')), '%Y - %M')
                ORDER BY SUM(toFloat64(JSONExtractRaw(l.lineitem, 'L_QUANTITY'))) DESC
            ) AS quantity_rank
        FROM {database}.jorders o
        JOIN {database}.jlineitem l 
            ON toInt64(JSONExtractRaw(o.orders, 'O_ORDERKEY')) = toInt64(JSONExtractRaw(l.lineitem, 'L_ORDERKEY'))
        JOIN {database}.jcustomer c 
            ON toInt64(JSONExtractRaw(o.orders, 'O_CUSTKEY')) = toInt64(JSONExtractRaw(c.customer, 'C_CUSTKEY'))
        GROUP BY order_month, C_NAME
    ),
    number_extraction AS (
        SELECT *,
            replaceRegexpAll(C_NAME, '[^0-9]', '') AS customer_number
        FROM customer_sales
    ),
    digit_sum_calc AS (
        SELECT 
            order_month, 
            C_NAME, 
            total_spent, 
            total_quantity, 
            price_rank, 
            quantity_rank, 
            customer_number,
            sum(toInt32(arrayJoin(splitByString('', customer_number)))) AS number_sum
        FROM number_extraction
        GROUP BY 
            order_month, 
            C_NAME, 
            total_spent, 
            total_quantity, 
            price_rank, 
            quantity_rank, 
            customer_number
    )
    SELECT 
        order_month, 
        C_NAME, 
        total_spent, 
        total_quantity, 
        price_rank, 
        quantity_rank
    FROM digit_sum_calc
    WHERE (price_rank <= 3 OR quantity_rank <= 3)
    AND modulo(number_sum, 2) = 1
    ORDER BY order_month, price_rank, quantity_rank 
    LIMIT 1000

    """),

    ("Query-8", f""" 
    WITH order_comments AS (
        SELECT 
            c.C_CUSTKEY,
            c.C_NAME,
            lower(trim(replaceRegexpAll(o.O_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
            CASE 
                WHEN length(o.O_COMMENT) > 100 THEN 'LONG_COMMENT'
                ELSE 'SHORT_COMMENT'
            END AS comment_type
        FROM {database}.orders o
        JOIN {database}.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
    ),
    lineitem_comments AS (
        SELECT 
            c.C_CUSTKEY,
            c.C_NAME,
            lower(trim(replaceRegexpAll(l.L_COMMENT, '[^a-zA-Z0-9 ]', ''))) AS cleaned_comment,
            CASE 
                WHEN length(l.L_COMMENT) > 100 THEN 'LONG_COMMENT'
                ELSE 'SHORT_COMMENT'
            END AS comment_type
        FROM {database}.lineitem l
        JOIN {database}.orders o ON l.L_ORDERKEY = o.O_ORDERKEY
        JOIN {database}.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
    ),
    combined_comments AS (
        SELECT * FROM order_comments
        UNION ALL
        SELECT * FROM lineitem_comments
    ),
    comment_counts AS (
        SELECT 
            C_CUSTKEY,
            COUNT(*) AS total_comments
        FROM combined_comments
        GROUP BY C_CUSTKEY
    ),
    filtered_comments AS (
        SELECT 
            cc.C_CUSTKEY,
            cc.C_NAME,
            cc.cleaned_comment,
            cc.comment_type,
            COALESCE(ccc.total_comments, 0) AS total_comments
        FROM combined_comments cc
        LEFT JOIN comment_counts ccc ON cc.C_CUSTKEY = ccc.C_CUSTKEY
        WHERE position('final', cc.cleaned_comment) > 0
    ),
    ranked_comments AS (
        SELECT 
            C_CUSTKEY,
            C_NAME,
            cleaned_comment,
            comment_type,
            total_comments,
            row_number() OVER (PARTITION BY C_CUSTKEY ORDER BY length(cleaned_comment) DESC) AS comment_rank
        FROM filtered_comments
    )
    SELECT 
        rc.C_CUSTKEY, 
        rc.C_NAME, 
        groupArray(concat(rc.cleaned_comment, ' (', rc.comment_type, ')')) AS customer_comments,
        MAX(rc.total_comments) AS total_comments_per_customer
    FROM ranked_comments rc
    WHERE rc.comment_rank <= 5 
    GROUP BY rc.C_CUSTKEY, rc.C_NAME
    ORDER BY total_comments_per_customer DESC 
    LIMIT 1000
    """),

    ("Query-9", f""" 
    WITH customer_orders AS (
        SELECT 
            c.C_CUSTKEY,
            c.C_NAME,
            o.O_ORDERDATE,
            SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
            COUNT(*) AS order_count,
            row_number() OVER (PARTITION BY c.C_CUSTKEY ORDER BY o.O_ORDERDATE) AS order_rank
        FROM {database}.customer c
        JOIN {database}.orders o ON c.C_CUSTKEY = o.O_CUSTKEY
        JOIN {database}.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
        WHERE O_ORDERDATE >= subtractYears(today(), 30)
        AND l.L_SHIPDATE > o.O_ORDERDATE 
        GROUP BY c.C_CUSTKEY, c.C_NAME, o.O_ORDERDATE
    ),
    cumulative_revenue AS (
        SELECT 
            C_CUSTKEY,
            C_NAME,
            order_rank,
            O_ORDERDATE,
            total_revenue,
            sum(total_revenue) OVER (PARTITION BY C_CUSTKEY ORDER BY order_rank) AS cumulative_revenue 
        FROM customer_orders
    ),
    monthly_analysis AS (
        SELECT 
            C_CUSTKEY,
            C_NAME,
            toStartOfMonth(O_ORDERDATE) AS order_month,
            COUNT(*) AS monthly_orders,
            SUM(total_revenue) AS monthly_revenue
        FROM cumulative_revenue
        GROUP BY C_CUSTKEY, C_NAME, toStartOfMonth(O_ORDERDATE)
    )
    SELECT 
        m.C_CUSTKEY,
        m.C_NAME,
        groupArray(
            concat(
                'Month: ', formatDateTime(order_month, '%Y-%m'),
                ', Orders: ', toString(monthly_orders),
                ', Revenue: ', toString(round(monthly_revenue, 2))
            )
        ) AS monthly_summary,
        MAX(cumulative_revenue) AS lifetime_revenue 
    FROM monthly_analysis m
    JOIN cumulative_revenue c ON m.C_CUSTKEY = c.C_CUSTKEY
    GROUP BY m.C_CUSTKEY, m.C_NAME
    ORDER BY lifetime_revenue DESC 
    LIMIT 1000
    """),

    ("Query-10", f""" 
    WITH customer_orders AS (
        SELECT 
            c.C_CUSTKEY,
            c.C_NAME,
            o.O_ORDERDATE,
            COUNT(*) AS total_orders,
            SUM(l.L_EXTENDEDPRICE * (1 - l.L_DISCOUNT)) AS total_revenue,
            SUM(if(l.L_SHIPDATE <= addDays(o.O_ORDERDATE, 30), 1, 0)) AS shipped_orders 
        FROM {database}.customer c
        JOIN {database}.orders o ON c.C_CUSTKEY = o.O_CUSTKEY
        JOIN {database}.lineitem l ON o.O_ORDERKEY = l.L_ORDERKEY
        WHERE o.O_ORDERDATE >= subtractYears(today(), 30)
        GROUP BY c.C_CUSTKEY, c.C_NAME, o.O_ORDERDATE
    ),
    customer_metrics AS (
        SELECT 
            C_CUSTKEY,
            C_NAME,
            SUM(total_orders) AS total_orders_per_customer,
            SUM(total_revenue) AS total_revenue_per_customer,
            SUM(shipped_orders) AS total_shipped_orders_per_customer,
            avg(if(total_orders = 0, NULL, total_revenue / total_orders)) AS avg_revenue_per_order 
        FROM customer_orders
        GROUP BY C_CUSTKEY, C_NAME
    ),
    customer_ratios AS (
        SELECT 
            C_CUSTKEY,
            C_NAME,
            total_orders_per_customer,
            total_revenue_per_customer,
            total_shipped_orders_per_customer,
            avg_revenue_per_order,
            if(total_orders_per_customer = 0, NULL, 
               toFloat64(total_shipped_orders_per_customer) / total_orders_per_customer) AS shipped_ratio 
        FROM customer_metrics
    )
    SELECT 
        C_CUSTKEY,
        C_NAME,
        total_orders_per_customer,
        total_revenue_per_customer,
        avg_revenue_per_order,
        shipped_ratio * 100 AS shipped_percentage 
    FROM customer_ratios
    WHERE shipped_ratio > 0.5 
    ORDER BY avg_revenue_per_order DESC 
    LIMIT 1000
    """),

    ("Query-11", f""" 
        SELECT 
        toInt64(JSONExtractRaw(o.orders, 'O_ORDERKEY')) AS orderkey,
        parseDateTimeBestEffortOrNull(JSONExtractRaw(o.orders, 'O_ORDERDATE')) AS orderdate,
        toFloat64(JSONExtractRaw(o.orders, 'O_TOTALPRICE')) AS totalprice,
        lineitems.total_revenue,
        lineitems.avg_discount
    FROM (
        SELECT 
            toInt64(JSONExtractRaw(l.lineitem, 'L_ORDERKEY')) AS orderkey,
            SUM(
                toFloat64(JSONExtractRaw(l.lineitem, 'L_EXTENDEDPRICE')) * 
                (1 - toFloat64(JSONExtractRaw(l.lineitem, 'L_DISCOUNT')))
            ) AS total_revenue,
            AVG(toFloat64(JSONExtractRaw(l.lineitem, 'L_DISCOUNT'))) AS avg_discount
        FROM {database}.jlineitem l
        GROUP BY orderkey
    ) AS lineitems
    JOIN {database}.jorders o
        ON lineitems.orderkey = toInt64(JSONExtractRaw(o.orders, 'O_ORDERKEY'))
    WHERE lineitems.total_revenue > 50000
    AND lineitems.avg_discount < 0.05
    ORDER BY lineitems.total_revenue DESC 
    LIMIT 1000
    """),
("Query-F", f""" 
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
    FROM {database}.supplier s
    JOIN {database}.lineitem l ON s.S_SUPPKEY = l.L_SUPPKEY
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
            FROM {database}.lineitem l
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
            FROM {database}.lineitem l
            JOIN {database}.orders o ON l.L_ORDERKEY = o.O_ORDERKEY
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
            FROM {database}.lineitem l
            JOIN {database}.orders o ON l.L_ORDERKEY = o.O_ORDERKEY
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
            FROM {database}.part p
            JOIN {database}.partsupp ps ON p.P_PARTKEY = ps.PS_PARTKEY
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
        -- Step 8: Analyze part Categories and Their Supply Chain Characteristics
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
            FROM {database}.part p
            JOIN part_supplier_diversity psd 
                ON p.P_PARTKEY = psd.P_PARTKEY
            JOIN {database}.partsupp ps 
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
            FROM {database}.supplier s
            JOIN supplier_delivery_metrics sdm 
                ON s.S_SUPPKEY = sdm.s_suppkey
            JOIN {database}.NATION n 
                ON s.S_NATIONKEY = n.N_NATIONKEY
            JOIN {database}.lineitem l 
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
            FROM {database}.REGION r
            JOIN nation_performance np ON r.R_REGIONKEY = np.N_REGIONKEY
            JOIN {database}.NATION n ON np.N_NATIONKEY = n.N_NATIONKEY
            JOIN {database}.supplier s ON n.N_NATIONKEY = s.S_NATIONKEY
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
            FROM {database}.lineitem l
            JOIN {database}.orders o 
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
                AS diversification_risk_score,
                
                (sca.avg_return_rate * 5) +
                (if(sca.max_return_rate > 30, (sca.max_return_rate - 30) * 2, 0)) AS quality_risk_score
            FROM supplier_delivery_metrics sdm
            JOIN supplier_customer_analysis sca ON sdm.S_SUPPKEY = sca.L_SUPPKEY
            LEFT JOIN (
                SELECT
                    L_SUPPKEY,
                    arrayMin(groupArray(months_since_last_activity)) AS recent_activity
                FROM supplier_transaction_frequency
                WHERE months_since_last_activity IS NOT NULL
                GROUP BY L_SUPPKEY
            ) stf ON sdm.S_SUPPKEY = stf.L_SUPPKEY
        ),
        -- Step 14: Aggregate Seasonal Insights per Supplier (Quarterly)
        supplier_seasonality_quarterly_agg AS (
            SELECT
                ssq.L_SUPPKEY,
                maxIf(ssq.quarter, ssq.quantity_quarter_rank = 1) AS peak_quantity_quarter,
                maxIf(ssq.quarter, ssq.revenue_quarter_rank = 1) AS peak_revenue_quarter,
                avg(if(ssq.yoy_quantity_growth IS NOT NULL, abs(ssq.yoy_quantity_growth), NULL)) AS avg_quantity_volatility,
                avg(if(ssq.yoy_revenue_growth IS NOT NULL, abs(ssq.yoy_revenue_growth), NULL)) AS avg_revenue_volatility,
                max(ssq.yoy_revenue_growth) AS max_revenue_growth,
                min(ssq.yoy_revenue_growth) AS min_revenue_growth,
                avg(ssq.unique_parts_in_quarter) AS avg_unique_parts_per_quarter,
                max(ssq.active_months_in_quarter) AS max_active_months_in_quarter,
                avg(ssq.avg_quantity_per_order) AS overall_avg_quantity_per_order,
                avg(ssq.avg_revenue_per_order) AS overall_avg_revenue_per_order,
                stddevPop(ssq.quarterly_revenue) / nullIf(avg(ssq.quarterly_revenue), 0) * 100 AS revenue_coefficient_of_variation
            FROM supplier_seasonality_quarterly ssq
            GROUP BY ssq.L_SUPPKEY
        ),
        -- Step 15: Aggregate Seasonal Insights per Supplier (Monthly)
        supplier_seasonality_monthly_agg AS (
            SELECT
                ssm.L_SUPPKEY,
                maxIf(ssm.month, ssm.quantity_month_rank = 1) AS peak_quantity_month,
                maxIf(ssm.month, ssm.revenue_month_rank = 1) AS peak_revenue_month,
                avg(if(ssm.yoy_quantity_growth_monthly IS NOT NULL,
                    abs(ssm.yoy_quantity_growth_monthly),
                    NULL)) AS avg_monthly_quantity_volatility,
                avg(if(ssm.yoy_revenue_growth_monthly IS NOT NULL,
                    abs(ssm.yoy_revenue_growth_monthly),
                    NULL)) AS avg_monthly_revenue_volatility,
                max(ssm.yoy_revenue_growth_monthly) AS max_monthly_revenue_growth,
                min(ssm.yoy_revenue_growth_monthly) AS min_monthly_revenue_growth,
                stddevPop(ssm.monthly_revenue) / 
                    nullIf(avg(ssm.monthly_revenue), 0) * 100 AS monthly_revenue_coefficient_of_variation
            FROM supplier_seasonality_monthly ssm
            GROUP BY ssm.L_SUPPKEY
        ),
        -- Step 16: Parts Supplied Analysis (Modified)
        supplier_parts_profile AS (
            WITH lineitem_quantities AS (
                SELECT 
                    L_SUPPKEY,
                    SUM(L_QUANTITY) as total_quantity_sold
                FROM {database}.lineitem
                GROUP BY L_SUPPKEY
            )
            SELECT
                ps.PS_SUPPKEY,
                COUNT(DISTINCT ps.PS_PARTKEY) AS unique_parts_supplied,
                COUNT(DISTINCT p.P_MFGR) AS manufacturer_count,
                COUNT(DISTINCT p.P_BRAND) AS brand_count,
                COUNT(DISTINCT splitByString(' ', p.P_TYPE)[1]) AS part_category_count,
                avg(ps.PS_SUPPLYCOST) AS avg_supply_cost,
                min(ps.PS_SUPPLYCOST) AS min_supply_cost,
                max(ps.PS_SUPPLYCOST) AS max_supply_cost,
                stddevPop(ps.PS_SUPPLYCOST) AS supply_cost_stddev,
                sum(ps.PS_AVAILQTY) AS total_availability,
                min(ps.PS_AVAILQTY) AS min_availability,
                max(ps.PS_AVAILQTY) AS max_availability,
                avg(toFloat64(ps.PS_AVAILQTY)) AS avg_availability,
                stddevPop(ps.PS_AVAILQTY) AS availability_stddev,
                avg(toFloat64(ps.PS_AVAILQTY) * p.P_RETAILPRICE) AS avg_inventory_value,
                sum(ps.PS_AVAILQTY * p.P_RETAILPRICE) AS total_inventory_value,
                COUNT(DISTINCT splitByString(' ', p.P_TYPE)[1]) AS category_diversity,
                avg(if(psd.supplier_count IS NOT NULL,
                    toFloat64(psd.supplier_count),
                    1.0)) AS avg_supply_chain_redundancy,
                sum(if(p.P_RETAILPRICE > 1000, 1, 0)) * 100.0 / 
                    nullIf(COUNT(*), 0) AS premium_part_percentage,
                sum(toFloat64(ps.PS_AVAILQTY)) / 
                    nullIf(sum(lq.total_quantity_sold), 0) AS inventory_turnover_ratio
            FROM {database}.partsupp ps
            JOIN {database}.part p 
                ON ps.PS_PARTKEY = p.P_PARTKEY
            LEFT JOIN part_supplier_diversity psd 
                ON p.P_PARTKEY = psd.P_PARTKEY
            LEFT JOIN lineitem_quantities lq
                ON ps.PS_SUPPKEY = lq.L_SUPPKEY
            GROUP BY ps.PS_SUPPKEY
        ),
        -- Step 17: Text Analysis of Supplier Comments
        supplier_comment_analysis AS (
            SELECT
                S_SUPPKEY,
                S_COMMENT,
                length(S_COMMENT) AS comment_length,
                -- Positive mentions using string functions
                (
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'quality', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'reliable', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'good', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'excellent', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'best', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'quick', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'fast', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'prompt', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'timely', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'superior', ''))
                ) / toFloat64(length('quality')) AS positive_mentions,
                
                -- Negative mentions using string functions
                (
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'delay', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'issue', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'problem', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'complaint', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'late', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'bad', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'slow', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'poor', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'dissatisfied', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'disappointed', ''))
                ) / toFloat64(length('delay')) AS negative_mentions,
                
                -- Sentiment analysis based on mention counts
                multiIf(
                    positive_mentions > negative_mentions, 'Positive',
                    positive_mentions < negative_mentions, 'Negative',
                    'Neutral'
                ) AS sentiment,
                
                -- Financial mentions
                (
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'price', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'cost', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'discount', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'rate', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'value', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'expense', ''))
                ) / toFloat64(length('price')) AS financial_mentions,
                
                -- Logistics mentions
                (
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'ship', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'deliver', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'transport', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'carry', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'move', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'logistics', ''))
                ) / toFloat64(length('ship')) AS logistics_mentions,
                
                -- Product mentions
                (
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'part', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'item', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'product', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'stock', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'component', '')) +
                    length(lower(S_COMMENT)) - length(replaceAll(lower(S_COMMENT), 'material', ''))
                ) / toFloat64(length('part')) AS product_mentions
            FROM {database}.supplier
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
                toInt32(sdm.total_orders) AS total_orders,
                sdm.avg_delivery_delay,
                sdm.median_delivery_delay,
                sdm.p90_delivery_delay,
                toInt32(sdm.late_deliveries) AS late_deliveries,
                toInt32(sdm.on_time_deliveries) AS on_time_deliveries,
                toInt32(sdm.severely_late_deliveries) AS severely_late_deliveries,
                sdm.total_revenue,
                sdm.total_tax,
                toInt32(sdm.total_quantity) AS total_quantity,
                sdm.avg_discount_rate,
                sdm.max_discount_offered,
                sdm.revenue_volatility,
                sdm.revenue_variance,
                sdm.first_shipment_date,
                sdm.last_shipment_date,
                toInt32(sdm.active_days) AS active_days,
                toInt32(sdm.unique_parts_shipped) AS unique_parts_shipped,
                toInt32(stf.transactions_per_month) AS transactions_per_month,
                toInt32(stf.quantity_per_month) AS quantity_per_month,
                stf.revenue_per_month,
                toInt32(stf.prev_month_transactions) AS prev_month_transactions,
                toInt32(stf.prev_month_quantity) AS prev_month_quantity,
                stf.prev_month_revenue,
                toInt32(stf.months_since_last_activity) AS months_since_last_activity,
                toInt32(ssq_agg.peak_quantity_quarter) AS peak_quantity_quarter,
                toInt32(ssq_agg.peak_revenue_quarter) AS peak_revenue_quarter,
                ssq_agg.avg_quantity_volatility,
                ssq_agg.avg_revenue_volatility,
                ssq_agg.max_revenue_growth,
                ssq_agg.min_revenue_growth,
                ssq_agg.avg_unique_parts_per_quarter,
                toInt32(ssq_agg.max_active_months_in_quarter) AS max_active_months_in_quarter,
                ssq_agg.overall_avg_quantity_per_order,
                ssq_agg.overall_avg_revenue_per_order,
                ssq_agg.revenue_coefficient_of_variation,
                toInt32(ssm_agg.peak_quantity_month) AS peak_quantity_month,
                toInt32(ssm_agg.peak_revenue_month) AS peak_revenue_month,
                ssm_agg.avg_monthly_quantity_volatility,
                ssm_agg.avg_monthly_revenue_volatility,
                ssm_agg.max_monthly_revenue_growth,
                ssm_agg.min_monthly_revenue_growth,
                ssm_agg.monthly_revenue_coefficient_of_variation,
                srs.delivery_risk_score,
                srs.financial_risk_score,
                srs.diversification_risk_score,
                srs.quality_risk_score,
                toInt32(spp.unique_parts_supplied) AS unique_parts_supplied,
                toInt32(spp.manufacturer_count) AS manufacturer_count,
                toInt32(spp.brand_count) AS brand_count,
                toInt32(spp.part_category_count) AS part_category_count,
                spp.avg_supply_cost,
                spp.min_supply_cost,
                spp.max_supply_cost,
                spp.supply_cost_stddev,
                toInt32(spp.total_availability) AS total_availability,
                toInt32(spp.min_availability) AS min_availability,
                toInt32(spp.max_availability) AS max_availability,
                spp.avg_availability,
                spp.availability_stddev,
                spp.avg_inventory_value,
                spp.total_inventory_value,
                toInt32(spp.category_diversity) AS category_diversity,
                spp.avg_supply_chain_redundancy,
                spp.premium_part_percentage,
                spp.inventory_turnover_ratio,
                sca.sentiment,
                toInt32(sca.comment_length) AS comment_length,
                sca.positive_mentions,
                sca.negative_mentions,
                sca.financial_mentions,
                sca.logistics_mentions,
                sca.product_mentions
            FROM supplier_delivery_metrics sdm
            LEFT JOIN supplier_transaction_frequency stf 
                ON sdm.S_SUPPKEY = stf.L_SUPPKEY
            LEFT JOIN supplier_seasonality_quarterly_agg ssq_agg 
                ON sdm.S_SUPPKEY = ssq_agg.L_SUPPKEY
            LEFT JOIN supplier_seasonality_monthly_agg ssm_agg 
                ON sdm.S_SUPPKEY = ssm_agg.L_SUPPKEY
            LEFT JOIN supplier_risk_scores srs 
                ON sdm.S_SUPPKEY = srs.S_SUPPKEY
            LEFT JOIN supplier_parts_profile spp 
                ON sdm.S_SUPPKEY = spp.PS_SUPPKEY
            LEFT JOIN supplier_comment_analysis sca 
                ON sdm.S_SUPPKEY = sca.S_SUPPKEY
        )
        SELECT * FROM final_supplier_report limit 1000
     """
    )
    
]






