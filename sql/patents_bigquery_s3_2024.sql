-- ============================================================================
-- FYP · 补充分析 S3：企业专利延到 2024 年（J12，2026-10-04）
-- 规则：docs/RQ2补充分析计划_2026-10-02.md「S3」（10/2 写定，未改）
--
-- 与 sql/patents_bigquery.sql v4 完全相同，只改两处：
--   ① 申请日上限 2023-12-31 → 2024-12-31（起点不变）
--   ② 每个家族多带出两列：
--        first_pub_in_window  该家族在本查询命中的公开里最早的公开日（判断数据是否完整用）
--        max_pub_in_query     本次查询全部命中公开里最晚的公开日（同一值，每行重复）
-- 全部季度（2015–2024）都用这一次新拉的数据，不与 8/26 的旧数拼接。
--
-- 成本：与 v4 同量级（v2 实测 15.37 GB），免费额度内。点运行前先看右上角 "This query will process X"。
-- 导出 → raw/patents_families_raw_s3.csv
-- 表头：industry,city,quarter,family_id,first_filing_in_window,first_pub_in_window,max_pub_in_query,assignees
-- ============================================================================

WITH hits AS (
  SELECT
    p.family_id,
    p.filing_date,
    p.publication_date,
    a.country_code AS cc,
    a.name         AS assignee,
    c.code         AS cpc
  FROM `patents-public-data.patents.publications` AS p,
    UNNEST(p.assignee_harmonized) AS a,
    UNNEST(p.cpc)                 AS c
  WHERE a.country_code IN ('HK', 'SG')
    AND p.filing_date BETWEEN 20150101 AND 20241231
),
latest AS (
  SELECT MAX(publication_date) AS max_pub_in_query FROM hits
),
tagged AS (
  SELECT family_id, filing_date, publication_date, cc, assignee,
    CASE
      WHEN cpc LIKE 'G06N%'   OR cpc LIKE 'G06V%' OR cpc LIKE 'G10L%'
        OR cpc LIKE 'G06F40%' OR cpc LIKE 'B25J%'   THEN 'ai'
      WHEN cpc LIKE 'A61%'  OR cpc LIKE 'C12%'  OR cpc LIKE 'C07K%'
        OR cpc LIKE 'C07D%' OR cpc LIKE 'G16H%'     THEN 'biomed'
      WHEN cpc LIKE 'G06Q20%' OR cpc LIKE 'G06Q40%' THEN 'fintech'
      ELSE NULL
    END AS industry
  FROM hits
)
SELECT
  t.industry,
  LOWER(t.cc) AS city,
  FORMAT('%dQ%d',
         DIV(MIN(t.filing_date), 10000),
         DIV(MOD(DIV(MIN(t.filing_date), 100), 100) - 1, 3) + 1) AS quarter,
  t.family_id,
  MIN(t.filing_date)      AS first_filing_in_window,
  MIN(t.publication_date) AS first_pub_in_window,
  ANY_VALUE(l.max_pub_in_query) AS max_pub_in_query,
  STRING_AGG(DISTINCT t.assignee, ' | ' ORDER BY t.assignee) AS assignees
FROM tagged AS t
CROSS JOIN latest AS l
WHERE t.industry IS NOT NULL
GROUP BY t.industry, city, t.family_id
ORDER BY t.industry, city, quarter, t.family_id;
