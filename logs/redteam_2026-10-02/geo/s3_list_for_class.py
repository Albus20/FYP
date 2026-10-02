from common import *
# company assignees (excluding ali/ant list) by city, families across all industries, windows 2015-17 and 2021-23
cnt=collections.defaultdict(collections.Counter)
tot=collections.Counter()
for r in rows:
    y=year(r)
    w = "w1" if y in (2015,2016,2017) else ("w3" if y in (2021,2022,2023) else None)
    if not w or not is_company_kept(r): continue
    tot[(r["city"],r["industry"],w)]+=1
    for a in parts(r):
        if smap.get(a)=="company" and (r["city"],a) not in EX:
            cnt[(r["city"],a)][(r["industry"],w)]+=1
lst=[(c,a,sum(v.values()),dict(v)) for (c,a),v in cnt.items()]
lst.sort(key=lambda x:(x[0],-x[2]))
import csv
with open(OUT/"company_assignees_w1w3.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["city","assignee","n_total","detail"])
    for c,a,n,d in lst: w.writerow([c,a,n,d])
for c in ("hk","sg"):
    big=[x for x in lst if x[0]==c and x[2]>=3]
    print(c, "assignees >=3:", len(big), "covering", sum(x[2] for x in big), "of", sum(x[2] for x in lst if x[0]==c))
print(tot)
