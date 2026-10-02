from common import *
exec(open("s7_variants.py").read().split("V={")[0])
import csv
basis={}
for r in csv.DictReader(open(OUT/"geo_class.csv",encoding="utf-8")):
    basis[(r["city"],r["pattern"])]=(r["group_hq"],r["basis"])
def info(c,a):
    for cc,p,k in cls:
        if cc==c and p.search(a):
            return basis[(cc,p.pattern)]
    return ("","")
with open(OUT/"top15_company_2021_23.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["city","industry","rank","assignee","families","category","group_hq","basis"])
    for c in ("sg","hk"):
        for i in ("ai","biomed","fintech"):
            cc=collections.Counter()
            for r in rows:
                if r["industry"]==i and r["city"]==c and year(r) in (2021,2022,2023) and is_company_kept(r):
                    for a in fam_company_assignees(r): cc[a]+=1
            for k,(a,n) in enumerate(cc.most_common(15),1):
                g,b=info(c,a); w.writerow([c,i,k,a,n,cat(c,a),g,b])
                print(c,i,k,a,n,cat(c,a),g,sep=" | ")
# V9: 只剔非中资外国跨国公司（两城同剔），保留中资/联想
for y0 in (2015,2021):
    yrs=(y0,y0+1,y0+2)
    for i in ("ai","biomed","fintech"):
        h=count(i,"hk",yrs,{"foreign_mnc"}); s=count(i,"sg",yrs,{"foreign_mnc"})
        print(f"V9 {y0} {i}: HK {h} SG {s} ratio {h/s:.3f}")
