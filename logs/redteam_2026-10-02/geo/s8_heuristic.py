from common import *
import csv, re
exec(open("s7_variants.py").read().split("V={")[0])  # reuse cat(), count()
# 对称名称启发式：「品牌 + 本城地名/亚太」后缀 → 疑似外地集团在本城的子公司
SUF={"hk":re.compile(r"\b(HK|H K|HONG ?KONG|HONGKONG)\b.*\b(LTD|LIMITED|CO)\b|\((HK|HONG KONG)\)"),
     "sg":re.compile(r"\b(SINGAPORE|SG|ASIA|ASIA PACIFIC|APAC)\b.*\b(PTE|PRIVATE|LTD|LIMITED)\b|\((SINGAPORE|S|ASIA PACIFIC)\)")}
EXCL_HK=re.compile(r"^(UNIV|THE HONG KONG|HONG KONG (APPLIED|PRODUCTIVITY|SCIENCE|R&D|CENTRE|CENTER|POLYTECHNIC|BAPTIST|INSTITUTE|UNIVERSITY))")
def cat2(c,a):
    k=cat(c,a)
    if k=="unclassified":
        if SUF[c].search(a) and not (c=="hk" and a.startswith("HONG KONG")):  # 以「HONG KONG」开头者多为本地机构，不按后缀计
            return "suffix_suspect"
    return k
def count2(i,c,yrs,drop):
    n=0; sus=collections.Counter()
    for r in rows:
        if r["industry"]!=i or r["city"]!=c or year(r) not in yrs or not is_company_kept(r): continue
        ks=[cat2(c,a) for a in fam_company_assignees(r)]
        if all(k in drop for k in ks): continue
        n+=1
    return n
D1={"foreign_mnc","mainland_grp","lenovo","hk_grp"}
for y0 in (2015,2021):
  yrs=(y0,y0+1,y0+2)
  for i in ("ai","biomed","fintech"):
    h=count2(i,"hk",yrs,D1|{"suffix_suspect"}); s=count2(i,"sg",yrs,D1|{"suffix_suspect"})
    h2=count2(i,"hk",yrs,D1|{"suffix_suspect","uncertain"}); s2=count2(i,"sg",yrs,D1|{"suffix_suspect","uncertain"})
    print(f"{y0} {i:8s} V7(V1+后缀疑似) HK {h} SG {s} ratio {h/s:.3f} | V8(V7+不确定) HK {h2} SG {s2} ratio {h2/s2:.3f}")
# 列出被后缀规则命中的名字（2021-23）
for c in ("hk","sg"):
    cc=collections.Counter()
    for r in rows:
        if r["city"]!=c or year(r) not in (2021,2022,2023) or not is_company_kept(r): continue
        for a in fam_company_assignees(r):
            if cat2(c,a)=="suffix_suspect": cc[a]+=1
    print(c, "后缀命中", len(cc), "名", sum(cc.values()), "族次；前 20：", cc.most_common(20))
