USE nanhu_mobile_analytics;

CREATE OR REPLACE VIEW vw_management_kpi_monthly AS
WITH sales AS (
  SELECT order_date_key AS date_key,
         SUM(net_sales) AS net_sales,
         SUM(gross_profit) AS gross_profit,
         SUM(ordered_qty) AS ordered_qty,
         SUM(shipped_qty) AS shipped_qty,
         AVG(on_time_flag) AS on_time_order_rate
  FROM fact_sales_order
  GROUP BY order_date_key
), production AS (
  SELECT month_key AS date_key,
         SUM(actual_good_units + defect_units) AS produced_units,
         SUM(capacity_allocated_units) AS capacity_units
  FROM fact_production
  GROUP BY month_key
), inventory AS (
  SELECT month_key AS date_key,
         SUM(inventory_value) AS ending_inventory_value,
         SUM(ending_inventory_qty) AS ending_inventory_qty,
         SUM(stockout_qty) AS stockout_qty,
         SUM(warehouse_capacity_qty) AS warehouse_capacity_qty
  FROM fact_inventory
  GROUP BY month_key
), cash AS (
  SELECT date_key,
         SUM(CASE WHEN flow_direction = 'Inflow' THEN amount ELSE 0 END) AS cash_inflow,
         SUM(CASE WHEN flow_direction = 'Outflow' THEN amount ELSE 0 END) AS cash_outflow,
         SUM(signed_amount) AS net_cashflow
  FROM fact_cashflow
  GROUP BY date_key
), base AS (
  SELECT d.date_key, d.month_start, d.month_label, d.quarter_seq, d.business_quarter,
         COALESCE(s.net_sales, 0) AS net_sales,
         COALESCE(s.gross_profit, 0) AS gross_profit,
         COALESCE(s.ordered_qty, 0) AS ordered_qty,
         COALESCE(s.shipped_qty, 0) AS shipped_qty,
         COALESCE(s.on_time_order_rate, 0) AS on_time_order_rate,
         COALESCE(p.produced_units, 0) AS produced_units,
         COALESCE(p.capacity_units, 0) AS capacity_units,
         COALESCE(i.ending_inventory_value, 0) AS ending_inventory_value,
         COALESCE(i.ending_inventory_qty, 0) AS ending_inventory_qty,
         COALESCE(i.stockout_qty, 0) AS stockout_qty,
         COALESCE(i.warehouse_capacity_qty, 0) AS warehouse_capacity_qty,
         COALESCE(c.cash_inflow, 0) AS cash_inflow,
         COALESCE(c.cash_outflow, 0) AS cash_outflow,
         COALESCE(c.net_cashflow, 0) AS net_cashflow
  FROM dim_date d
  LEFT JOIN sales s ON d.date_key = s.date_key
  LEFT JOIN production p ON d.date_key = p.date_key
  LEFT JOIN inventory i ON d.date_key = i.date_key
  LEFT JOIN cash c ON d.date_key = c.date_key
)
SELECT base.*,
       CASE WHEN net_sales = 0 THEN 0 ELSE gross_profit / net_sales END AS gross_margin,
       CASE WHEN ordered_qty = 0 THEN 0 ELSE shipped_qty / ordered_qty END AS fill_rate,
       CASE WHEN capacity_units = 0 THEN 0 ELSE produced_units / capacity_units END AS capacity_utilization,
       CASE WHEN warehouse_capacity_qty = 0 THEN 0 ELSE ending_inventory_qty / warehouse_capacity_qty END AS warehouse_utilization,
       SUM(net_cashflow) OVER (ORDER BY date_key ROWS UNBOUNDED PRECEDING) AS closing_cash
FROM base;

CREATE OR REPLACE VIEW vw_sales_mix AS
WITH mix AS (
  SELECT d.quarter_seq, d.business_quarter, p.product_family, p.sku, p.product_name,
         c.channel_name, r.region_name,
         SUM(s.net_sales) AS net_sales, SUM(s.ordered_qty) AS ordered_qty,
         SUM(s.gross_profit) AS gross_profit
  FROM fact_sales_order s
  JOIN dim_date d ON s.order_date_key = d.date_key
  JOIN dim_product p ON s.product_key = p.product_key
  JOIN dim_channel c ON s.channel_key = c.channel_key
  JOIN dim_region r ON s.region_key = r.region_key
  GROUP BY d.quarter_seq, d.business_quarter, p.product_family, p.sku, p.product_name,
           c.channel_name, r.region_name
)
SELECT mix.*,
       gross_profit / NULLIF(net_sales, 0) AS gross_margin,
       net_sales / NULLIF(SUM(net_sales) OVER (PARTITION BY quarter_seq), 0) AS quarter_sales_share
FROM mix;

CREATE OR REPLACE VIEW vw_inventory_health AS
SELECT d.month_start, d.month_label, d.quarter_seq, d.business_quarter,
       p.sku, p.product_name, p.product_family,
       i.beginning_inventory_qty, i.production_receipts_qty, i.demand_qty,
       i.shipped_qty, i.ending_inventory_qty, i.stockout_qty,
       i.inventory_value, i.days_of_supply, i.inventory_status,
       i.ending_inventory_qty / NULLIF(i.warehouse_capacity_qty, 0) AS warehouse_utilization
FROM fact_inventory i
JOIN dim_date d ON i.month_key = d.date_key
JOIN dim_product p ON i.product_key = p.product_key;

CREATE OR REPLACE VIEW vw_fulfillment_efficiency AS
SELECT d.quarter_seq, d.business_quarter, c.channel_name, r.region_name,
       COUNT(*) AS order_lines,
       SUM(s.ordered_qty) AS ordered_qty,
       SUM(s.shipped_qty) AS shipped_qty,
       SUM(s.shipped_qty) / NULLIF(SUM(s.ordered_qty), 0) AS fill_rate,
       AVG(s.on_time_flag) AS on_time_order_rate,
       AVG(s.delivery_days) AS avg_delivery_days,
       SUM(CASE WHEN s.order_status <> 'Completed' THEN 1 ELSE 0 END) AS exception_orders
FROM fact_sales_order s
JOIN dim_date d ON s.order_date_key = d.date_key
JOIN dim_channel c ON s.channel_key = c.channel_key
JOIN dim_region r ON s.region_key = r.region_key
GROUP BY d.quarter_seq, d.business_quarter, c.channel_name, r.region_name;

CREATE OR REPLACE VIEW vw_cashflow_analysis AS
WITH monthly_category AS (
  SELECT d.date_key, d.month_start, d.month_label, d.quarter_seq, d.business_quarter,
         c.flow_direction, c.flow_category, c.flow_category_cn,
         SUM(c.amount) AS amount, SUM(c.signed_amount) AS signed_amount
  FROM fact_cashflow c
  JOIN dim_date d ON c.date_key = d.date_key
  GROUP BY d.date_key, d.month_start, d.month_label, d.quarter_seq, d.business_quarter,
           c.flow_direction, c.flow_category, c.flow_category_cn
), monthly_net AS (
  SELECT date_key, SUM(signed_amount) AS net_cashflow
  FROM monthly_category
  GROUP BY date_key
), balance AS (
  SELECT date_key,
         SUM(net_cashflow) OVER (ORDER BY date_key ROWS UNBOUNDED PRECEDING) AS closing_cash
  FROM monthly_net
)
SELECT mc.*, b.closing_cash
FROM monthly_category mc
JOIN balance b ON mc.date_key = b.date_key;

