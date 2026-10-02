from common import *
# 复现 2021-23 年均：企业(ali_ant_grp)、大学、公共
import csv
def filesum(kind, i, c, yrs):
    return sum(float(r["patent_families"]) for r in csv.DictReader(open(ROOT/f"raw/patents_families_by_quarter_{kind}.csv")) if r["industry"]==i and r["city"]==c and int(r["quarter"][:4]) in yrs)
for yrs in [(2021,2022,2023),(2015,2016,2017)]:
  print("窗口", yrs)
  for i in ("ai","biomed","fintech"):
    for c in ("hk","sg"):
        sub=[r for r in rows if r["industry"]==i and r["city"]==c and year(r) in yrs]
        comp=sum(1 for r in sub if is_company_kept(r))
        uni=sum(1 for r in sub if "university" in secs(r))
        pub=sum(1 for r in sub if "public_rd" in secs(r))
        print(f"  {i:8s}{c} company {comp} (file {filesum('company_ali_ant_grp',i,c,yrs):.0f}) univ {uni} (file {filesum('university',i,c,yrs):.0f}) pub {pub} (file {filesum('public_rd',i,c,yrs):.0f})")
# 未归类申请人覆盖
unk=collections.Counter()
for r in rows:
    for a in parts(r):
        if a not in smap: unk[(r['city'],a)]+=1
print("未归类申请人 family-rows:", sum(unk.values()), "distinct", len(unk))
