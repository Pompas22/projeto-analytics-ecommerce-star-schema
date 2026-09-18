-- kpi_queries.sql
-- Consultas de KPI usadas no dashboard (Looker Studio / painel local).
-- SQL ANSI, testado em DuckDB.

-- 1) Receita, pedidos e ticket médio por mês
SELECT
    d.year_month,
    SUM(f.gross_revenue)                         AS receita,
    COUNT(DISTINCT f.order_id)                   AS pedidos,
    ROUND(SUM(f.gross_revenue) / COUNT(DISTINCT f.order_id), 2) AS ticket_medio
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
WHERE f.is_cancelled = FALSE
GROUP BY d.year_month
ORDER BY d.year_month;

-- 2) Receita e margem por categoria de produto
SELECT
    p.category,
    SUM(f.gross_revenue)                                   AS receita,
    SUM(f.gross_revenue - f.cost_total)                     AS margem_bruta,
    ROUND(100.0 * SUM(f.gross_revenue - f.cost_total) / SUM(f.gross_revenue), 1) AS margem_pct
FROM fact_sales f
JOIN dim_product p ON p.product_id = f.product_id
WHERE f.is_cancelled = FALSE
GROUP BY p.category
ORDER BY receita DESC;

-- 3) Receita por região
SELECT
    c.region,
    SUM(f.gross_revenue) AS receita,
    COUNT(DISTINCT f.customer_id) AS clientes_ativos
FROM fact_sales f
JOIN dim_customer c ON c.customer_id = f.customer_id
WHERE f.is_cancelled = FALSE
GROUP BY c.region
ORDER BY receita DESC;

-- 4) Taxa de cancelamento por canal (KPI de qualidade/operacional)
SELECT
    ch.channel_name,
    COUNT(*)                                           AS total_pedidos,
    SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END)     AS cancelados,
    ROUND(100.0 * SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END) / COUNT(*), 2) AS taxa_cancelamento_pct
FROM fact_sales f
JOIN dim_channel ch ON ch.channel_id = f.channel_id
GROUP BY ch.channel_name
ORDER BY taxa_cancelamento_pct DESC;
