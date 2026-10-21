-- AI-related patent families; HK/SG ASSIGNEE country, not patent office.
-- Window-first filing date is consistent with the original FYP convention.
-- Recent filing years are incomplete because applications publish with a lag.
WITH hits AS (
 SELECT CAST(p.family_id AS STRING) AS family_id, p.publication_number,
        p.filing_date, p.publication_date, a.country_code AS country,
        a.name AS assignee, c.code AS cpc
 FROM `patents-public-data.patents.publications` p,
      UNNEST(p.assignee_harmonized) a, UNNEST(p.cpc) c
 WHERE a.country_code IN ('HK','SG')
   AND p.filing_date BETWEEN 20150101 AND 20251231
   AND (STARTS_WITH(c.code, 'G06N') OR STARTS_WITH(c.code, 'G06V') OR STARTS_WITH(c.code, 'G10L') OR STARTS_WITH(c.code, 'G06F40') OR STARTS_WITH(c.code, 'B25J'))
), valid AS (
 SELECT *, CASE WHEN family_id IS NULL OR family_id IN ('','0','-1')
                THEN CONCAT('PUBLICATION:',publication_number)
                ELSE CONCAT('FAMILY:',family_id) END AS family_key
 FROM hits
)
SELECT country, family_key,
       IF(STARTS_WITH(family_key,'FAMILY:'),'family','publication_fallback') AS id_quality,
       MIN(filing_date) AS first_filing_in_window,
       DIV(MIN(filing_date),10000) AS year,
       FORMAT('%dQ%d', DIV(MIN(filing_date),10000),
              DIV(MOD(DIV(MIN(filing_date),100),100)-1,3)+1) AS quarter,
       MIN(NULLIF(publication_date,0)) AS first_publication_of_hits,
       MAX(publication_date) AS latest_publication_of_hits,
       STRING_AGG(DISTINCT assignee,' | ' ORDER BY assignee) AS assignees,
       STRING_AGG(DISTINCT cpc,' | ' ORDER BY cpc) AS cpc_codes,
       STRING_AGG(DISTINCT publication_number,' | ' ORDER BY publication_number) AS publication_numbers
FROM valid
GROUP BY country,family_key
ORDER BY country,year,family_key;
