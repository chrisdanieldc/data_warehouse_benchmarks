from dotenv import load_dotenv
import os

load_dotenv()

firebolt_database = os.getenv("FIREBOLT_DATABASE")
firebolt_schema = os.getenv("FIREBOLT_SCHEMA")


queries = [
    ("query-1", f"""
    select
        sum(l_extendedprice) as sum
    from {firebolt_database}.{firebolt_schema}.lineitem;
    """),
    ("query-2", f"""
        SELECT
            COUNT(*) AS count_of_line_items,
            SUM(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_extendedprice') AS FLOAT)) AS sum,
            AVG(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_discount') AS FLOAT)) AS avg,
            MIN(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_shipdate') AS DATE)) AS min,
            MAX(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_receiptdate') AS DATE)) AS max
        FROM {firebolt_database}.{firebolt_schema}.jlineitem;
    """),
    ("query-3", f"""
    select
        l_orderkey,
        l_linenumber,
        l_shipdate,
        l_extendedprice,
        lead(l_extendedprice) over (partition by l_orderkey order by l_linenumber) as next_line_price,
        lag(l_shipdate) over (partition by l_orderkey order by l_linenumber) as prev_ship_date,
        first_value(l_extendedprice) over (partition by l_orderkey order by l_linenumber) as first_line_price
    from {firebolt_database}.{firebolt_schema}.lineitem
    order by l_orderkey, l_linenumber limit 1000;
    """),
    ("query-4", f"""
        WITH base_table AS (
        SELECT
            EXTRACT(year FROM CAST(JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_shipdate') AS DATE)) || '-' ||
            LPAD(EXTRACT(month FROM CAST(JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_shipdate') AS DATE))::STRING, 2, '0') AS ship_year_month,
            JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_shipmode') AS l_shipmode,
            JSON_POINTER_EXTRACT_TEXT(ord.json_data, '/o_orderpriority') AS order_priority,
            COUNT(*) AS count_of_line_items,
            SUM(CAST(JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_extendedprice') AS FLOAT)) AS sum,
            AVG(CAST(JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_discount') AS FLOAT)) AS avg
        FROM {firebolt_database}.{firebolt_schema}.jlineitem li
        LEFT JOIN {firebolt_database}.{firebolt_schema}.jorders ord
            ON CAST(JSON_POINTER_EXTRACT_TEXT(li.json_data, '/l_orderkey') AS INT) =
            CAST(JSON_POINTER_EXTRACT_TEXT(ord.json_data, '/o_orderkey') AS INT)
        GROUP BY ship_year_month, l_shipmode, order_priority
    )
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY order_priority ORDER BY sum) AS row_number_by_order_priority,
        ROW_NUMBER() OVER (PARTITION BY l_shipmode ORDER BY avg) AS row_number_by_ship_mode
    FROM base_table 
    LIMIT 1000;
    """),
    ("query-5", f"""
            with customer_sales as (
            select
                extract(year from cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date)) || ' - ' ||
                to_char(cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date), 'month') as order_month,
                JSON_POINTER_EXTRACT(c.json_data, '/c_name') as c_name,
                sum(cast(JSON_POINTER_EXTRACT(o.json_data, '/o_totalprice') as float)) as total_spent,
                sum(cast(JSON_POINTER_EXTRACT(l.json_data, '/l_quantity') as int)) as total_quantity,
                rank() over (
                    partition by extract(year from cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date)) || ' - ' ||
                            to_char(cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date), 'month')
                    order by sum(cast(JSON_POINTER_EXTRACT(o.json_data, '/o_totalprice') as float)) desc
                ) as price_rank,
                rank() over (
                    partition by extract(year from cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date)) || ' - ' ||
                            to_char(cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderdate') as date), 'month')
                    order by sum(cast(JSON_POINTER_EXTRACT(l.json_data, '/l_quantity') as int)) desc
                ) as quantity_rank
            from jorders o
            join jlineitem l
                on cast(JSON_POINTER_EXTRACT(o.json_data, '/o_orderkey') as int) =
                cast(JSON_POINTER_EXTRACT(l.json_data, '/l_orderkey') as int)
            join jcustomer c
                on cast(JSON_POINTER_EXTRACT(o.json_data, '/o_custkey') as int) =
                cast(JSON_POINTER_EXTRACT(c.json_data, '/c_custkey') as int)
            group by order_month, c_name
        )
        select order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
        from customer_sales
        where price_rank <= 3 or quantity_rank <= 3
        order by order_month, price_rank, quantity_rank limit 1000;
    """),
    ("query-6", f"""
            with combined_comments as (
            select
                extract(year from cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date)) || ' - ' ||
                to_char(cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date), 'month') as order_month,
                lower(REGEXP_REPLACE(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_comment'), '[^a-zA-Z0-9 ]', '')) as cleaned_comment
            from jorders o
            union all
            select
                extract(year from cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date)) || ' - ' ||
                to_char(cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date), 'month') as order_month,
                lower(REGEXP_REPLACE(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_comment'), '[^a-zA-Z0-9 ]', '')) as cleaned_comment
            from jlineitem l
            join jorders o
                on cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_orderkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderkey') as int)
        ),
        tokenized_words as (
            select
                order_month,
                trim(word) as word
            from combined_comments,
            UNNEST(STRING_TO_ARRAY(cleaned_comment, ' ')) as t(word)
        ),
        word_counts as (
            select
                order_month,
                word,
                count(*) as word_count,
                rank() over (partition by order_month order by count(*) desc) as rank
            from tokenized_words
            where word not in ('the', 'is', 'and', 'or', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at')
            group by order_month, word
        )
        select order_month, word, word_count
        from word_counts
        where rank <= 5
        order by order_month, word_count desc limit 1000;
    """),
    ("query-7", f"""
            WITH customer_sales AS (
            SELECT
                EXTRACT(year FROM CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE)) || ' - ' ||
                TO_CHAR(CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE), 'month') AS order_month,
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name') AS c_name,
                SUM(CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_totalprice') AS FLOAT)) AS total_spent,
                SUM(CAST(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_quantity') AS INT)) AS total_quantity,
                RANK() OVER (
                    PARTITION BY EXTRACT(year FROM CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE)) || ' - ' ||
                            TO_CHAR(CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE), 'month')
                    ORDER BY SUM(CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_totalprice') AS FLOAT)) DESC
                ) AS price_rank,
                RANK() OVER (
                    PARTITION BY EXTRACT(year FROM CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE)) || ' - ' ||
                            TO_CHAR(CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') AS DATE), 'month')
                    ORDER BY SUM(CAST(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_quantity') AS INT)) DESC
                ) AS quantity_rank
            FROM {firebolt_database}.{firebolt_schema}.jorders o
            JOIN {firebolt_database}.{firebolt_schema}.jlineitem l
                ON CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderkey') AS INT) =
                CAST(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_orderkey') AS INT)
            JOIN {firebolt_database}.{firebolt_schema}.jcustomer c
                ON CAST(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_custkey') AS INT) =
                CAST(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') AS INT)
            GROUP BY order_month, c_name
        ),
        number_extraction AS (
            SELECT *,
                REGEXP_REPLACE(c_name, '[^0-9]', '') AS customer_number
            FROM customer_sales
        ),
        digit_sum_calc AS (
            SELECT
                order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank, customer_number,
                SUM(CAST(digit AS INT)) AS number_sum
            FROM number_extraction,
            UNNEST(STRING_TO_ARRAY(customer_number, '')) AS digit
            GROUP BY order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank, customer_number
        )
        SELECT order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
        FROM digit_sum_calc
        WHERE (price_rank <= 3 OR quantity_rank <= 3)
        AND MOD(number_sum, 2) = 1
        ORDER BY order_month, price_rank, quantity_rank 
        LIMIT 1000;
    """),
    ("query-8", f"""

            with order_comments as (
            select
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) as c_custkey,
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name') as c_name,
                lower(REGEXP_REPLACE(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_comment'), '[^a-zA-Z0-9 ]', '')) as cleaned_comment,
                case
                    when length(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_comment')) > 100 then 'long_comment'
                    else 'short_comment'
                end as comment_type
            from jorders o
            join jcustomer c
                on cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_custkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int)
        ),
        lineitem_comments as (
            select
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) as c_custkey,
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name') as c_name,
                lower(REGEXP_REPLACE(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_comment'), '[^a-zA-Z0-9 ]', '')) as cleaned_comment,
                case
                    when length(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_comment')) > 100 then 'long_comment'
                    else 'short_comment'
                end as comment_type
            from jlineitem l
            join jorders o
                on cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_orderkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderkey') as int)
            join jcustomer c
                on cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_custkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int)
        ),
        combined_comments as (
            select * from order_comments
            union all
            select * from lineitem_comments
        ),
        comment_counts as (
            select
                c_custkey,
                count(*) as total_comments
            from combined_comments
            group by c_custkey
        ),
        filtered_comments as (
            select
                cc.c_custkey,
                cc.c_name,
                cc.cleaned_comment,
                cc.comment_type,
                coalesce(ccc.total_comments, 0) as total_comments
            from combined_comments cc
            left join comment_counts ccc on cc.c_custkey = ccc.c_custkey
            where cc.cleaned_comment like '%final%'
        ),
        ranked_comments as (
            select
                c_custkey,
                c_name,
                cleaned_comment,
                comment_type,
                total_comments,
                row_number() over (partition by c_custkey order by length(cleaned_comment) desc) as comment_rank
            from filtered_comments
        )
        select
            rc.c_custkey,
            rc.c_name,
            ARRAY_AGG(CONCAT(rc.cleaned_comment, ' (', rc.comment_type, ')')) as customer_comments,
            max(rc.total_comments) as total_comments_per_customer
        from ranked_comments rc
        where rc.comment_rank <= 5
        group by rc.c_custkey, rc.c_name
        order by total_comments_per_customer desc limit 1000;
    
    """),
    ("query-9", f"""

            with customer_orders as (
            select
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) as c_custkey,
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name') as c_name,
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) as o_orderdate,
                sum(cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_extendedprice') as float) *
                    (1 - cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_discount') as float))) as total_revenue,
                count(*) as order_count,
                row_number() over (partition by cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int)
                                order by cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) asc) as order_rank
            from jcustomer c
            join jorders o
                on cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_custkey') as int)
            join jlineitem l
                on cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_orderkey') as int)
            where cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) >= current_date - INTERVAL '30' YEAR
            group by
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int),
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name'),
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date)
        ),
        cumulative_revenue as (
            select
                c_custkey,
                c_name,
                order_rank,
                o_orderdate,
                total_revenue,
                sum(total_revenue) over (partition by c_custkey order by order_rank asc) as cumulative_revenue
            from customer_orders
        ),
        monthly_analysis as (
            select
                c_custkey,
                c_name,
                DATE_TRUNC('month', o_orderdate) as order_month,
                count(*) as monthly_orders,
                sum(total_revenue) as monthly_revenue
            from cumulative_revenue
            group by c_custkey, c_name, DATE_TRUNC('month', o_orderdate)
        ),
        customer_lifetime as (
            select
                c_custkey,
                max(cumulative_revenue) as lifetime_revenue
            from cumulative_revenue
            group by c_custkey
        ),
        monthly_summary as (
            select
                c_custkey,
                c_name,
                ARRAY_SORT(
                    ARRAY_AGG(
                        CONCAT('month: ', TO_CHAR(order_month, 'YYYY-MM'),
                            ', orders: ', cast(monthly_orders as TEXT),
                            ', revenue: ', cast(round(monthly_revenue, 2) as TEXT))
                    )
                ) as monthly_summary
            from monthly_analysis
            group by c_custkey, c_name
        )
        select
            ms.c_custkey,
            ms.c_name,
            ms.monthly_summary,
            cl.lifetime_revenue
        from monthly_summary ms
        join customer_lifetime cl on ms.c_custkey = cl.c_custkey
        order by cl.lifetime_revenue desc
        limit 1000;
    
    """),
    ("query-10", f"""
                with customer_orders as (
            select
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) as c_custkey,
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name') as c_name,
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) as o_orderdate,
                sum(cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_extendedprice') as float) *
                    (1 - cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_discount') as float))) as total_revenue,
                count(*) as order_count,
                row_number() over (partition by cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int)
                                order by cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) asc) as order_rank
            from jcustomer c
            join jorders o
                on cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_custkey') as int)
            join jlineitem l
                on cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderkey') as int) =
                cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_orderkey') as int)
            where cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date) >= current_date - INTERVAL '30' YEAR
            and cast(JSON_POINTER_EXTRACT_TEXT(l.json_data, '/l_shipdate') as date) >
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date)
            group by
                cast(JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_custkey') as int),
                JSON_POINTER_EXTRACT_TEXT(c.json_data, '/c_name'),
                cast(JSON_POINTER_EXTRACT_TEXT(o.json_data, '/o_orderdate') as date)
        ),
        cumulative_revenue as (
            select
                c_custkey,
                c_name,
                order_rank,
                o_orderdate,
                total_revenue,
                sum(total_revenue) over (partition by c_custkey order by order_rank asc) as cumulative_revenue
            from customer_orders
        ),
        monthly_analysis as (
            select
                c_custkey,
                c_name,
                DATE_TRUNC('month', o_orderdate) as order_month,
                count(*) as monthly_orders,
                sum(total_revenue) as monthly_revenue
            from cumulative_revenue
            group by c_custkey, c_name, DATE_TRUNC('month', o_orderdate)
        ),
        customer_lifetime as (
            select
                c_custkey,
                max(cumulative_revenue) as lifetime_revenue
            from cumulative_revenue
            group by c_custkey
        ),
        monthly_summary as (
            select
                c_custkey,
                c_name,
                ARRAY_SORT(
                    ARRAY_AGG(
                        CONCAT('month: ', TO_CHAR(order_month, 'YYYY-MM'),
                            ', orders: ', cast(monthly_orders as TEXT),
                            ', revenue: ', cast(round(monthly_revenue, 2) as TEXT))
                    )
                ) as monthly_summary
            from monthly_analysis
            group by c_custkey, c_name
        )
        select
            ms.c_custkey,
            ms.c_name,
            ms.monthly_summary,
            cl.lifetime_revenue
        from monthly_summary ms
        join customer_lifetime cl on ms.c_custkey = cl.c_custkey
        order by cl.lifetime_revenue desc
        limit 1000;
    """),
    ("query-11", f"""
        SELECT
    CAST(JSON_POINTER_EXTRACT_TEXT(orders.json_data, '/o_orderkey') AS INT) AS orderkey,
    CAST(JSON_POINTER_EXTRACT_TEXT(orders.json_data, '/o_orderdate') AS DATE) AS orderdate,
    CAST(JSON_POINTER_EXTRACT_TEXT(orders.json_data, '/o_totalprice') AS FLOAT) AS totalprice,
    lineitems.total_revenue,
    lineitems.avg_discount
FROM (
    SELECT
        CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_orderkey') AS INT) AS orderkey,
        SUM(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_extendedprice') AS FLOAT) *
            (1 - CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_discount') AS FLOAT))) AS total_revenue,
        AVG(CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_discount') AS FLOAT)) AS avg_discount
    FROM {firebolt_database}.{firebolt_schema}.jlineitem
    GROUP BY CAST(JSON_POINTER_EXTRACT_TEXT(json_data, '/l_orderkey') AS INT)
) AS lineitems
JOIN {firebolt_database}.{firebolt_schema}.jorders AS orders
    ON lineitems.orderkey = CAST(JSON_POINTER_EXTRACT_TEXT(orders.json_data, '/o_orderkey') AS INT)
WHERE lineitems.total_revenue > 50000
AND lineitems.avg_discount < 0.05
ORDER BY lineitems.total_revenue DESC 
LIMIT 1000;
    """),
    ("query-f", f"""

-- step 1: analyze supplier delivery performance
    with supplier_delivery_metrics as (
        select
            s.s_suppkey,
            s.s_name,
            s.s_nationkey,
            s.s_acctbal,
            s.s_address,
            s.s_phone,
            count(distinct l.l_orderkey) as total_orders,
            avg(date_diff('day', l.l_commitdate, l.l_receiptdate)) as avg_delivery_delay,
            percentile_cont(0.5) within group (order by date_diff('day', l.l_commitdate, l.l_receiptdate)) as median_delivery_delay,
            percentile_cont(0.90) within group (order by date_diff('day', l.l_commitdate, l.l_receiptdate)) as p90_delivery_delay,
            sum(case when l.l_receiptdate > l.l_commitdate then 1 else 0 end) as late_deliveries,
            sum(case when l.l_receiptdate <= l.l_commitdate then 1 else 0 end) as on_time_deliveries,
            sum(case when date_diff('day', l.l_commitdate, l.l_receiptdate) > 7 then 1 else 0 end) as severely_late_deliveries,
            sum(l.l_extendedprice * (1 - l.l_discount)) as total_revenue,
            sum(l.l_extendedprice * (1 - l.l_discount) * l.l_tax) as total_tax,
            sum(l.l_quantity) as total_quantity,
            avg(l.l_discount) as avg_discount_rate,
            max(l.l_discount) as max_discount_offered,
            stddev_samp(cast(l.l_extendedprice * (1 - l.l_discount) as double precision)) as revenue_volatility,
            var_pop(cast(l.l_extendedprice * (1 - l.l_discount) as double precision)) as revenue_variance,
            min(l.l_shipdate) as first_shipment_date,
            max(l.l_shipdate) as last_shipment_date,
            date_diff('day', min(l.l_shipdate), max(l.l_shipdate)) as active_days,
            count(distinct l.l_partkey) as unique_parts_shipped
        from supplier s
        join lineitem l on s.s_suppkey = l.l_suppkey
        group by s.s_suppkey, s.s_name, s.s_nationkey, s.s_acctbal, s.s_address, s.s_phone
    ),
    -- step 2: calculate supplier transaction frequency patterns
    supplier_transaction_frequency as (
        select
            l_suppkey,
            date_trunc('month', l_shipdate) as ship_month,
            count(*) as transactions_per_month,
            sum(l_quantity) as quantity_per_month,
            sum(l_extendedprice * (1 - l_discount)) as revenue_per_month,
            lag(count(*)) over (partition by l_suppkey order by date_trunc('month', l_shipdate)) as prev_month_transactions,
            lag(sum(l_quantity)) over (partition by l_suppkey order by date_trunc('month', l_shipdate)) as prev_month_quantity,
            lag(sum(l_extendedprice * (1 - l_discount))) over (partition by l_suppkey order by date_trunc('month', l_shipdate)) as prev_month_revenue,
            date_diff('month', lag(date_trunc('month', l_shipdate)) over (partition by l_suppkey order by date_trunc('month', l_shipdate)), date_trunc('month', l_shipdate)) as months_since_last_activity
        from lineitem
        group by l_suppkey, ship_month
    ),
    -- step 3: calculate seasonal ordering patterns (quarterly)
    seasonal_patterns_quarterly as (
        select
            l.l_suppkey,
            extract(quarter from o.o_orderdate) as quarter,
            extract(year from o.o_orderdate) as year,
            count(distinct o.o_orderkey) as quarterly_orders,
            count(distinct extract(month from o.o_orderdate)) as active_months_in_quarter,
            sum(l.l_quantity) as quarterly_quantity,
            sum(l.l_extendedprice * (1 - l.l_discount)) as quarterly_revenue,
            avg(l.l_extendedprice * (1 - l.l_discount)) as avg_order_value_in_quarter,
            count(distinct l.l_partkey) as unique_parts_in_quarter,
            lag(sum(l.l_quantity)) over (partition by l.l_suppkey, extract(quarter from o.o_orderdate) order by extract(year from o.o_orderdate)) as prev_year_quarterly_quantity,
            lag(sum(l.l_extendedprice * (1 - l.l_discount))) over (partition by l.l_suppkey, extract(quarter from o.o_orderdate) order by extract(year from o.o_orderdate)) as prev_year_quarterly_revenue
        from lineitem l
        join orders o on l.l_orderkey = o.o_orderkey
        group by l.l_suppkey, quarter, year
    ),
    -- step 4: calculate seasonal ordering patterns (monthly)
    seasonal_patterns_monthly as (
        select
            l.l_suppkey,
            extract(month from o.o_orderdate) as month,
            extract(year from o.o_orderdate) as year,
            count(distinct o.o_orderkey) as monthly_orders,
            sum(l.l_quantity) as monthly_quantity,
            sum(l.l_extendedprice * (1 - l.l_discount)) as monthly_revenue,
            lag(sum(l.l_quantity)) over (partition by l.l_suppkey, extract(month from o.o_orderdate) order by extract(year from o.o_orderdate)) as prev_year_monthly_quantity,
            lag(sum(l.l_extendedprice * (1 - l.l_discount))) over (partition by l.l_suppkey, extract(month from o.o_orderdate) order by extract(year from o.o_orderdate)) as prev_year_monthly_revenue
        from lineitem l
        join orders o on l.l_orderkey = o.o_orderkey
        group by l.l_suppkey, month, year
    ),
    -- step 5: calculate yoy growth and seasonality scores (quarterly)
    supplier_seasonality_quarterly as (
        select
            l_suppkey,
            quarter,
            year,
            quarterly_quantity,
            quarterly_revenue,
            unique_parts_in_quarter,
            active_months_in_quarter,
            case
                when prev_year_quarterly_quantity > 0 then (quarterly_quantity - prev_year_quarterly_quantity) / prev_year_quarterly_quantity * 100
                else null
            end as yoy_quantity_growth,
            case
                when prev_year_quarterly_revenue > 0 then (quarterly_revenue - prev_year_quarterly_revenue) / prev_year_quarterly_revenue * 100
                else null
            end as yoy_revenue_growth,
            dense_rank() over (partition by l_suppkey order by quarterly_quantity desc) as quantity_quarter_rank,
            dense_rank() over (partition by l_suppkey order by quarterly_revenue desc) as revenue_quarter_rank,
            quarterly_quantity / nullif(quarterly_orders, 0) as avg_quantity_per_order,
            quarterly_revenue / nullif(quarterly_orders, 0) as avg_revenue_per_order
        from seasonal_patterns_quarterly
    ),
    -- step 6: calculate yoy growth and seasonality scores (monthly)
    supplier_seasonality_monthly as (
        select
            l_suppkey,
            month,
            year,
            monthly_quantity,
            monthly_revenue,
            case
                when prev_year_monthly_quantity > 0 then (monthly_quantity - prev_year_monthly_quantity) / prev_year_monthly_quantity * 100
                else null
            end as yoy_quantity_growth_monthly,
            case
                when prev_year_monthly_revenue > 0 then (monthly_revenue - prev_year_monthly_revenue) / prev_year_monthly_revenue * 100
                else null
            end as yoy_revenue_growth_monthly,
            dense_rank() over (partition by l_suppkey order by monthly_quantity desc) as quantity_month_rank,
            dense_rank() over (partition by l_suppkey order by monthly_revenue desc) as revenue_month_rank
        from seasonal_patterns_monthly
    ),
    -- step 7: analyze parts supply chain diversification
    part_supplier_diversity as (
        select
            p.p_partkey,
            p.p_name,
            p.p_mfgr,
            p.p_brand,
            p.p_type,
            p.p_size,
            p.p_container,
            p.p_retailprice,
            count(distinct ps.ps_suppkey) as supplier_count,
            max(ps.ps_supplycost) / nullif(min(ps.ps_supplycost), 0) as cost_ratio,
            max(ps.ps_supplycost) - min(ps.ps_supplycost) as cost_spread,
            stddev_samp(cast(ps.ps_supplycost as double precision)) as cost_volatility,
            avg(ps.ps_supplycost) as avg_cost,
            min(ps.ps_supplycost) as min_cost,
            max(ps.ps_supplycost) as max_cost,
            avg(ps.ps_availqty) as avg_availability,
            sum(ps.ps_availqty) as total_availability,
            min(ps.ps_availqty) as min_availability,
            max(ps.ps_availqty) as max_availability,
            var_pop(cast(ps.ps_availqty as double precision)) as availability_variance
        from part p
        join partsupp ps on p.p_partkey = ps.ps_partkey
        group by p.p_partkey, p.p_name, p.p_mfgr, p.p_brand, p.p_type, p.p_size, p.p_container, p.p_retailprice
        having count(distinct ps.ps_suppkey) > 1
    ),
    -- step 8: analyze part categories and their supply chain characteristics
    part_category_analysis as (
        select
            split_part(p.p_type, ' ', 1) as part_category,
            count(distinct p.p_partkey) as category_part_count,
            avg(psd.supplier_count) as avg_suppliers_per_part,
            min(psd.supplier_count) as min_suppliers_per_part,
            max(psd.supplier_count) as max_suppliers_per_part,
            avg(psd.cost_ratio) as avg_cost_ratio,
            avg(psd.cost_volatility) as avg_cost_volatility,
            sum(p.p_retailprice * psd.total_availability) as category_inventory_value,
            count(distinct ps.ps_suppkey) as unique_suppliers_in_category
        from part p
        join part_supplier_diversity psd on p.p_partkey = psd.p_partkey
        join partsupp ps on p.p_partkey = ps.ps_partkey
        group by part_category
    ),
    -- step 9: geographic performance analysis (nation level)
    nation_performance as (
        select
            n.n_nationkey,
            n.n_name as nation,
            n.n_regionkey,
            count(distinct s.s_suppkey) as supplier_count,
            avg(sdm.avg_delivery_delay) as nation_avg_delay,
            percentile_cont(0.5) within group (order by sdm.avg_delivery_delay) as nation_median_delay,
            avg(sdm.p90_delivery_delay) as nation_p90_delay,
            sum(sdm.total_revenue) as nation_revenue,
            sum(sdm.total_quantity) as nation_quantity,
            sum(sdm.late_deliveries) / nullif(sum(sdm.total_orders), 0) * 100 as nation_late_delivery_pct,
            sum(sdm.severely_late_deliveries) / nullif(sum(sdm.total_orders), 0) * 100 as nation_severely_late_pct,
            avg(sdm.revenue_volatility) as nation_avg_rev_volatility,
            sum(sdm.unique_parts_shipped) as nation_unique_parts,
            count(distinct l.l_partkey) as nation_distinct_parts
        from supplier s
        join supplier_delivery_metrics sdm on s.s_suppkey = sdm.s_suppkey
        join nation n on s.s_nationkey = n.n_nationkey
        join lineitem l on s.s_suppkey = l.l_suppkey
        group by n.n_nationkey, n.n_name, n.n_regionkey
    ),
    -- step 10: geographic performance analysis (region level)
    region_performance as (
        select
            r.r_regionkey,
            r.r_name as region,
            count(distinct s.s_suppkey) as supplier_count,
            count(distinct n.n_nationkey) as nations_count,
            avg(np.nation_avg_delay) as region_avg_delay,
            avg(np.nation_median_delay) as region_median_delay,
            sum(np.nation_revenue) as region_revenue,
            sum(np.nation_quantity) as region_quantity,
            sum(np.nation_unique_parts) as region_unique_parts,
            avg(np.nation_late_delivery_pct) as region_late_delivery_pct,
            avg(np.nation_severely_late_pct) as region_severely_late_pct,
            avg(np.nation_avg_rev_volatility) as region_avg_rev_volatility,
            max(np.nation_revenue) / nullif(min(np.nation_revenue), 0) as nation_revenue_disparity,
            stddev_samp(cast(np.nation_late_delivery_pct as double precision)) as late_delivery_pct_stddev
        from region r
        join nation_performance np on r.r_regionkey = np.n_regionkey
        join nation n on np.n_nationkey = n.n_nationkey
        join supplier s on n.n_nationkey = s.s_nationkey
        group by r.r_regionkey, r.r_name
    ),
    -- step 11: customer satisfaction metrics via order lifecycle analysis
    customer_satisfaction as (
        select
            l.l_suppkey,
            o.o_custkey,
            count(distinct o.o_orderkey) as order_count,
            avg(date_diff('day', o.o_orderdate, l.l_receiptdate)) as avg_order_to_receipt,
            avg(o.o_totalprice) as avg_order_value,
            count(distinct case when l.l_returnflag = 'r' then l.l_orderkey end) as returned_orders,
            count(distinct case when l.l_returnflag = 'r' then l.l_orderkey end) / nullif(count(distinct o.o_orderkey), 0) * 100 as return_rate,
            avg(case when l.l_returnflag = 'r' then l.l_extendedprice * (1 - l.l_discount) else null end) as avg_return_value,
            count(distinct case when o.o_orderstatus = 'f' then o.o_orderkey end) / nullif(count(distinct o.o_orderkey), 0) * 100 as fulfillment_rate,
            count(distinct case when o.o_orderpriority like '1-%' or o.o_orderpriority like '2-%' then o.o_orderkey end) as high_priority_orders,
            count(distinct case when o.o_orderpriority like '1-%' or o.o_orderpriority like '2-%' then o.o_orderkey end) / nullif(count(distinct o.o_orderkey), 0) * 100 as high_priority_percentage
        from lineitem l
        join orders o on l.l_orderkey = o.o_orderkey
        group by l.l_suppkey, o.o_custkey
    ),
    -- step 12: supplier customer diversity and loyalty analysis
    supplier_customer_analysis as (
        select
            cs.l_suppkey,
            count(distinct cs.o_custkey) as unique_customers,
            avg(cs.order_count) as avg_orders_per_customer,
            max(cs.order_count) as max_orders_from_customer,
            min(cs.order_count) as min_orders_from_customer,
            stddev_samp(cast(cs.order_count as double precision)) as order_count_stddev,
            count(distinct case when cs.order_count > 5 then cs.o_custkey else null end) as loyal_customers,
            count(distinct case when cs.order_count > 5 then cs.o_custkey else null end) / nullif(count(distinct cs.o_custkey), 0) * 100 as loyal_customer_percentage,
            avg(cs.return_rate) as avg_return_rate,
            max(cs.return_rate) as max_return_rate,
            avg(cs.avg_order_value) as avg_customer_order_value,
            max(cs.avg_order_value) as max_customer_order_value,
            min(cs.avg_order_value) as min_customer_order_value,
            count(distinct case when cs.high_priority_percentage > 50 then cs.o_custkey else null end) as high_priority_customers,
            count(distinct case when cs.high_priority_percentage > 50 then cs.o_custkey else null end) / nullif(count(distinct cs.o_custkey), 0) * 100 as high_priority_customer_percentage
        from customer_satisfaction cs
        group by cs.l_suppkey
    ),
    -- step 13: calculate risk scores for each supplier
    supplier_risk_scores as (
        select
            sdm.s_suppkey,
            sdm.s_name,
            sdm.s_acctbal,
            sdm.total_orders,
            sdm.total_revenue,
            sdm.total_quantity,
            sdm.late_deliveries / nullif(sdm.total_orders, 0) * 100 as late_delivery_pct,
            sdm.severely_late_deliveries / nullif(sdm.total_orders, 0) * 100 as severely_late_pct,
            sdm.on_time_deliveries / nullif(sdm.total_orders, 0) * 100 as on_time_delivery_pct,
            sdm.avg_delivery_delay,
            sdm.median_delivery_delay,
            sdm.p90_delivery_delay,
            (select coalesce(stddev_samp(cast(revenue_volatility as double precision)), 0)
             from supplier_delivery_metrics sdm_inner
             where sdm_inner.s_suppkey = sdm.s_suppkey) as normalized_volatility,
            sdm.active_days,
            sdm.unique_parts_shipped,
            sdm.avg_discount_rate,
            sdm.max_discount_offered,
            sca.unique_customers,
            sca.loyal_customer_percentage,
            sca.avg_return_rate,
            -- delivery risk score
            (sdm.late_deliveries / nullif(sdm.total_orders, 0) * 40) +
            (sdm.severely_late_deliveries / nullif(sdm.total_orders, 0) * 60) +
            (case when sdm.avg_delivery_delay > 0 then log(10, sdm.avg_delivery_delay + 1) * 10 else 0 end) +
            (case when sdm.p90_delivery_delay > 10 then log(10, sdm.p90_delivery_delay) * 5 else 0 end) as delivery_risk_score,
            -- financial risk score
            ((select coalesce(stddev_samp(cast(revenue_volatility as double precision)), 0)
              from supplier_delivery_metrics sdm_inner
              where sdm_inner.s_suppkey = sdm.s_suppkey) * 20) +
            (case when sdm.s_acctbal < 0 then abs(sdm.s_acctbal) / 1000 * 5 else 0 end) +
            (case when sdm.total_orders < 10 then 20 else 0 end) +
            (case when sdm.active_days < 365 then (365 - sdm.active_days) / 3.65 else 0 end) +
            (case when stf.months_since_last_activity is null or stf.months_since_last_activity > 6 then 30 else stf.months_since_last_activity * 5 end) as financial_risk_score,
            -- diversification risk score
            (case when sdm.unique_parts_shipped < 5 then (5 - sdm.unique_parts_shipped) * 10 else 0 end) +
            (case when sca.unique_customers < 5 then (5 - sca.unique_customers) * 10 else 0 end) +
            (case when sca.loyal_customer_percentage < 30 then (30 - sca.loyal_customer_percentage) else 0 end) as diversification_risk_score,
            -- quality risk score
            (sca.avg_return_rate * 5) +
            (case when sca.max_return_rate > 30 then (sca.max_return_rate - 30) * 2 else 0 end) as quality_risk_score
        from supplier_delivery_metrics sdm
        join supplier_customer_analysis sca on sdm.s_suppkey = sca.l_suppkey
        left join (
            select
                l_suppkey,
                min(months_since_last_activity) as months_since_last_activity
            from supplier_transaction_frequency
            where months_since_last_activity is not null
            group by l_suppkey
        ) stf on sdm.s_suppkey = stf.l_suppkey
    ),
    -- step 14: aggregate seasonal insights per supplier (quarterly)
    supplier_seasonality_quarterly_agg as (
        select
            ssq.l_suppkey,
            max(case when ssq.quantity_quarter_rank = 1 then ssq.quarter else null end) as peak_quantity_quarter,
            max(case when ssq.revenue_quarter_rank = 1 then ssq.quarter else null end) as peak_revenue_quarter,
            avg(case when ssq.yoy_quantity_growth is not null then abs(ssq.yoy_quantity_growth) else null end) as avg_quantity_volatility,
            avg(case when ssq.yoy_revenue_growth is not null then abs(ssq.yoy_revenue_growth) else null end) as avg_revenue_volatility,
            max(ssq.yoy_revenue_growth) as max_revenue_growth,
            min(ssq.yoy_revenue_growth) as min_revenue_growth,
            avg(ssq.unique_parts_in_quarter) as avg_unique_parts_per_quarter,
            max(ssq.active_months_in_quarter) as max_active_months_in_quarter,
            avg(ssq.avg_quantity_per_order) as overall_avg_quantity_per_order,
            avg(ssq.avg_revenue_per_order) as overall_avg_revenue_per_order,
            stddev(cast(ssq.quarterly_revenue as double precision)) / nullif(avg(ssq.quarterly_revenue), 0) * 100 as revenue_coefficient_of_variation
        from supplier_seasonality_quarterly ssq
        group by ssq.l_suppkey
    ),
    -- step 15: aggregate seasonal insights per supplier (monthly)
    supplier_seasonality_monthly_agg as (
        select
            ssm.l_suppkey,
            max(case when ssm.quantity_month_rank = 1 then ssm.month else null end) as peak_quantity_month,
            max(case when ssm.revenue_month_rank = 1 then ssm.month else null end) as peak_revenue_month,
            avg(case when ssm.yoy_quantity_growth_monthly is not null then abs(ssm.yoy_quantity_growth_monthly) else null end) as avg_monthly_quantity_volatility,
            avg(case when ssm.yoy_revenue_growth_monthly is not null then abs(ssm.yoy_revenue_growth_monthly) else null end) as avg_monthly_revenue_volatility,
            max(ssm.yoy_revenue_growth_monthly) as max_monthly_revenue_growth,
            min(ssm.yoy_revenue_growth_monthly) as min_monthly_revenue_growth,
            stddev(cast(ssm.monthly_revenue as double precision)) / nullif(avg(ssm.monthly_revenue), 0) * 100 as monthly_revenue_coefficient_of_variation
        from supplier_seasonality_monthly ssm
        group by ssm.l_suppkey
    ),
    -- step 16: parts supplied analysis
    supplier_parts_profile as (
        select
            ps.ps_suppkey,
            count(distinct ps.ps_partkey) as unique_parts_supplied,
            count(distinct p.p_mfgr) as manufacturer_count,
            count(distinct p.p_brand) as brand_count,
            count(distinct split_part(p.p_type, ' ', 1)) as part_category_count,
            avg(ps.ps_supplycost) as avg_supply_cost,
            min(ps.ps_supplycost) as min_supply_cost,
            max(ps.ps_supplycost) as max_supply_cost,
            stddev_samp(cast(ps.ps_supplycost as double precision)) as supply_cost_stddev,
            sum(ps.ps_availqty) as total_availability,
            min(ps.ps_availqty) as min_availability,
            max(ps.ps_availqty) as max_availability,
            avg(ps.ps_availqty) as avg_availability,
            stddev_samp(cast(ps.ps_availqty as double precision)) as availability_stddev,
            avg(ps.ps_availqty * p.p_retailprice) as avg_inventory_value,
            sum(ps.ps_availqty * p.p_retailprice) as total_inventory_value,
            count(distinct split_part(p.p_type, ' ', 1)) as category_diversity,
            avg(case when psd.supplier_count is not null then psd.supplier_count else 1 end) as avg_supply_chain_redundancy,
            sum(case when p.p_retailprice > 1000 then 1 else 0 end) / nullif(count(*), 0) * 100 as premium_part_percentage,
            sum(ps.ps_availqty) / nullif((select sum(l_quantity) from lineitem where l_suppkey = ps.ps_suppkey), 0) as inventory_turnover_ratio
        from partsupp ps
        join part p on ps.ps_partkey = p.p_partkey
        left join part_supplier_diversity psd on p.p_partkey = psd.p_partkey
        group by ps.ps_suppkey
    ),
    -- step 17: text analysis of supplier comments
    supplier_comment_analysis as (
        select
            s_suppkey,
            s_comment,
            length(s_comment) as comment_length,
            array_length(
              regexp_extract_all(
                lower(s_comment),
                '(quality|reliable|good|excellent|best|quick|fast|prompt|timely|superior)'
              )
            )::integer as positive_mentions,
            array_length(
              regexp_extract_all(
                lower(s_comment),
                '(delay|issue|problem|complaint|late|bad|slow|poor|dissatisfied|disappointed)'
              )
            )::integer as negative_mentions,
            case
                when
                  array_length(regexp_extract_all(lower(s_comment), '(quality|reliable|good|excellent)')) >
                  array_length(regexp_extract_all(lower(s_comment), '(delay|issue|problem)'))
                then 'positive'
                else 'negative'
            end as sentiment,
            array_length(
              regexp_extract_all(lower(s_comment), '(price|cost|discount|rate|value|expense)')
            )::integer as financial_mentions,
            array_length(
              regexp_extract_all(lower(s_comment), '(ship|deliver|transport|carry|move|logistics)')
            )::integer as logistics_mentions,
            array_length(
              regexp_extract_all(lower(s_comment), '(part|item|product|stock|component|material)')
            )::integer as product_mentions
        from supplier
    ),
    -- step 18: final supplier performance report
    final_supplier_report as (
        select
            sdm.s_suppkey,
            any_value(sdm.s_name) as s_name,
            any_value(sdm.s_nationkey) as s_nationkey,
            any_value(sdm.s_acctbal) as s_acctbal,
            any_value(sdm.s_address) as s_address,
            any_value(sdm.s_phone) as s_phone,
            max(sdm.total_orders) as total_orders,
            avg(sdm.avg_delivery_delay) as avg_delivery_delay,
            percentile_cont(0.5) within group (order by sdm.median_delivery_delay) as median_delivery_delay,
            percentile_cont(0.90) within group (order by sdm.p90_delivery_delay) as p90_delivery_delay,
            sum(sdm.late_deliveries) as late_deliveries,
            sum(sdm.on_time_deliveries) as on_time_deliveries,
            sum(sdm.severely_late_deliveries) as severely_late_deliveries,
            sum(sdm.total_revenue) as total_revenue,
            sum(sdm.total_tax) as total_tax,
            sum(sdm.total_quantity) as total_quantity,
            avg(sdm.avg_discount_rate) as avg_discount_rate,
            max(sdm.max_discount_offered) as max_discount_offered,
            var_pop(cast(sdm.revenue_volatility as double precision)) as revenue_variance,
            min(sdm.first_shipment_date) as first_shipment_date,
            max(sdm.last_shipment_date) as last_shipment_date,
            max(sdm.active_days) as active_days,
            count(distinct sdm.unique_parts_shipped) as unique_parts_shipped,
            avg(stf.transactions_per_month) as avg_transactions_per_month,
            coalesce(sum(stf.quantity_per_month), 0) as total_quantity_per_month,
            coalesce(sum(stf.revenue_per_month), 0) as total_revenue_per_month,
            max(ssq_agg.peak_quantity_quarter) as peak_quantity_quarter,
            max(ssq_agg.peak_revenue_quarter) as peak_revenue_quarter,
            avg(ssq_agg.avg_quantity_volatility) as avg_quantity_volatility,
            avg(ssq_agg.avg_revenue_volatility) as avg_revenue_volatility,
            max(srs.delivery_risk_score) as delivery_risk_score,
            avg(srs.financial_risk_score) as financial_risk_score,
            max(spp.unique_parts_supplied) as unique_parts_supplied,
            any_value(sca.sentiment) as sentiment,
            avg(sca.comment_length) as avg_comment_length
        from supplier_delivery_metrics sdm
        left join supplier_transaction_frequency stf
            on sdm.s_suppkey = stf.l_suppkey
        left join supplier_seasonality_quarterly_agg ssq_agg
            on sdm.s_suppkey = ssq_agg.l_suppkey
        left join supplier_seasonality_monthly_agg ssm_agg
            on sdm.s_suppkey = ssm_agg.l_suppkey
        left join supplier_risk_scores srs
            on sdm.s_suppkey = srs.s_suppkey
        left join supplier_parts_profile spp
            on sdm.s_suppkey = spp.ps_suppkey
        left join supplier_comment_analysis sca
            on sdm.s_suppkey = sca.s_suppkey
        group by sdm.s_suppkey
    )
    select * from final_supplier_report limit 1000;

        """)
]
