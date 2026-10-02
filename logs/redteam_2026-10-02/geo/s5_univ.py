from common import *
for c in ("hk","sg"):
  for i in ("ai","biomed","fintech"):
    for y0 in (2015,2021):
        yrs=(y0,y0+1,y0+2)
        sub=[r for r in rows if r["industry"]==i and r["city"]==c and year(r) in yrs and "university" in secs(r)]
        cc=collections.Counter()
        for r in sub:
            for a in set(parts(r)):
                if smap.get(a)=="university": cc[a]+=1
        print(f"\n== {i}/{c} {y0}-{y0+2} 大学族 {len(sub)}")
        for a,n in cc.most_common(40): print(f"   {n:4d} {a}")
