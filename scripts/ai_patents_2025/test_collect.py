"""Offline synthetic tests; no cloud calls, no sample values used as real data."""
import unittest
import csv
import json
import tempfile
import sys
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch, MagicMock
import collect
from collect import classify

class ClassificationTests(unittest.TestCase):
    def rows(self):
        names=['ACME','UNI','EXCLUDED','EXCLUDED | ACME','UNKNOWN','ACME | UNKNOWN','EXCLUDED | UNKNOWN']
        return [{'city':'hk','quarter':'2025Q1','family_id':str(i),'assignees':a} for i,a in enumerate(names,1)]
    def test_mixed_and_unknown(self):
        c,p,u,a=classify(self.rows(),{'ACME':'company','UNI':'university','EXCLUDED':'company'},{('hk','EXCLUDED')})
        self.assertEqual(c['hk','2025Q1'],3)
        self.assertEqual(p['hk','2025Q1'],2)
        self.assertEqual(u['hk','UNKNOWN'],3)
    def test_duplicate(self):
        r=self.rows()[:1]
        with self.assertRaises(ValueError):classify(r+r,{'ACME':'company'},set())
    def test_invalid_family(self):
        r=self.rows()[:1];r[0]['family_id']='0'
        with self.assertRaises(ValueError):classify(r,{'ACME':'company'},set())
    def test_new_group_alias(self):
        r=self.rows()[:1];r[0]['assignees']='ALIBABA NEW ENTITY LTD'
        c,p,u,a=classify(r,{'ALIBABA NEW ENTITY LTD':'company'},set())
        self.assertEqual(sum(c.values()),0)
        self.assertEqual(sum(p.values()),1)

class PipelineTests(unittest.TestCase):
    def setUp(self):
        # Use the package directory so Windows restricted temp folders are avoided.
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root=Path(self.temp.name)
        self.patch=patch.object(collect,'ROOT',self.root);self.patch.start()
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.patch.stop)
        collect.write(self.root/'config/assignee_sectors.csv',['assignee','sector'],[['ACME','company'],['UNI','university']])
        collect.write(self.root/'config/exclusions.csv',['city','assignee','exclude_level'],[])
        (self.root/'ai_patents_2025.sql').write_text('SELECT 1',encoding='utf-8')
    def source(self,rows):
        p=self.root/'input.csv'
        collect.write(p,['industry','city','quarter','family_id','first_filing_in_window','assignees'],rows)
        return p
    def test_pending_stays_blank_and_can_be_resolved(self):
        src=self.source([['ai','hk','2025Q1','1','20250115','NEW ENTITY']])
        out=self.root/'results';collect.aggregate(src,out)
        rows=collect.read(out/'港新AI企业专利_2025年度.csv')
        self.assertEqual(rows[0]['待判断专利族'],'1')
        self.assertEqual(rows[0]['可用于原口径的观察值'],'')
        collect.write(self.root/'config/new_assignees.csv',['assignee','sector'],[['NEW ENTITY','company']])
        collect.aggregate(src,out)
        self.assertEqual(collect.read(out/'港新AI企业专利_2025年度.csv')[0]['可用于原口径的观察值'],'1')
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['complete']);self.assertEqual(len(manifest['input_sha256']),64)
    def test_annual_equals_four_quarters(self):
        src=self.source([['ai',c,f'2025Q{q}',str(q),f'2025{3*q:02d}01','ACME'] for c in ['hk','sg'] for q in range(1,5)])
        out=self.root/'results';collect.aggregate(src,out)
        a=collect.read(out/'港新AI企业专利_2025年度.csv');q=collect.read(out/'港新AI企业专利_2025季度.csv')
        self.assertEqual([x['已确认企业专利族'] for x in a],['4','4'])
        self.assertEqual(sum(int(x['已确认企业专利族']) for x in q),8)
    def test_wrong_year_country_and_quarter_rejected(self):
        for row in [['ai','hk','2024Q1','1','20240101','ACME'],['ai','us','2025Q1','1','20250101','ACME'],['ai','sg','2025Q2','1','20250101','ACME']]:
            with self.subTest(row=row),self.assertRaises(ValueError):collect.aggregate(self.source([row]),self.root/'result')
    def test_missing_headers_rejected(self):
        p=self.root/'bad.csv';p.write_text('title,count\nexample,1\n',encoding='utf-8')
        with self.assertRaises(ValueError):collect.aggregate(p,self.root/'result')
    def test_invalid_manual_sector_rejected(self):
        collect.write(self.root/'config/new_assignees.csv',['assignee','sector'],[['NEW','comapny']])
        with self.assertRaises(ValueError):collect.aggregate(self.source([['ai','hk','2025Q1','1','20250101','NEW']]),self.root/'result')
    def test_cloud_dry_run_and_budget_limit(self):
        google=ModuleType('google');cloud=ModuleType('google.cloud');bq=ModuleType('google.cloud.bigquery')
        client=MagicMock();client.query.return_value.total_bytes_processed=60_000_000_000
        bq.Client=MagicMock(return_value=client);bq.QueryJobConfig=lambda **kw:SimpleNamespace(**kw)
        google.cloud=cloud;cloud.bigquery=bq
        modules={'google':google,'google.cloud':cloud,'google.cloud.bigquery':bq}
        with patch.dict(sys.modules,modules),patch.object(sys,'argv',['collect.py','--project','test-project']):collect.main()
        self.assertEqual(client.query.call_count,1)
        self.assertTrue(client.query.call_args.kwargs['job_config'].dry_run)
        client.reset_mock()
        with patch.dict(sys.modules,modules),patch.object(sys,'argv',['collect.py','--project','test-project','--execute','--max-gb','50']),self.assertRaises(SystemExit):collect.main()
        self.assertEqual(client.query.call_count,1)  # Never submits billed query.
    def test_nonfinite_budget_rejected(self):
        for value in ['nan','inf','0','-1']:
            with self.subTest(value=value),patch.object(sys,'argv',['collect.py','--max-gb',value]),self.assertRaises(SystemExit):collect.main()

class SQLContractTests(unittest.TestCase):
    def test_cohort_filtered_after_family_grouping(self):
        sql=(Path(__file__).resolve().parent/'ai_patents_2025.sql').read_text(encoding='utf-8')
        self.assertIn('p.filing_date BETWEEN 20150101 AND 20251231',sql)
        self.assertIn('HAVING MIN(filing_date) BETWEEN 20250101 AND 20251231',sql)
        self.assertLess(sql.index('GROUP BY city,family_id'),sql.index('HAVING MIN(filing_date)'))
        for prefix in ['G06N','G06V','G10L','G06F40','B25J']:self.assertIn("'"+prefix+"'",sql)

if __name__=='__main__':unittest.main()
