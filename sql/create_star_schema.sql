-- create_star_schema.sql
-- Modelagem star-schema do Data Warehouse de Vendas.
-- Escrito em SQL ANSI (roda em DuckDB, BigQuery, Snowflake, PostgreSQL etc.
-- com poucos ajustes de tipos).
--
-- FATO: fact_sales (granularidade = 1 item de pedido)
-- DIMENSÕES: dim_customer, dim_product, dim_date, dim_channel

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer (
    customer_id   INTEGER PRIMARY KEY,
    region        VARCHAR,
    signup_date   DATE,
    customer_tenure_days INTEGER
);

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_id   INTEGER PRIMARY KEY,
    category     VARCHAR,
    unit_cost    DECIMAL(10,2),
    unit_price   DECIMAL(10,2),
    margin_pct   DECIMAL(6,3)
);

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date_key     DATE PRIMARY KEY,
    year         INTEGER,
    month        INTEGER,
    year_month   VARCHAR,
    quarter      INTEGER
);

DROP TABLE IF EXISTS dim_channel;
CREATE TABLE dim_channel (
    channel_id   INTEGER PRIMARY KEY,
    channel_name VARCHAR
);

DROP TABLE IF EXISTS fact_sales;
CREATE TABLE fact_sales (
    order_id      INTEGER,
    date_key      DATE,
    customer_id   INTEGER,
    product_id    INTEGER,
    channel_id    INTEGER,
    quantity      INTEGER,
    gross_revenue DECIMAL(12,2),
    cost_total    DECIMAL(12,2),
    is_cancelled  BOOLEAN,
    FOREIGN KEY (date_key)    REFERENCES dim_date(date_key),
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (product_id)  REFERENCES dim_product(product_id),
    FOREIGN KEY (channel_id)  REFERENCES dim_channel(channel_id)
);
