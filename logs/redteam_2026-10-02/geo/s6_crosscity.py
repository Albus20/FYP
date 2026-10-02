from common import *
idx=collections.defaultdict(dict)
for r in rows: idx[(r["industry"],r["family_id"])][r["city"]]=r
both=[(k,v) for k,v in idx.items() if len(v)==2]
print("跨城族（同产业同时出现在 hk 与 sg）:", len(both), "of", len(idx))
cnt=collections.Counter()
for (i,f),v in both:
    y=year(v["hk"]); ys=year(v["sg"])
    w="w3" if y in (2021,2022,2023) else ("w1" if y in (2015,2016,2017) else "other")
    hs=secs(v["hk"]); ss=secs(v["sg"])
    hk_c=is_company_kept(v["hk"]); sg_c=is_company_kept(v["sg"])
    cnt[(i,w,"company_both" if hk_c and sg_c else "")]+=0
    print(i, f, v["hk"]["quarter"], v["sg"]["quarter"], "| HK:", v["hk"]["assignees"], "| SG:", v["sg"]["assignees"], "| hk_comp",hk_c,"sg_comp",sg_c, "hk_uni","university" in hs,"sg_uni","university" in ss)
