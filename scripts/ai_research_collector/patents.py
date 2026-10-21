"""Generate BigQuery SQL, optionally dry-run/execute, then aggregate downloaded CSV."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))


def sql(start, end):
    prefixes = ' OR '.join("STARTS_WITH(c.code, '%s')" % x for x in CFG['patent_cpc_prefixes'])
    return f'''-- AI-related patent families; HK/SG ASSIGNEE country, not patent office.
-- Window-first filing date is consistent with the original FYP convention.
-- Recent filing years are incomplete because applications publish with a lag.
WITH hits AS (
 SELECT CAST(p.family_id AS STRING) AS family_id, p.publication_number,
        p.filing_date, p.publication_date, a.country_code AS country,
        a.name AS assignee, c.code AS cpc
 FROM `patents-public-data.patents.publications` p,
      UNNEST(p.assignee_harmonized) a, UNNEST(p.cpc) c
 WHERE a.country_code IN ('HK','SG')
   AND p.filing_date BETWEEN {start}0101 AND {end}1231
   AND ({prefixes})
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
'''


def aggregate(file, start, end):
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    counts, seen, assignees = Counter(), set(), set()
    with open(file, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            key = (r['country'], r['family_key'])
            if key in seen:
                raise ValueError('Duplicate country/family: ' + str(key))
            seen.add(key)
            year = int(r['year'])
            if r['country'] not in ('HK','SG') or not start <= year <= end:
                raise ValueError('Country/year outside requested range')
            counts[(year, r['country'], r['id_quality'])] += 1
            for a in r['assignees'].split(' | '):
                if a.strip():
                    assignees.add((r['country'], a.strip()))
    with (out / 'patents_annual.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['year','country','patent_families','missing_family_id_publications'])
        for year in range(start,end+1):
            for cc in ('HK','SG'):
                w.writerow([year,cc,counts[year,cc,'family'],counts[year,cc,'publication_fallback']])
    with (out / 'patent_assignees_to_classify.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['country','assignee','sector'])
        w.writerows((cc,a,'unclassified') for cc,a in sorted(assignees))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',type=int,default=CFG['start_year'])
    p.add_argument('--end',type=int,default=CFG['end_year'])
    p.add_argument('--project',help='Google Cloud project; without this only writes SQL')
    p.add_argument('--execute',action='store_true',help='Actually run billed query; otherwise dry run only')
    p.add_argument('--max-gb',type=float,default=25,help='maximum_bytes_billed in decimal GB')
    p.add_argument('--csv',help='Aggregate a CSV exported by this SQL')
    a=p.parse_args()
    if a.start>a.end:p.error('start > end')
    if a.execute and not a.project:p.error('--execute requires --project')
    q=sql(a.start,a.end)
    target=ROOT/'ai_patents.sql'; target.write_text(q,encoding='utf-8')
    print('SQL ready:',target)
    if a.csv:
        aggregate(a.csv,a.start,a.end)
    if a.project:
        from google.cloud import bigquery
        client=bigquery.Client(project=a.project)
        dry=client.query(q,job_config=bigquery.QueryJobConfig(dry_run=True,use_query_cache=False))
        print('Estimated GB:',dry.total_bytes_processed/1e9)
        if not a.execute:return
        result=client.query(q,job_config=bigquery.QueryJobConfig(maximum_bytes_billed=int(a.max_gb*1e9))).result()
        path=ROOT/'results'/'patents_raw.csv';path.parent.mkdir(exist_ok=True)
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow([s.name for s in result.schema]);w.writerows(tuple(r) for r in result)
        aggregate(path,a.start,a.end)
        print('Saved:',path)


if __name__=='__main__':main()
