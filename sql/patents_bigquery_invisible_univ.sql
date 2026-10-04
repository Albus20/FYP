-- ============================================================================
-- FYP · 红队 P1 检查 ①：「看不见」的大学专利（J12，2026-10-04）
-- 规则：docs/红队审查_2026-10-02.md「需要补做的检查」P1 第 1 条（10/2 写定）
--
-- 现有专利数据按「申请人国别 = HK／SG」筛选。只在内地申请、或挂在港校深圳研究院（内地法人）、
-- NUS 苏州／重庆研究院名下的专利，申请人国别不是 HK／SG，因此看不见。
-- 本查询**不加国别条件**，按申请人名称找港星大学（含其内地研究院）的专利族，并带出每个家族的全部
-- 申请人、申请人国别、公开国别。哪些是「看不见的」，在本地与 raw/patents_families_raw.csv 比对后判定。
-- 也用来核查浸会大学 2018 年后的申请主体去向（看 assignees 列里的名称随年份的变化）。
--
-- 名称匹配故意放宽（宁多勿漏），本地再按名单逐条归类。
-- 成本：两次扫描，估计 30–60 GB，免费额度（每月 1 TB）内。点运行前先看右上角 "This query will process X"。
-- 导出 → raw/patents_invisible_univ_families.csv
-- 表头：industry,family_id,first_filing,first_pub,has_hk_sg_cc,assignee_ccs,pub_countries,assignees
-- ============================================================================

WITH cand AS (
  SELECT DISTINCT p.family_id
  FROM `patents-public-data.patents.publications` AS p,
    UNNEST(p.assignee_harmonized) AS a
  WHERE p.filing_date BETWEEN 20150101 AND 20241231
    AND p.family_id != '-1'
    AND (
      (REGEXP_CONTAINS(UPPER(a.name), r'HONG KONG|HKUST')
         AND REGEXP_CONTAINS(UPPER(a.name), r'UNIV|POLYTECHNIC|HKUST|LINGNAN'))
      OR (REGEXP_CONTAINS(UPPER(a.name), r'SINGAPORE')
         AND REGEXP_CONTAINS(UPPER(a.name), r'UNIV'))
      OR REGEXP_CONTAINS(UPPER(a.name), r'NANYANG TECH')
    )
),
pubs AS (
  SELECT p.family_id, p.filing_date, p.publication_date, p.country_code AS pub_country,
         p.assignee_harmonized, p.cpc
  FROM `patents-public-data.patents.publications` AS p
  JOIN cand USING (family_id)
  WHERE p.filing_date BETWEEN 20150101 AND 20241231
),
ind AS (
  SELECT DISTINCT pubs.family_id,
    CASE
      WHEN c.code LIKE 'G06N%'   OR c.code LIKE 'G06V%' OR c.code LIKE 'G10L%'
        OR c.code LIKE 'G06F40%' OR c.code LIKE 'B25J%'   THEN 'ai'
      WHEN c.code LIKE 'A61%'  OR c.code LIKE 'C12%'  OR c.code LIKE 'C07K%'
        OR c.code LIKE 'C07D%' OR c.code LIKE 'G16H%'     THEN 'biomed'
      WHEN c.code LIKE 'G06Q20%' OR c.code LIKE 'G06Q40%' THEN 'fintech'
      ELSE NULL
    END AS industry
  FROM pubs, UNNEST(pubs.cpc) AS c
),
fam AS (
  SELECT pubs.family_id,
    MIN(pubs.filing_date)      AS first_filing,
    MIN(pubs.publication_date) AS first_pub,
    LOGICAL_OR(a.country_code IN ('HK', 'SG')) AS has_hk_sg_cc,
    STRING_AGG(DISTINCT a.country_code, '|' ORDER BY a.country_code) AS assignee_ccs,
    STRING_AGG(DISTINCT pubs.pub_country, '|' ORDER BY pubs.pub_country) AS pub_countries,
    STRING_AGG(DISTINCT a.name, ' | ' ORDER BY a.name) AS assignees
  FROM pubs, UNNEST(pubs.assignee_harmonized) AS a
  GROUP BY pubs.family_id
)
SELECT i.industry, f.*
FROM fam AS f
JOIN ind AS i USING (family_id)
WHERE i.industry IS NOT NULL
ORDER BY i.industry, f.first_filing, f.family_id;
