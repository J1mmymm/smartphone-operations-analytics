USE nanhu_mobile_analytics;

WITH checks AS (
  SELECT 'dim_date_row_count' AS check_name,
         CAST(COUNT(*) AS DECIMAL(18,2)) AS actual_value,
         CAST(42 AS DECIMAL(18,2)) AS expected_value
  FROM dim_date
  UNION ALL
  SELECT 'sales_total', SUM(net_sales), 32870200 FROM fact_sales_order
  UNION ALL
  SELECT 'L_family_total', SUM(s.net_sales), 26948200
  FROM fact_sales_order s JOIN dim_product p ON s.product_key = p.product_key
  WHERE p.product_family = 'L'
  UNION ALL
  SELECT 'H_family_total', SUM(s.net_sales), 5922000
  FROM fact_sales_order s JOIN dim_product p ON s.product_key = p.product_key
  WHERE p.product_family = 'H'
  UNION ALL
  SELECT 'cash_inflow_total', SUM(amount), 50130681 FROM fact_cashflow WHERE flow_direction = 'Inflow'
  UNION ALL
  SELECT 'cash_outflow_total', SUM(amount), 49777407 FROM fact_cashflow WHERE flow_direction = 'Outflow'
  UNION ALL
  SELECT 'ending_cash', SUM(signed_amount), 353274 FROM fact_cashflow
  UNION ALL
  SELECT 'duplicate_order_ids', COUNT(*) - COUNT(DISTINCT order_id), 0 FROM fact_sales_order
  UNION ALL
  SELECT 'invalid_inventory_balance', COUNT(*), 0 FROM fact_inventory
  WHERE beginning_inventory_qty + production_receipts_qty - shipped_qty <> ending_inventory_qty
  UNION ALL
  SELECT 'orphan_dimension_keys',
         SUM(CASE WHEN p.product_key IS NULL OR c.channel_key IS NULL OR r.region_key IS NULL OR d.date_key IS NULL THEN 1 ELSE 0 END), 0
  FROM fact_sales_order s
  LEFT JOIN dim_product p ON s.product_key = p.product_key
  LEFT JOIN dim_channel c ON s.channel_key = c.channel_key
  LEFT JOIN dim_region r ON s.region_key = r.region_key
  LEFT JOIN dim_date d ON s.order_date_key = d.date_key
)
SELECT check_name, actual_value, expected_value,
       CASE WHEN ABS(actual_value - expected_value) < 0.01 THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks
ORDER BY status, check_name;

WITH quarters AS (
  SELECT DISTINCT quarter_seq FROM dim_date
), quarter_cash AS (
  SELECT q.quarter_seq,
         COALESCE(SUM(CASE WHEN c.flow_direction = 'Inflow' THEN c.amount ELSE 0 END), 0) AS inflow,
         COALESCE(SUM(CASE WHEN c.flow_direction = 'Outflow' THEN c.amount ELSE 0 END), 0) AS outflow,
         COALESCE(SUM(c.signed_amount), 0) AS net_flow
  FROM quarters q
  LEFT JOIN fact_cashflow c ON q.quarter_seq = c.quarter_seq
  GROUP BY q.quarter_seq
), balances AS (
  SELECT quarter_seq, inflow, outflow, net_flow,
         SUM(net_flow) OVER (ORDER BY quarter_seq ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS opening_cash,
         SUM(net_flow) OVER (ORDER BY quarter_seq ROWS UNBOUNDED PRECEDING) AS closing_cash
  FROM quarter_cash
)
SELECT quarter_seq, COALESCE(opening_cash, 0) AS opening_cash, inflow, outflow, net_flow, closing_cash,
       CASE WHEN ABS(COALESCE(opening_cash, 0) + net_flow - closing_cash) < 0.01 THEN 'PASS' ELSE 'FAIL' END AS reconciliation_status
FROM balances
ORDER BY quarter_seq;
