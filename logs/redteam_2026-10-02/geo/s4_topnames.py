from common import *
names=collections.defaultdict(dict)
for c in ("hk","sg"):
  for y0 in (2015,2021):
    yrs=(y0,y0+1,y0+2)
    for i in ("ai","biomed","fintech"):
        cc=collections.Counter()
        for r in rows:
            if r["industry"]==i and r["city"]==c and year(r) in yrs and is_company_kept(r):
                for a in parts(r):
                    if smap.get(a)=="company" and (c,a) not in EX: cc[a]+=1
        top=cc.most_common(15)
        thr=top[-1][1] if top else 0
        for a,n in cc.items():
            if n>=thr and n>=2:
                names[(c,a)][f"{i}{y0}"]=n
for (c,a),d in sorted(names.items()):
    print(c, "|", a, "|", d)
print(len(names))
