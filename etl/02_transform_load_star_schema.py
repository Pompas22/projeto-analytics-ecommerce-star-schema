"""
02_transform_load_star_schema.py
---------------------------------
Camada de transformação (Bronze -> Silver/Gold): lê os dados brutos,
aplica limpeza e regras de negócio com Pandas/NumPy e carrega o resultado
no Data Warehouse modelado em star-schema.

Neste projeto o "warehouse" é um arquivo DuckDB local (sql ANSI, mesma
sintaxe usada no BigQuery para estas consultas). Em produção no GCP, esta
etapa seria um job PySpark rodando no Dataproc/Dataflow, gravando as
tabelas no BigQuery — ver etl/03_pyspark_etl_reference.py para a versão
equivalente em PySpark.
"""

import duckdb
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "data" / "warehouse.duckdb"
SQL_DIR = BASE_DIR / "sql"

# ---- 1. Extract -----------------------------------------------------------
customers = pd.read_csv(RAW_DIR / "customers_raw.csv", parse_dates=["signup_date"])
products = pd.read_csv(RAW_DIR / "products_raw.csv")
orders = pd.read_csv(RAW_DIR / "orders_raw.csv", parse_dates=["order_date"])

# ---- 2. Transform: dim_customer -------------------------------------------
today = pd.Timestamp("2026-09-18")
customers["customer_tenure_days"] = (today - customers["signup_date"]).dt.days
dim_customer = customers[["customer_id", "region", "signup_date", "customer_tenure_days"]]

# ---- 2. Transform: dim_product (margem calculada) -------------------------
products["margin_pct"] = ((products["unit_price"] - products["unit_cost"]) / products["unit_price"]).round(3)
dim_product = products[["product_id", "category", "unit_cost", "unit_price", "margin_pct"]]

# ---- 2. Transform: dim_date (uma linha por dia distinto de pedido) --------
dates = pd.DataFrame({"date_key": orders["order_date"].dt.normalize().unique()})
dates = dates.sort_values("date_key").reset_index(drop=True)
dates["year"] = dates["date_key"].dt.year
dates["month"] = dates["date_key"].dt.month
dates["year_month"] = dates["date_key"].dt.strftime("%Y-%m")
dates["quarter"] = dates["date_key"].dt.quarter
dim_date = dates

# ---- 2. Transform: dim_channel --------------------------------------------
channels = sorted(orders["channel"].unique())
dim_channel = pd.DataFrame({
    "channel_id": np.arange(1, len(channels) + 1),
    "channel_name": channels,
})
channel_map = dict(zip(dim_channel["channel_name"], dim_channel["channel_id"]))

# ---- 2. Transform: fact_sales -----------------------------------------------
fact = orders.merge(products[["product_id", "unit_price", "unit_cost"]], on="product_id", how="left")
fact["gross_revenue"] = (fact["quantity"] * fact["unit_price"]).round(2)
fact["cost_total"] = (fact["quantity"] * fact["unit_cost"]).round(2)
fact["is_cancelled"] = fact["status"].eq("cancelado")
fact["channel_id"] = fact["channel"].map(channel_map)
fact["date_key"] = fact["order_date"].dt.normalize()

fact_sales = fact[[
    "order_id", "date_key", "customer_id", "product_id", "channel_id",
    "quantity", "gross_revenue", "cost_total", "is_cancelled",
]]

# ---- 3. Load: cria o schema estrela e grava as tabelas no DuckDB ----------
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB_PATH))
con.execute((SQL_DIR / "create_star_schema.sql").read_text())

con.register("dim_customer_df", dim_customer)
con.register("dim_product_df", dim_product)
con.register("dim_date_df", dim_date)
con.register("dim_channel_df", dim_channel)
con.register("fact_sales_df", fact_sales)

con.execute("INSERT INTO dim_customer SELECT * FROM dim_customer_df")
con.execute("INSERT INTO dim_product SELECT * FROM dim_product_df")
con.execute("INSERT INTO dim_date SELECT * FROM dim_date_df")
con.execute("INSERT INTO dim_channel SELECT * FROM dim_channel_df")
con.execute("INSERT INTO fact_sales SELECT * FROM fact_sales_df")

n_fact = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
print(f"Star-schema carregado em {DB_PATH}")
print(f"fact_sales: {n_fact} linhas | dim_customer: {len(dim_customer)} | dim_product: {len(dim_product)} | dim_date: {len(dim_date)} | dim_channel: {len(dim_channel)}")

con.close()
