USE nanhu_mobile_analytics;
SET FOREIGN_KEY_CHECKS = 0;
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

LOAD DATA LOCAL INFILE 'data/processed/dim_date.csv'
INTO TABLE dim_date CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(date_key, month_start, year, month_number, month_label, quarter_seq, business_quarter, year_quarter, month_in_quarter);

LOAD DATA LOCAL INFILE 'data/processed/dim_product.csv'
INTO TABLE dim_product CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(product_key, sku, product_name, product_family, positioning, list_price, standard_unit_cost, launch_month_key);

LOAD DATA LOCAL INFILE 'data/processed/dim_channel.csv'
INTO TABLE dim_channel CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(channel_key, channel_name, channel_type, price_factor);

LOAD DATA LOCAL INFILE 'data/processed/dim_region.csv'
INTO TABLE dim_region CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(region_key, region_name, region_tier);

LOAD DATA LOCAL INFILE 'data/processed/fact_sales_order.csv'
INTO TABLE fact_sales_order CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, order_date_key, order_date, promised_date, shipped_date, product_key, channel_key, region_key,
 ordered_qty, shipped_qty, unit_price, gross_sales, discount_amount, net_sales, unit_cost, cogs,
 gross_profit, delivery_days, on_time_flag, full_fill_flag, order_status, payment_term_days);

LOAD DATA LOCAL INFILE 'data/processed/fact_production.csv'
INTO TABLE fact_production CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(month_key, product_key, planned_units, actual_good_units, defect_units, capacity_allocated_units,
 downtime_hours, overtime_hours, capacity_utilization);

LOAD DATA LOCAL INFILE 'data/processed/fact_inventory.csv'
INTO TABLE fact_inventory CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(month_key, product_key, beginning_inventory_qty, production_receipts_qty, demand_qty, shipped_qty,
 ending_inventory_qty, stockout_qty, inventory_value, warehouse_capacity_qty, days_of_supply, inventory_status);

LOAD DATA LOCAL INFILE 'data/processed/fact_cashflow.csv'
INTO TABLE fact_cashflow CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 LINES
(cashflow_id, date_key, transaction_date, quarter_seq, flow_direction, flow_category,
 flow_category_cn, amount, signed_amount, control_source);

SET FOREIGN_KEY_CHECKS = 1;

