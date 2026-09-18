"""
03_kpis_e_previsao.py
----------------------
1) Executa as consultas de KPI (sql/kpi_queries.sql) contra o star-schema.
2) Roda uma análise preditiva simples com NumPy: regressão linear sobre a
   série mensal de receita para projetar os próximos 3 meses (proxy de
   "análises preditivas" pedido na vaga).
3) Exporta tudo em JSON para alimentar o dashboard (dashboard/dashboard.html).
"""

import json
import duckdb
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "warehouse.duckdb"
SQL_DIR = BASE_DIR / "sql"
OUT_JSON = BASE_DIR / "dashboard" / "kpi_data.json"

con = duckdb.connect(str(DB_PATH))
queries = [q.strip() for q in (SQL_DIR / "kpi_queries.sql").read_text().split(";") if q.strip() and not q.strip().startswith("--") is False]

# separa as 4 queries nomeadas manualmente (mais simples e legível que parsear comentários)
q_receita_mensal = """
SELECT d.year_month, SUM(f.gross_revenue) AS receita, COUNT(DISTINCT f.order_id) AS pedidos,
       ROUND(SUM(f.gross_revenue) / COUNT(DISTINCT f.order_id), 2) AS ticket_medio
FROM fact_sales f JOIN dim_date d ON d.date_key = f.date_key
WHERE f.is_cancelled = FALSE GROUP BY d.year_month ORDER BY d.year_month;
"""
q_categoria = """
SELECT p.category, SUM(f.gross_revenue) AS receita, SUM(f.gross_revenue - f.cost_total) AS margem_bruta,
       ROUND(100.0 * SUM(f.gross_revenue - f.cost_total) / SUM(f.gross_revenue), 1) AS margem_pct
FROM fact_sales f JOIN dim_product p ON p.product_id = f.product_id
WHERE f.is_cancelled = FALSE GROUP BY p.category ORDER BY receita DESC;
"""
q_regiao = """
SELECT c.region, SUM(f.gross_revenue) AS receita, COUNT(DISTINCT f.customer_id) AS clientes_ativos
FROM fact_sales f JOIN dim_customer c ON c.customer_id = f.customer_id
WHERE f.is_cancelled = FALSE GROUP BY c.region ORDER BY receita DESC;
"""
q_cancelamento = """
SELECT ch.channel_name, COUNT(*) AS total_pedidos,
       SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END) AS cancelados,
       ROUND(100.0 * SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END) / COUNT(*), 2) AS taxa_cancelamento_pct
FROM fact_sales f JOIN dim_channel ch ON ch.channel_id = f.channel_id
GROUP BY ch.channel_name ORDER BY taxa_cancelamento_pct DESC;
"""

df_mensal = con.execute(q_receita_mensal).fetch_df()
df_categoria = con.execute(q_categoria).fetch_df()
df_regiao = con.execute(q_regiao).fetch_df()
df_cancelamento = con.execute(q_cancelamento).fetch_df()

# ---- Análise preditiva: regressão linear (NumPy) sobre receita mensal -----
# Usa apenas meses "fechados" (exclui o último, que costuma estar incompleto)
serie = df_mensal.iloc[:-1].reset_index(drop=True)
x = np.arange(len(serie))
y = serie["receita"].to_numpy()

# ajuste linear simples y = a*x + b (mesma lógica de uma regressão OLS)
a, b = np.polyfit(x, y, 1)

n_forecast = 3
x_future = np.arange(len(serie), len(serie) + n_forecast)
y_future = (a * x_future + b).round(2)

last_period = pd.Period(serie["year_month"].iloc[-1])
future_periods = [(last_period + i).strftime("%Y-%m") for i in range(1, n_forecast + 1)]

previsao = pd.DataFrame({"year_month": future_periods, "receita_prevista": y_future})

# KPIs consolidados (cards do dashboard)
receita_total = float(df_mensal["receita"].sum())
pedidos_total = int(df_mensal["pedidos"].sum())
ticket_medio_geral = round(receita_total / pedidos_total, 2)
taxa_cancel_geral = float(
    con.execute("SELECT ROUND(100.0*SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)/COUNT(*),2) FROM fact_sales").fetchone()[0]
)
crescimento_mensal_pct = round(100 * a / y.mean(), 2)  # inclinação da tendência vs. média (proxy de crescimento)

payload = {
    "kpis": {
        "receita_total": receita_total,
        "pedidos_total": pedidos_total,
        "ticket_medio_geral": ticket_medio_geral,
        "taxa_cancelamento_pct": taxa_cancel_geral,
        "tendencia_mensal_pct": crescimento_mensal_pct,
    },
    "receita_mensal": df_mensal.to_dict(orient="records"),
    "previsao_3_meses": previsao.to_dict(orient="records"),
    "receita_por_categoria": df_categoria.to_dict(orient="records"),
    "receita_por_regiao": df_regiao.to_dict(orient="records"),
    "cancelamento_por_canal": df_cancelamento.to_dict(orient="records"),
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

print("KPIs principais:")
for k, v in payload["kpis"].items():
    print(f"  {k}: {v}")
print(f"\nPrevisão próximos {n_forecast} meses:")
print(previsao.to_string(index=False))
print(f"\nJSON exportado em: {OUT_JSON}")

con.close()
