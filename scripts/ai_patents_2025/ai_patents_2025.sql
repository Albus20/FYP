-- GoogleSQL / Standard SQL. HK/SG by harmonized assignee country.
-- Preserve the original 2015 window BEFORE selecting the 2025 cohort.
-- Not priority-year or publication-year counts. Same AI CPC scope as prior FYP.
WITH hits AS (
 SELECT CAST(p.family_id AS STRING) AS family_id,
        p.filing_date, p.publication_date, a.country_code AS cc,
        a.name AS assignee
 FROM `patents-public-data.patents.publications` AS p,
      UNNEST(p.assignee_harmonized) AS a
 WHERE a.country_code IN ('HK','SG')
   AND p.filing_date BETWEEN 20150101 AND 20251231
   AND EXISTS (
     SELECT 1 FROM UNNEST(p.cpc) AS c
     WHERE STARTS_WITH(c.code,'G06N') OR STARTS_WITH(c.code,'G06V')
        OR STARTS_WITH(c.code,'G10L') OR STARTS_WITH(c.code,'G06F40')
        OR STARTS_WITH(c.code,'B25J')
   )
), grouped AS (
 SELECT 'ai' AS industry, LOWER(cc) AS city, family_id,
        MIN(filing_date) AS first_filing_in_window,
        MIN(NULLIF(publication_date,0)) AS first_pub_in_window,
        MAX(publication_date) AS last_pub_of_family,
        STRING_AGG(DISTINCT assignee,' | ' ORDER BY assignee) AS assignees
 FROM hits
 GROUP BY city,family_id
 HAVING MIN(filing_date) BETWEEN 20250101 AND 20251231
)
SELECT industry,city,
       FORMAT('2025Q%d',DIV(MOD(DIV(first_filing_in_window,100),100)-1,3)+1) AS quarter,
       family_id,first_filing_in_window,first_pub_in_window,last_pub_of_family,assignees
FROM grouped
ORDER BY city,quarter,family_id;
