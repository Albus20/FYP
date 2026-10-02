from common import *
import sys
city = sys.argv[1]; N=int(sys.argv[2]) if len(sys.argv)>2 else 15
yrs=(2021,2022,2023)
for i in ("ai","biomed","fintech"):
    sub=[r for r in rows if r["industry"]==i and r["city"]==city and year(r) in yrs and is_company_kept(r)]
    cc=collections.Counter(); solo=collections.Counter()
    for r in sub:
        cps=[a for a in parts(r) if smap.get(a)=="company" and (city,a) not in EX]
        for a in cps: cc[a]+=1
        if len(cps)==1: solo[cps[0]]+=1
    print(f"\n== {i}/{city} 企业族(ali_ant_grp) 2021-23 = {len(sub)}，distinct company assignees {len(cc)}")
    for a,n in cc.most_common(N):
        print(f"  {n:4d}  (solo {solo[a]:4d})  {a}")
