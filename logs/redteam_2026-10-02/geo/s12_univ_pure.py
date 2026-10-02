from common import *
idx=collections.defaultdict(set)
for r in rows: idx[(r["industry"],r["family_id"])].add(r["city"])
for y0 in (2015,2021):
    yrs=(y0,y0+1,y0+2)
    for i in ("ai","biomed"):
        out={}
        for c in ("hk","sg"):
            u=[r for r in rows if r["industry"]==i and r["city"]==c and year(r) in yrs and "university" in secs(r)]
            pure=[r for r in u if not ({"public_rd"}&secs(r)) and not is_company_kept(r)]
            frac=sum(0.5 if len(idx[(i,r["family_id"])])==2 else 1 for r in u)
            out[c]=(len(u),len(pure),frac)
        h,s=out["hk"],out["sg"]
        print(f"{y0} {i}: 基线 {h[0]}/{s[0]}={h[0]/s[0]:.3f} | 纯大学（不与企业/公共机构共同申请）{h[1]}/{s[1]}={h[1]/s[1]:.3f} | 跨城族各记 0.5 {h[2]}/{s[2]}={h[2]/s[2]:.3f}")
