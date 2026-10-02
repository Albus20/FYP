from common import *
import sys
city = sys.argv[1]; N=int(sys.argv[2]); y0=int(sys.argv[3])
yrs=(y0,y0+1,y0+2)
for i in ("ai","biomed","fintech"):
    sub=[r for r in rows if r["industry"]==i and r["city"]==city and year(r) in yrs and is_company_kept(r)]
    cc=collections.Counter()
    for r in sub:
        for a in [a for a in parts(r) if smap.get(a)=="company" and (city,a) not in EX]: cc[a]+=1
    print(f"\n== {i}/{city} {yrs} 企业族 = {len(sub)}")
    print("   " + "; ".join(f"{a} {n}" for a,n in cc.most_common(N)))
