"""
03_pyspark_etl_reference.py
-----------------------------
Versão de referência em PySpark do mesmo ETL (etl/02_transform_load_star_schema.py),
para rodar em um cluster real (Databricks, Dataproc no GCP, ou localmente com
`pip install pyspark` + Java instalado). Mantém a mesma lógica de negócio e o
mesmo modelo star-schema, trocando Pandas/DuckDB por Spark DataFrames e
gravação no BigQuery.

Como rodar:
  - Local/teste:   spark-submit 03_pyspark_etl_reference.py --env local
  - GCP Dataproc:  gcloud dataproc jobs submit pyspark 03_pyspark_etl_reference.py \
                     --cluster=<nome-do-cluster> --region=<regiao> \
                     -- --env gcp --dataset analytics_ecommerce
"""

import argparse
from pyspark.sql import SparkSession, functions as F, Window


def build_spark(app_name="analytics-ecommerce-etl"):
    return (
        SparkSession.builder.appName(app_name)
        # em produção no GCP: .config("spark.jars", "gcs-connector.jar") para ler/gravar em GCS/BigQuery
        .getOrCreate()
    )


def run(spark, raw_path: str, sink: str, bq_dataset: str | None = None):
    customers = spark.read.option("header", True).csv(f"{raw_path}/customers_raw.csv")
    products = spark.read.option("header", True).csv(f"{raw_path}/products_raw.csv")
    orders = spark.read.option("header", True).csv(f"{raw_path}/orders_raw.csv")

    customers = customers.withColumn("signup_date", F.to_date("signup_date"))
    orders = orders.withColumn("order_date", F.to_date("order_date")) \
                    .withColumn("quantity", F.col("quantity").cast("int"))
    products = products.withColumn("unit_cost", F.col("unit_cost").cast("double")) \
                       .withColumn("unit_price", F.col("unit_price").cast("double"))

    # ---- dim_customer ----------------------------------------------------
    dim_customer = customers.withColumn(
        "customer_tenure_days", F.datediff(F.current_date(), F.col("signup_date"))
    ).select("customer_id", "region", "signup_date", "customer_tenure_days")

    # ---- dim_product (margem calculada) -----------------------------------
    dim_product = products.withColumn(
        "margin_pct", F.round((F.col("unit_price") - F.col("unit_cost")) / F.col("unit_price"), 3)
    ).select("product_id", "category", "unit_cost", "unit_price", "margin_pct")

    # ---- dim_date -----------------------------------------------------------
    dim_date = (
        orders.select(F.col("order_date").alias("date_key")).distinct()
        .withColumn("year", F.year("date_key"))
        .withColumn("month", F.month("date_key"))
        .withColumn("year_month", F.date_format("date_key", "yyyy-MM"))
        .withColumn("quarter", F.quarter("date_key"))
    )

    # ---- dim_channel --------------------------------------------------------
    channels = orders.select("channel").distinct()
    w = Window.orderBy("channel")
    dim_channel = channels.withColumn("channel_id", F.row_number().over(w)) \
                           .select("channel_id", F.col("channel").alias("channel_name"))

    # ---- fact_sales -----------------------------------------------------------
    fact_sales = (
        orders.join(products.select("product_id", "unit_price", "unit_cost"), "product_id", "left")
        .join(dim_channel.withColumnRenamed("channel_name", "channel"), "channel", "left")
        .withColumn("gross_revenue", F.round(F.col("quantity") * F.col("unit_price"), 2))
        .withColumn("cost_total", F.round(F.col("quantity") * F.col("unit_cost"), 2))
        .withColumn("is_cancelled", F.col("status") == F.lit("cancelado"))
        .withColumnRenamed("order_date", "date_key")
        .select("order_id", "date_key", "customer_id", "product_id", "channel_id",
                "quantity", "gross_revenue", "cost_total", "is_cancelled")
    )

    tables = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_date": dim_date,
        "dim_channel": dim_channel,
        "fact_sales": fact_sales,
    }

    if sink == "bigquery":
        # Gravação real no BigQuery (star-schema), usando o conector spark-bigquery.
        for name, df in tables.items():
            (
                df.write.format("bigquery")
                .option("table", f"{bq_dataset}.{name}")
                .mode("overwrite")
                .save()
            )
    else:
        # Sink local (parquet) para validação sem depender de credenciais de nuvem.
        for name, df in tables.items():
            df.write.mode("overwrite").parquet(f"{raw_path}/../warehouse_parquet/{name}")

    return tables


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["local", "gcp"], default="local")
    parser.add_argument("--dataset", default="analytics_ecommerce")
    args = parser.parse_args()

    spark = build_spark()
    raw_path = "data/raw"
    sink = "bigquery" if args.env == "gcp" else "parquet"
    result = run(spark, raw_path, sink, bq_dataset=args.dataset)

    for name, df in result.items():
        print(f"{name}: {df.count()} linhas")
    spark.stop()
