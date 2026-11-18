from dotenv import load_dotenv
import os

load_dotenv()

queries = [
    ("query-1", f"""
        select
            sum(l_extendedprice) as sum
        from lineitem;
        """),
    ("query-2", f"""
        select
            count(*) as count_of_line_items,
            sum(lineitem::%l_extendedprice) as sum,
            avg(lineitem::%l_discount) as avg,
            min(cast(lineitem::$l_shipdate as datetime)) as min,
            max(cast(lineitem::$l_receiptdate as datetime)) as max
        from jlineitem;
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
        from lineitem
        order by l_orderkey, l_linenumber limit 1000;
        """),
    ("query-4", f"""
        with base_table as (
            select
                date_format(cast(li.lineitem::$l_shipdate as datetime), '%y-%m') as ship_year_month,
                li.lineitem::$l_shipmode as l_shipmode,
                ord.orders::$o_orderpriority as order_priority,
                count(*) as count_of_line_items,
                sum(li.lineitem::%l_extendedprice) as sum,
                avg(li.lineitem::%l_discount) as avg
            from jlineitem li
            left join jorders ord
                on json_extract_bigint(li.lineitem, '$.l_orderkey') = json_extract_bigint(ord.orders, '$.o_orderkey')
            group by
                date_format(cast(li.lineitem::$l_shipdate as datetime), '%y-%m'),
                li.lineitem::$l_shipmode,
                ord.orders::$o_orderpriority
        )
        select
            base_table.*,
            row_number() over (partition by base_table.order_priority order by base_table.sum) as row_number_by_order_priority,
            row_number() over (partition by base_table.l_shipmode order by base_table.avg) as row_number_by_ship_mode
        from base_table
        limit 1000;
    """),
    ("query-5", f"""
        with customer_sales as (
            select
                date_format(o.o_orderdate, '%y - %m') as order_month,
                c.c_name,
                sum(o.o_totalprice) as total_spent,
                sum(l.l_quantity) as total_quantity,
                rank() over (partition by date_format(o.o_orderdate, '%y - %m') order by sum(o.o_totalprice) desc) as price_rank,
                rank() over (partition by date_format(o.o_orderdate, '%y - %m') order by sum(l.l_quantity) desc) as quantity_rank
            from orders o
            join lineitem l on o.o_orderkey = l.l_orderkey
            join customer c on o.o_custkey = c.c_custkey
            group by order_month, c.c_name
        )
        select order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
        from customer_sales
        where price_rank <= 3 or quantity_rank <= 3
        order by order_month, price_rank, quantity_rank limit 1000;
        """),
    ("query-6", f"""
        with combined_comments as (
            select
                date_format(o.o_orderdate, '%y - %m') as order_month,
                lower(trim(regexp_replace(o.o_comment, '[^a-za-z0-9 ]', ''))) as cleaned_comment
            from orders o
            union all
            select
                date_format(o.o_orderdate, '%y - %m') as order_month,
                lower(trim(regexp_replace(l.l_comment, '[^a-za-z0-9 ]', ''))) as cleaned_comment
            from lineitem l
            join orders o
                on l.l_orderkey = o.o_orderkey
        ),
        numbers as (
            select row_number() over () - 1 as n
            from (select 1 union all select 2 union all select 3 union all select 4 union all select 5 union all
                  select 6 union all select 7 union all select 8 union all select 9 union all select 10) as t
        ),
        tokenized_words as (
            select
                cc.order_month,
                trim(substring_index(substring_index(cc.cleaned_comment, ' ', n + 1), ' ', -1)) as word
            from combined_comments cc
            join numbers n
            where n.n < (length(cc.cleaned_comment) - length(replace(cc.cleaned_comment, ' ', '')) + 1)
                and trim(substring_index(substring_index(cc.cleaned_comment, ' ', n + 1), ' ', -1)) != ''
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
        with customer_sales as (
            select
                date_format(o.o_orderdate, '%y - %m') as order_month,
                c.c_name,
                sum(o.o_totalprice) as total_spent,
                sum(l.l_quantity) as total_quantity,
                rank() over (partition by date_format(o.o_orderdate, '%y - %m') order by sum(o.o_totalprice) desc) as price_rank,
                rank() over (partition by date_format(o.o_orderdate, '%y - %m') order by sum(l.l_quantity) desc) as quantity_rank
            from orders o
            join lineitem l on o.o_orderkey = l.l_orderkey
            join customer c on o.o_custkey = c.c_custkey
            group by order_month, c.c_name
        ),
        number_extraction as (
            select *,
                   regexp_replace(c_name, '[^0-9]', '') as customer_number
            from customer_sales
        ),
        numbers as (
            select 0 as n union all select 1 union all select 2 union all select 3 union all select 4 union all
            select 5 union all select 6 union all select 7 union all select 8 union all select 9
        ),
        digit_sum_calc as (
            select
                ne.order_month, ne.c_name, ne.total_spent, ne.total_quantity, ne.price_rank, ne.quantity_rank, ne.customer_number,
                sum(cast(substring(ne.customer_number, n.n + 1, 1) as signed)) as number_sum
            from number_extraction ne
            join numbers n
            on n.n < length(ne.customer_number)
            group by ne.order_month, ne.c_name, ne.total_spent, ne.total_quantity, ne.price_rank, ne.quantity_rank, ne.customer_number
        )
        select order_month, c_name, total_spent, total_quantity, price_rank, quantity_rank
        from digit_sum_calc
        where (price_rank <= 3 or quantity_rank <= 3)
        and mod(number_sum, 2) = 1
        order by order_month, price_rank, quantity_rank
        limit 1000;
    """),
    ("query-8", f"""
        with order_comments as (
            select
                c.c_custkey,
                c.c_name,
                lower(trim(regexp_replace(o.o_comment, '[^a-za-z0-9 ]', ''))) as cleaned_comment,
                case
                    when length(o.o_comment) > 100 then 'long_comment'
                    else 'short_comment'
                end as comment_type
            from orders o
            join customer c on o.o_custkey = c.c_custkey
        ),
        lineitem_comments as (
            select
                c.c_custkey,
                c.c_name,
                lower(trim(regexp_replace(l.l_comment, '[^a-za-z0-9 ]', ''))) as cleaned_comment,
                case
                    when length(l.l_comment) > 100 then 'long_comment'
                    else 'short_comment'
                end as comment_type
            from lineitem l
            join orders o on l.l_orderkey = o.o_orderkey
            join customer c on o.o_custkey = c.c_custkey
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
            group_concat(rc.cleaned_comment || ' (' || rc.comment_type || ')' order by rc.comment_rank separator ' | ') as customer_comments,
            max(rc.total_comments) as total_comments_per_customer
        from ranked_comments rc
        where rc.comment_rank <= 5
        group by rc.c_custkey, rc.c_name
        order by total_comments_per_customer desc limit 1000;
    """),
    ("query-9", f"""
        with customer_orders as (
            select
                c.c_custkey,
                c.c_name,
                o.o_orderdate,
                sum(l.l_extendedprice * (1 - l.l_discount)) as total_revenue,
                count(*) as order_count,
                row_number() over (partition by c.c_custkey order by o.o_orderdate asc) as order_rank
            from customer c
            join orders o on c.c_custkey = o.o_custkey
            join lineitem l on o.o_orderkey = l.l_orderkey
            where o.o_orderdate >= date_sub(current_date, interval 30 year)
              and l.l_shipdate > o.o_orderdate
            group by c.c_custkey, c.c_name, o.o_orderdate
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
                date_format(o_orderdate, '%y-%m-01') as order_month,
                count(*) as monthly_orders,
                sum(total_revenue) as monthly_revenue
            from cumulative_revenue
            group by c_custkey, c_name, date_format(o_orderdate, '%y-%m-01')
        )
        select
            m.c_custkey,
            m.c_name,
            group_concat(
                concat('month: ', date_format(order_month, '%y-%m'),
                ', orders: ', monthly_orders,
                ', revenue: ', format(monthly_revenue, 2))
                order by order_month separator ' | '
            ) as monthly_summary,
            max(c.cumulative_revenue) as lifetime_revenue
        from monthly_analysis m
        join cumulative_revenue c on m.c_custkey = c.c_custkey
        group by m.c_custkey, m.c_name
        order by lifetime_revenue desc
        limit 1000;
        """),
    ("query-10", f"""
        with customer_orders as (
            select
                c.c_custkey,
                c.c_name,
                o.o_orderdate,
                count(*) as total_orders,
                sum(l.l_extendedprice * (1 - l.l_discount)) as total_revenue,
                sum(case when l.l_shipdate <= date_add(o.o_orderdate, interval 30 day) then 1 else 0 end) as shipped_orders
            from customer c
            join orders o on c.c_custkey = o.o_custkey
            join lineitem l on o.o_orderkey = l.l_orderkey
            where o.o_orderdate >= date_sub(current_date, interval 30 year)
            group by c.c_custkey, c.c_name, o.o_orderdate
        ),
        customer_metrics as (
            select
                c_custkey,
                c_name,
                sum(total_orders) as total_orders_per_customer,
                sum(total_revenue) as total_revenue_per_customer,
                sum(shipped_orders) as total_shipped_orders_per_customer,
                avg(total_revenue / nullif(total_orders, 0)) as avg_revenue_per_order
            from customer_orders
            group by c_custkey, c_name
        ),
        customer_ratios as (
            select
                c_custkey,
                c_name,
                total_orders_per_customer,
                total_revenue_per_customer,
                total_shipped_orders_per_customer,
                avg_revenue_per_order,
                1.0 * total_shipped_orders_per_customer / nullif(total_orders_per_customer, 0) as shipped_ratio
            from customer_metrics
        )
        select
            c_custkey,
            c_name,
            total_orders_per_customer,
            total_revenue_per_customer,
            avg_revenue_per_order,
            shipped_ratio * 100 as shipped_percentage
        from customer_ratios
        where shipped_ratio > 0.5
        order by avg_revenue_per_order desc
        limit 1000;
        """),
    ("query-11", f"""
        select
            json_extract_json(o.orders, '$.o_orderkey') as orderkey,
            json_extract_json(o.orders, '$.o_orderdate') as orderdate,
            json_extract_json(o.orders, '$.o_totalprice') as totalprice,
            li.total_revenue,
            li.avg_discount
        from (
            select
                json_extract_json(lineitem, '$.l_orderkey') as orderkey,
                sum(json_extract_json(lineitem, '$.l_extendedprice') *
                    (1 - json_extract_json(lineitem, '$.l_discount'))) as total_revenue,
                avg(json_extract_json(lineitem, '$.l_discount')) as avg_discount
            from jlineitem
            group by json_extract_json(lineitem, '$.l_orderkey')
        ) as li
        join jorders as o
            on li.orderkey = json_extract_json(o.orders, '$.o_orderkey')
        where li.total_revenue > 50000
        and li.avg_discount < 0.05
        order by li.total_revenue desc
        limit 1000;
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
                avg(datediff(l.l_receiptdate, l.l_commitdate)) as avg_delivery_delay,
                avg(datediff(l.l_receiptdate, l.l_commitdate)) as median_delivery_delay,
                avg(datediff(l.l_receiptdate, l.l_commitdate)) + 1.28 * stddev(datediff(l.l_receiptdate, l.l_commitdate)) as p90_delivery_delay,
                sum(case when l.l_receiptdate > l.l_commitdate then 1 else 0 end) as late_deliveries,
                sum(case when l.l_receiptdate <= l.l_commitdate then 1 else 0 end) as on_time_deliveries,
                sum(case when datediff(l.l_receiptdate, l.l_commitdate) > 7 then 1 else 0 end) as severely_late_deliveries,
                sum(l.l_extendedprice * (1 - l.l_discount)) as total_revenue,
                sum(l.l_extendedprice * (1 - l.l_discount) * l.l_tax) as total_tax,
                sum(l.l_quantity) as total_quantity,
                avg(l.l_discount) as avg_discount_rate,
                max(l.l_discount) as max_discount_offered,
                stddev(l.l_extendedprice * (1 - l.l_discount)) as revenue_volatility,
                variance(l.l_extendedprice * (1 - l.l_discount)) as revenue_variance,
                min(l.l_shipdate) as first_shipment_date,
                max(l.l_shipdate) as last_shipment_date,
                datediff(max(l.l_shipdate), min(l.l_shipdate)) as active_days,
                count(distinct l.l_partkey) as unique_parts_shipped
            from supplier s
            join lineitem l on s.s_suppkey = l.l_suppkey
            group by s.s_suppkey, s.s_name, s.s_nationkey, s.s_acctbal, s.s_address, s.s_phone
        ),
        -- step 2: calculate supplier transaction frequency patterns
        supplier_transaction_frequency as (
            select
                l_suppkey,
                date_format(l_shipdate, '%y-%m-01') as ship_month,
                count(*) as transactions_per_month,
                sum(l_quantity) as quantity_per_month,
                sum(l_extendedprice * (1 - l_discount)) as revenue_per_month,
                lag(count(*)) over (partition by l_suppkey order by date_format(l_shipdate, '%y-%m-01')) as prev_month_transactions,
                lag(sum(l_quantity)) over (partition by l_suppkey order by date_format(l_shipdate, '%y-%m-01')) as prev_month_quantity,
                lag(sum(l_extendedprice * (1 - l_discount))) over (partition by l_suppkey order by date_format(l_shipdate, '%y-%m-01')) as prev_month_revenue,
                timestampdiff(month,
                    lag(date_format(l_shipdate, '%y-%m-01')) over (partition by l_suppkey order by date_format(l_shipdate, '%y-%m-01')),
                    date_format(l_shipdate, '%y-%m-01')
                ) as months_since_last_activity
            from lineitem
            group by l_suppkey, ship_month
        ),
        -- step 3: calculate seasonal ordering patterns (quarterly)
        seasonal_patterns_quarterly as (
            select
                l.l_suppkey,
                quarter(o.o_orderdate) as quarter,
                year(o.o_orderdate) as year,
                count(distinct o.o_orderkey) as quarterly_orders,
                count(distinct month(o.o_orderdate)) as active_months_in_quarter,
                sum(l.l_quantity) as quarterly_quantity,
                sum(l.l_extendedprice * (1 - l.l_discount)) as quarterly_revenue,
                avg(l.l_extendedprice * (1 - l.l_discount)) as avg_order_value_in_quarter,
                count(distinct l.l_partkey) as unique_parts_in_quarter,
                lag(sum(l.l_quantity)) over (partition by l.l_suppkey, quarter(o.o_orderdate) order by year(o.o_orderdate)) as prev_year_quarterly_quantity,
                lag(sum(l.l_extendedprice * (1 - l.l_discount))) over (partition by l.l_suppkey, quarter(o.o_orderdate) order by year(o.o_orderdate)) as prev_year_quarterly_revenue
            from lineitem l
            join orders o on l.l_orderkey = o.o_orderkey
            group by l.l_suppkey, quarter, year
        ),
        -- step 4: calculate seasonal ordering patterns (monthly)
        seasonal_patterns_monthly as (
            select
                l.l_suppkey,
                month(o.o_orderdate) as month,
                year(o.o_orderdate) as year,
                count(distinct o.o_orderkey) as monthly_orders,
                sum(l.l_quantity) as monthly_quantity,
                sum(l.l_extendedprice * (1 - l.l_discount)) as monthly_revenue,
                lag(sum(l.l_quantity)) over (partition by l.l_suppkey, month(o.o_orderdate) order by year(o.o_orderdate)) as prev_year_monthly_quantity,
                lag(sum(l.l_extendedprice * (1 - l.l_discount))) over (partition by l.l_suppkey, month(o.o_orderdate) order by year(o.o_orderdate)) as prev_year_monthly_revenue
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
                stddev(ps.ps_supplycost) as cost_volatility,
                avg(ps.ps_supplycost) as avg_cost,
                min(ps.ps_supplycost) as min_cost,
                max(ps.ps_supplycost) as max_cost,
                avg(ps.ps_availqty) as avg_availability,
                sum(ps.ps_availqty) as total_availability,
                min(ps.ps_availqty) as min_availability,
                max(ps.ps_availqty) as max_availability,
                variance(ps.ps_availqty) as availability_variance
            from part p
            join partsupp ps on p.p_partkey = ps.ps_partkey
            group by p.p_partkey, p.p_name, p.p_mfgr, p.p_brand, p.p_type, p.p_size, p.p_container, p.p_retailprice
            having count(distinct ps.ps_suppkey) > 1
        ),
        -- step 8: analyze part categories and their supply chain characteristics
        part_category_analysis as (
            select
                substring_index(p.p_type, ' ', 1) as part_category,
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
                avg(sdm.median_delivery_delay) as nation_median_delay,
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
                stddev(np.nation_late_delivery_pct) as late_delivery_pct_stddev
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
                avg(datediff(l.l_receiptdate, o.o_orderdate)) as avg_order_to_receipt,
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
                stddev(cs.order_count) as order_count_stddev,
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
                sdm.revenue_volatility,
                sdm.revenue_volatility / nullif(sdm.total_revenue / sdm.total_orders, 0) as normalized_volatility,
                sdm.active_days,
                sdm.unique_parts_shipped,
                sdm.avg_discount_rate,
                sdm.max_discount_offered,
                sca.unique_customers,
                sca.loyal_customer_percentage,
                sca.avg_return_rate,
                -- risk components:
                -- delivery risk score (higher is worse): 0-100
                (sdm.late_deliveries / nullif(sdm.total_orders, 0) * 40) +
                (sdm.severely_late_deliveries / nullif(sdm.total_orders, 0) * 60) +
                (case when sdm.avg_delivery_delay > 0 then log10(sdm.avg_delivery_delay + 1) * 10 else 0 end) +
                (case when sdm.p90_delivery_delay > 10 then log10(sdm.p90_delivery_delay) * 5 else 0 end) as delivery_risk_score,
                -- financial risk score (higher is worse): 0-100
                (sdm.revenue_volatility / nullif(sdm.total_revenue / sdm.total_orders, 0) * 20) +
                (case when sdm.s_acctbal < 0 then abs(sdm.s_acctbal) / 1000 * 5 else 0 end) +
                (case when sdm.total_orders < 10 then 20 else 0 end) +
                (case when sdm.active_days < 365 then (365 - sdm.active_days) / 3.65 else 0 end) +
                (case when stf.months_since_last_activity is null or stf.months_since_last_activity > 6 then 30 else stf.months_since_last_activity * 5 end) as financial_risk_score,
                -- diversification risk score (higher is worse): 0-100
                (case when sdm.unique_parts_shipped < 5 then (5 - sdm.unique_parts_shipped) * 10 else 0 end) +
                (case when sca.unique_customers < 5 then (5 - sca.unique_customers) * 10 else 0 end) +
                (case when sca.loyal_customer_percentage < 30 then (30 - sca.loyal_customer_percentage) else 0 end) as diversification_risk_score,
                -- quality risk score (higher is worse): 0-100
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
                stddev(ssq.quarterly_revenue) / nullif(avg(ssq.quarterly_revenue), 0) * 100 as revenue_coefficient_of_variation
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
                stddev(ssm.monthly_revenue) / nullif(avg(ssm.monthly_revenue), 0) * 100 as monthly_revenue_coefficient_of_variation
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
                count(distinct substring_index(p.p_type, ' ', 1)) as part_category_count,
                avg(ps.ps_supplycost) as avg_supply_cost,
                min(ps.ps_supplycost) as min_supply_cost,
                max(ps.ps_supplycost) as max_supply_cost,
                stddev(ps.ps_supplycost) as supply_cost_stddev,
                sum(ps.ps_availqty) as total_availability,
                min(ps.ps_availqty) as min_availability,
                max(ps.ps_availqty) as max_availability,
                avg(ps.ps_availqty) as avg_availability,
                stddev(ps.ps_availqty) as availability_stddev,
                avg(ps.ps_availqty * p.p_retailprice) as avg_inventory_value,
                sum(ps.ps_availqty * p.p_retailprice) as total_inventory_value,
                -- parts category diversity
                count(distinct substring(p.p_type, 1, locate(' ', p.p_type))) as category_diversity,
                -- average supply chain redundancy for parts supplied
                avg(case when psd.supplier_count is not null then psd.supplier_count else 1 end) as avg_supply_chain_redundancy,
                -- premium category percentage
                sum(case when p.p_retailprice > 1000 then 1 else 0 end) / nullif(count(*), 0) * 100 as premium_part_percentage,
                -- inventory turnover potential (based on historic lineitem volume)
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
                (length(s_comment) - length(replace(lower(s_comment), 'quality', ''))) / length('quality') +
                (length(s_comment) - length(replace(lower(s_comment), 'reliable', ''))) / length('reliable') +
                (length(s_comment) - length(replace(lower(s_comment), 'good', ''))) / length('good') +
                (length(s_comment) - length(replace(lower(s_comment), 'excellent', ''))) / length('excellent') +
                (length(s_comment) - length(replace(lower(s_comment), 'best', ''))) / length('best') as positive_mentions,
                (length(s_comment) - length(replace(lower(s_comment), 'problem', ''))) / length('problem') +
                (length(s_comment) - length(replace(lower(s_comment), 'complaint', ''))) / length('complaint') +
                (length(s_comment) - length(replace(lower(s_comment), 'late', ''))) / length('late') as negative_mentions,
                case
                    when ((length(s_comment) - length(replace(lower(s_comment), 'quality', ''))) / length('quality') +
                         (length(s_comment) - length(replace(lower(s_comment), 'reliable', ''))) / length('reliable')) >
                         ((length(s_comment) - length(replace(lower(s_comment), 'delay', ''))) / length('delay') +
                         (length(s_comment) - length(replace(lower(s_comment), 'issue', ''))) / length('issue'))
                    then 'positive'
                    when ((length(s_comment) - length(replace(lower(s_comment), 'quality', ''))) / length('quality') +
                         (length(s_comment) - length(replace(lower(s_comment), 'reliable', ''))) / length('reliable')) <
                         ((length(s_comment) - length(replace(lower(s_comment), 'delay', ''))) / length('delay') +
                         (length(s_comment) - length(replace(lower(s_comment), 'issue', ''))) / length('issue'))
                    then 'negative'
                    else 'neutral'
                end as sentiment,
                -- additional text analytics
                (length(s_comment) - length(replace(lower(s_comment), 'price', ''))) / length('price') +
                (length(s_comment) - length(replace(lower(s_comment), 'cost', ''))) / length('cost') as financial_mentions,
                (length(s_comment) - length(replace(lower(s_comment), 'ship', ''))) / length('ship') +
                (length(s_comment) - length(replace(lower(s_comment), 'deliver', ''))) / length('deliver') as logistics_mentions,
                (length(s_comment) - length(replace(lower(s_comment), 'part', ''))) / length('part') +
                (length(s_comment) - length(replace(lower(s_comment), 'item', ''))) / length('item') as product_mentions
            from supplier
        ),
        -- step 18: final supplier performance report
        final_supplier_report as (
            select
                sdm.s_suppkey,
                sdm.s_name,
                sdm.s_nationkey,
                sdm.s_acctbal,
                sdm.s_address,
                sdm.s_phone,
                sdm.total_orders,
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
                sdm.unique_parts_shipped,
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
                ssq_agg.avg_unique_parts_per_quarter,
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
                spp.unique_parts_supplied,
                spp.manufacturer_count,
                spp.brand_count,
                spp.part_category_count,
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
                spp.premium_part_percentage,
                spp.inventory_turnover_ratio,
                sca.sentiment,
                sca.comment_length,
                sca.positive_mentions,
                sca.negative_mentions,
                sca.financial_mentions,
                sca.logistics_mentions,
                sca.product_mentions
            from supplier_delivery_metrics sdm
            left join supplier_transaction_frequency stf on sdm.s_suppkey = stf.l_suppkey
            left join supplier_seasonality_quarterly_agg ssq_agg on sdm.s_suppkey = ssq_agg.l_suppkey
            left join supplier_seasonality_monthly_agg ssm_agg on sdm.s_suppkey = ssm_agg.l_suppkey
            left join supplier_risk_scores srs on sdm.s_suppkey = srs.s_suppkey
            left join supplier_parts_profile spp on sdm.s_suppkey = spp.ps_suppkey
            left join supplier_comment_analysis sca on sdm.s_suppkey = sca.s_suppkey
        )
        select * from final_supplier_report
        limit 1000;
    """)
]
