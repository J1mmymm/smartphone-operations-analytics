USE nanhu_mobile_analytics;

-- 1) Quarterly KPI trend with LAG: growth, margin, fulfillment and cash buffer.
WITH quarters AS (
  SELECT DISTINCT quarter_seq, business_quarter FROM dim_date
), sales_quarter AS (
  SELECT d.quarter_seq,
         SUM(s.net_sales) AS net_sales,
         SUM(s.gross_profit) AS gross_profit,
         SUM(s.shipped_qty) AS shipped_qty,
         SUM(s.ordered_qty) AS ordered_qty,
         AVG(s.on_time_flag) AS on_time_order_rate
  FROM fact_sales_order s JOIN dim_date d ON s.order_date_key = d.date_key
  GROUP BY d.quarter_seq
), quarterly AS (
  SELECT q.quarter_seq, q.business_quarter,
         COALESCE(s.net_sales, 0) AS net_sales,
         COALESCE(s.gross_profit, 0) / NULLIF(s.net_sales, 0) AS gross_margin,
         COALESCE(s.shipped_qty, 0) / NULLIF(s.ordered_qty, 0) AS fill_rate,
         COALESCE(s.on_time_order_rate, 0) AS on_time_order_rate
  FROM quarters q LEFT JOIN sales_quarter s USING (quarter_seq)
), cash AS (
  SELECT q.quarter_seq,
         COALESCE(SUM(c.signed_amount), 0) AS net_cashflow,
         SUM(COALESCE(SUM(c.signed_amount), 0)) OVER (ORDER BY q.quarter_seq) AS closing_cash
  FROM quarters q LEFT JOIN fact_cashflow c USING (quarter_seq)
  GROUP BY q.quarter_seq
)
SELECT q.*,
       (q.net_sales - LAG(q.net_sales) OVER (ORDER BY q.quarter_seq))
         / NULLIF(LAG(q.net_sales) OVER (ORDER BY q.quarter_seq), 0) AS sales_qoq_growth,
       c.net_cashflow, c.closing_cash,
       CASE
         WHEN c.closing_cash < 100000 THEN 'Critical'
         WHEN c.closing_cash < 300000 THEN 'Watch'
         ELSE 'Stable'
       END AS cash_risk_band
FROM quarterly q JOIN cash c USING (quarter_seq)
ORDER BY q.quarter_seq;

-- 2) Product contribution and margin rank using window functions.
WITH product_performance AS (
  SELECT p.sku, p.product_name, p.product_family,
         SUM(s.net_sales) AS net_sales, SUM(s.gross_profit) AS gross_profit,
         SUM(s.gross_profit) / NULLIF(SUM(s.net_sales), 0) AS gross_margin
  FROM fact_sales_order s JOIN dim_product p ON s.product_key = p.product_key
  GROUP BY p.sku, p.product_name, p.product_family
)
SELECT *,
       net_sales / SUM(net_sales) OVER () AS sales_share,
       DENSE_RANK() OVER (ORDER BY net_sales DESC) AS sales_rank,
       DENSE_RANK() OVER (ORDER BY gross_margin DESC) AS margin_rank
FROM product_performance
ORDER BY sales_rank;

-- 3) Channel x region concentration, with rank inside each channel.
WITH channel_region AS (
  SELECT c.channel_name, r.region_name,
         SUM(s.net_sales) AS net_sales, SUM(s.ordered_qty) AS units,
         AVG(s.on_time_flag) AS on_time_order_rate
  FROM fact_sales_order s
  JOIN dim_channel c ON s.channel_key = c.channel_key
  JOIN dim_region r ON s.region_key = r.region_key
  GROUP BY c.channel_name, r.region_name
)
SELECT *,
       RANK() OVER (PARTITION BY channel_name ORDER BY net_sales DESC) AS region_rank_in_channel,
       net_sales / SUM(net_sales) OVER (PARTITION BY channel_name) AS channel_region_share
FROM channel_region
ORDER BY channel_name, region_rank_in_channel;

-- 4) Operational pressure: capacity, stock coverage and delivery performance.
WITH operation_month AS (
  SELECT d.date_key, d.month_label, d.quarter_seq,
         SUM(p.actual_good_units + p.defect_units) / NULLIF(SUM(p.capacity_allocated_units), 0) AS capacity_utilization,
         SUM(i.ending_inventory_qty) / NULLIF(SUM(i.warehouse_capacity_qty), 0) AS warehouse_utilization,
         SUM(i.demand_qty) AS demand_qty,
         SUM(i.stockout_qty) AS stockout_qty,
         AVG(i.days_of_supply) AS avg_days_of_supply
  FROM dim_date d
  JOIN fact_production p ON d.date_key = p.month_key
  JOIN fact_inventory i ON p.month_key = i.month_key AND p.product_key = i.product_key
  GROUP BY d.date_key, d.month_label, d.quarter_seq
), delivery_month AS (
  SELECT order_date_key AS date_key,
         AVG(on_time_flag) AS on_time_order_rate,
         AVG(delivery_days) AS avg_delivery_days
  FROM fact_sales_order GROUP BY order_date_key
)
SELECT o.*, COALESCE(d.on_time_order_rate, 0) AS on_time_order_rate,
       COALESCE(d.avg_delivery_days, 0) AS avg_delivery_days,
       CASE
         WHEN o.demand_qty = 0 THEN 'No commercial demand'
         WHEN o.capacity_utilization >= 0.90 OR o.avg_days_of_supply < 8 THEN 'High pressure'
         WHEN o.capacity_utilization >= 0.80 OR o.avg_days_of_supply < 15 THEN 'Watch'
         ELSE 'Normal'
       END AS operating_pressure
FROM operation_month o LEFT JOIN delivery_month d USING (date_key)
ORDER BY o.date_key;

-- 5) Cash use structure and concentration.
WITH outflow AS (
  SELECT flow_category_cn, SUM(amount) AS outflow_amount
  FROM fact_cashflow
  WHERE flow_direction = 'Outflow'
  GROUP BY flow_category_cn
)
SELECT flow_category_cn, outflow_amount,
       outflow_amount / SUM(outflow_amount) OVER () AS outflow_share,
       SUM(outflow_amount) OVER (ORDER BY outflow_amount DESC ROWS UNBOUNDED PRECEDING)
         / SUM(outflow_amount) OVER () AS cumulative_share
FROM outflow
ORDER BY outflow_amount DESC;
