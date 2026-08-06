USE nanhu_mobile_analytics;

CREATE TABLE dim_date (
  date_key INT PRIMARY KEY,
  month_start DATE NOT NULL,
  year SMALLINT NOT NULL,
  month_number TINYINT NOT NULL,
  month_label VARCHAR(7) NOT NULL,
  quarter_seq TINYINT NOT NULL,
  business_quarter VARCHAR(3) NOT NULL,
  year_quarter VARCHAR(7) NOT NULL,
  month_in_quarter TINYINT NOT NULL,
  UNIQUE KEY uk_dim_date_month_start (month_start)
);

CREATE TABLE dim_product (
  product_key INT PRIMARY KEY,
  sku VARCHAR(10) NOT NULL,
  product_name VARCHAR(50) NOT NULL,
  product_family CHAR(1) NOT NULL,
  positioning VARCHAR(50) NOT NULL,
  list_price DECIMAL(12,2) NOT NULL,
  standard_unit_cost DECIMAL(12,2) NOT NULL,
  launch_month_key INT NOT NULL,
  UNIQUE KEY uk_dim_product_sku (sku)
);

CREATE TABLE dim_channel (
  channel_key INT PRIMARY KEY,
  channel_name VARCHAR(30) NOT NULL,
  channel_type VARCHAR(20) NOT NULL,
  price_factor DECIMAL(8,4) NOT NULL
);

CREATE TABLE dim_region (
  region_key INT PRIMARY KEY,
  region_name VARCHAR(30) NOT NULL,
  region_tier VARCHAR(20) NOT NULL
);

CREATE TABLE fact_sales_order (
  order_id VARCHAR(12) PRIMARY KEY,
  order_date_key INT NOT NULL,
  order_date DATE NOT NULL,
  promised_date DATE NOT NULL,
  shipped_date DATE NOT NULL,
  product_key INT NOT NULL,
  channel_key INT NOT NULL,
  region_key INT NOT NULL,
  ordered_qty INT NOT NULL,
  shipped_qty INT NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  gross_sales DECIMAL(14,2) NOT NULL,
  discount_amount DECIMAL(14,2) NOT NULL,
  net_sales DECIMAL(14,2) NOT NULL,
  unit_cost DECIMAL(12,2) NOT NULL,
  cogs DECIMAL(14,2) NOT NULL,
  gross_profit DECIMAL(14,2) NOT NULL,
  delivery_days INT NOT NULL,
  on_time_flag TINYINT NOT NULL,
  full_fill_flag TINYINT NOT NULL,
  order_status VARCHAR(20) NOT NULL,
  payment_term_days INT NOT NULL,
  KEY idx_sales_date (order_date_key),
  KEY idx_sales_product (product_key),
  KEY idx_sales_channel (channel_key),
  KEY idx_sales_region (region_key),
  CONSTRAINT fk_sales_date FOREIGN KEY (order_date_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_sales_product FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
  CONSTRAINT fk_sales_channel FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key),
  CONSTRAINT fk_sales_region FOREIGN KEY (region_key) REFERENCES dim_region(region_key),
  CONSTRAINT ck_sales_qty CHECK (ordered_qty > 0 AND shipped_qty BETWEEN 0 AND ordered_qty),
  CONSTRAINT ck_sales_amount CHECK (net_sales > 0 AND cogs >= 0)
);

CREATE TABLE fact_production (
  month_key INT NOT NULL,
  product_key INT NOT NULL,
  planned_units INT NOT NULL,
  actual_good_units INT NOT NULL,
  defect_units INT NOT NULL,
  capacity_allocated_units INT NOT NULL,
  downtime_hours DECIMAL(10,1) NOT NULL,
  overtime_hours DECIMAL(10,1) NOT NULL,
  capacity_utilization DECIMAL(8,4) NOT NULL,
  PRIMARY KEY (month_key, product_key),
  CONSTRAINT fk_production_date FOREIGN KEY (month_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_production_product FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
  CONSTRAINT ck_production_qty CHECK (planned_units >= 0 AND actual_good_units >= 0 AND defect_units >= 0)
);

CREATE TABLE fact_inventory (
  month_key INT NOT NULL,
  product_key INT NOT NULL,
  beginning_inventory_qty INT NOT NULL,
  production_receipts_qty INT NOT NULL,
  demand_qty INT NOT NULL,
  shipped_qty INT NOT NULL,
  ending_inventory_qty INT NOT NULL,
  stockout_qty INT NOT NULL,
  inventory_value DECIMAL(14,2) NOT NULL,
  warehouse_capacity_qty INT NOT NULL,
  days_of_supply DECIMAL(10,1) NOT NULL,
  inventory_status VARCHAR(10) NOT NULL,
  PRIMARY KEY (month_key, product_key),
  CONSTRAINT fk_inventory_date FOREIGN KEY (month_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_inventory_product FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
  CONSTRAINT ck_inventory_balance CHECK (
    beginning_inventory_qty + production_receipts_qty - shipped_qty = ending_inventory_qty
  )
);

CREATE TABLE fact_cashflow (
  cashflow_id VARCHAR(10) PRIMARY KEY,
  date_key INT NOT NULL,
  transaction_date DATE NOT NULL,
  quarter_seq TINYINT NOT NULL,
  flow_direction VARCHAR(10) NOT NULL,
  flow_category VARCHAR(50) NOT NULL,
  flow_category_cn VARCHAR(50) NOT NULL,
  amount DECIMAL(14,2) NOT NULL,
  signed_amount DECIMAL(14,2) NOT NULL,
  control_source VARCHAR(30) NOT NULL,
  KEY idx_cashflow_date (date_key),
  KEY idx_cashflow_category (flow_category),
  CONSTRAINT fk_cashflow_date FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
  CONSTRAINT ck_cashflow_direction CHECK (
    (flow_direction = 'Inflow' AND signed_amount > 0)
    OR (flow_direction = 'Outflow' AND signed_amount < 0)
  )
);

