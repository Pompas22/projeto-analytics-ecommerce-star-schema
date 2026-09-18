# Analytics de Vendas — E-commerce (projeto de portfólio)

Projeto pessoal de analytics engineering: SQL avançado, Python (Pandas/NumPy/PySpark),
modelagem star-schema/snowflake, KPIs, análise preditiva e um dashboard com storytelling
de dados.

Os dados são **sintéticos** (gerados por script, sem informação real de clientes),
o que permite publicar o código e o dashboard livremente como portfólio.

## Arquitetura

```
data/raw/*.csv  ───►  ETL (Python/Pandas ou PySpark)  ───►  Star-schema (SQL ANSI)  ───►  KPIs + previsão  ───►  Dashboard
   (Bronze)              02_transform_load_star_schema.py        DuckDB / BigQuery         03_kpis_e_previsao.py    dashboard/dashboard.html
```

- **`etl/01_generate_raw_data.py`** — gera pedidos, clientes e produtos sintéticos (camada Bronze/RAW).
- **`etl/02_transform_load_star_schema.py`** — limpeza e transformação com Pandas/NumPy; carga no
  data warehouse modelado em **star-schema** (`sql/create_star_schema.sql`), usando DuckDB localmente.
- **`etl/03_pyspark_etl_reference.py`** — a mesma lógica de ETL escrita em **PySpark**, pronta para
  rodar em um cluster real (Databricks, Dataproc no GCP) e gravar as tabelas no **BigQuery**.
- **`sql/kpi_queries.sql`** — consultas de KPI em SQL ANSI (receita mensal, margem por categoria,
  receita por região, taxa de cancelamento por canal).
- **`etl/03_kpis_e_previsao.py`** — roda os KPIs e uma **análise preditiva** (regressão linear com
  NumPy) projetando a receita dos próximos 3 meses.
- **`dashboard/dashboard.html`** — dashboard interativo (HTML/SVG) com os KPIs, a série histórica +
  previsão, e os recortes por categoria, região e canal.

## Por que star-schema

O modelo separa uma tabela fato de granularidade fina (`fact_sales`, 1 linha por item de
pedido) de quatro dimensões (`dim_customer`, `dim_product`, `dim_date`, `dim_channel`),
o padrão recomendado pela Kimball methodology para BI/analytics. Isso permite agregações
rápidas por qualquer combinação de dimensão sem duplicar contexto na fato, e é o mesmo
desenho que o BigQuery/Looker Studio esperam para consultas de dashboard performáticas.

## Como rodar localmente

```bash
pip install pandas numpy duckdb
python etl/01_generate_raw_data.py
python etl/02_transform_load_star_schema.py
python etl/03_kpis_e_previsao.py
# abra dashboard/dashboard.html (após injetar dashboard/kpi_data.json) no navegador
```

## Como levar para um ambiente real de nuvem (GCP + Looker Studio)

Este projeto foi desenhado para ser promovido para um ambiente real de nuvem em 3 passos:

1. **Armazenamento bruto**: subir os CSVs de `data/raw/` para um bucket do **Google Cloud
   Storage** (camada RAW).
2. **Processamento**: rodar `etl/03_pyspark_etl_reference.py --env gcp` em um cluster
   **Dataproc** (ou adaptar para um notebook **Databricks**), gravando as tabelas
   star-schema diretamente no **BigQuery** via `spark-bigquery-connector`.
3. **Visualização**: conectar o **Looker Studio** (ou Looker, via LookML) direto ao dataset
   do BigQuery, recriando os mesmos KPIs do `dashboard.html` como um relatório nativo do
   Looker Studio — com filtros de data/canal e atualização automática.

## Stack utilizada

SQL avançado (ANSI, com sintaxe compatível com Oracle SQL/BigQuery) · Python (Pandas,
NumPy, PySpark) · Modelagem de dados (star-schema) · DuckDB (warehouse local) · KPIs e
análise preditiva · Storytelling de dados / dashboard.

## Próximos passos (evolução do projeto)

- Adicionar uma dimensão `dim_promo` e medir o efeito de campanhas na receita (teste A/B).
- Modelar uma segunda fato (`fact_sessions`) em snowflake, normalizando `dim_product` em
  `dim_category` + `dim_subcategory`, para comparar os dois padrões de modelagem.
- Publicar de fato no BigQuery + Looker Studio e trocar o link do dashboard local pelo
  relatório publicado.
