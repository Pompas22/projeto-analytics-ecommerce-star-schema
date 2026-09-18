"""
01_generate_raw_data.py
------------------------
Gera dados brutos sintéticos de vendas de um e-commerce (pedidos, itens,
clientes, produtos) simulando a extração de um sistema operacional (OLTP).

Em um cenário real no GCP, esse arquivo seria substituído por uma extração
via Cloud Functions / Cloud Composer (Airflow) a partir do banco
transacional, com o resultado gravado em Cloud Storage (camada RAW/Bronze).
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 400
N_PRODUCTS = 60
N_ORDERS = 6000

REGIONS = ["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"]
CHANNELS = ["App", "Site", "Marketplace"]
CATEGORIES = ["Eletrônicos", "Moda", "Casa", "Beleza", "Esporte"]

# ---- Dimensão Cliente (bruta) -------------------------------------------
customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUSTOMERS + 1),
    "region": RNG.choice(REGIONS, N_CUSTOMERS, p=[0.45, 0.2, 0.2, 0.1, 0.05]),
    "signup_date": pd.to_datetime("2023-01-01") + pd.to_timedelta(
        RNG.integers(0, 900, N_CUSTOMERS), unit="D"
    ),
})

# ---- Dimensão Produto (bruta) --------------------------------------------
products = pd.DataFrame({
    "product_id": np.arange(1, N_PRODUCTS + 1),
    "category": RNG.choice(CATEGORIES, N_PRODUCTS),
    "unit_cost": RNG.uniform(10, 400, N_PRODUCTS).round(2),
})
products["unit_price"] = (products["unit_cost"] * RNG.uniform(1.3, 2.2, N_PRODUCTS)).round(2)

# ---- Fato Pedidos (bruta, granularidade item-de-pedido) ------------------
order_id = np.arange(1, N_ORDERS + 1)
order_dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(
    RNG.integers(0, 600, N_ORDERS), unit="D"
)
orders = pd.DataFrame({
    "order_id": order_id,
    "order_date": order_dates,
    "customer_id": RNG.integers(1, N_CUSTOMERS + 1, N_ORDERS),
    "channel": RNG.choice(CHANNELS, N_ORDERS, p=[0.4, 0.35, 0.25]),
    "product_id": RNG.integers(1, N_PRODUCTS + 1, N_ORDERS),
    "quantity": RNG.integers(1, 5, N_ORDERS),
    # ~7% de cancelamento, usado depois como proxy de "churn de pedido"
    "status": RNG.choice(["concluído", "cancelado"], N_ORDERS, p=[0.93, 0.07]),
})

customers.to_csv(OUT_DIR / "customers_raw.csv", index=False)
products.to_csv(OUT_DIR / "products_raw.csv", index=False)
orders.to_csv(OUT_DIR / "orders_raw.csv", index=False)

print(f"Gerado: {len(customers)} clientes, {len(products)} produtos, {len(orders)} pedidos")
print(f"Arquivos salvos em: {OUT_DIR}")
