from common import *
import csv, re
cls=[(r["city"],re.compile(r["pattern"]),r["category"]) for r in csv.DictReader(open(OUT/"geo_class.csv",encoding="utf-8"))]
def cat(city,a):
    for c,p,k in cls:
        if c==city and p.search(a): return k
    return "unclassified"
def fam_company_assignees(r):
    return [a for a in parts(r) if smap.get(a)=="company" and (r["city"],a) not in EX]
def count(i,c,yrs,drop=set(),reassign_in=None):
    """家族级：该族全部 company 申请人（剔阿里蚂蚁后）都属于 drop 类 → 剔除"""
    n=0
    for r in rows:
        if r["industry"]!=i or r["city"]!=c or year(r) not in yrs or not is_company_kept(r): continue
        cps=fam_company_assignees(r)
        ks=[cat(c,a) for a in cps]
        if all(k in drop for k in ks): continue
        n+=1
    return n
def moved(i,yrs,catname):
    """sg 侧 catname 类（全部 company 申请人都属该类）的族，且该族不在 hk 侧"""
    hkf={r["family_id"] for r in rows if r["industry"]==i and r["city"]=="hk" and year(r) in yrs and is_company_kept(r)}
    n=0
    for r in rows:
        if r["industry"]!=i or r["city"]!="sg" or year(r) not in yrs or not is_company_kept(r): continue
        ks=[cat("sg",a) for a in fam_company_assignees(r)]
        if ks and all(k==catname for k in ks) and r["family_id"] not in hkf: n+=1
    return n
V={
 "V0 基线（项目口径）": (set(),set()),
 "V1 两城同剔：已判定的外地集团（外国跨国+内地集团+联想）": ({"foreign_mnc","mainland_grp","lenovo","hk_grp"},{"foreign_mnc","mainland_grp","lenovo"}),
 "V2 = V1 + 两城同剔『不确定』": ({"foreign_mnc","mainland_grp","lenovo","hk_grp","uncertain"},{"foreign_mnc","mainland_grp","lenovo","uncertain"}),
 "V3 = V1 + 两城同剔误归 company 的公营机构": ({"foreign_mnc","mainland_grp","lenovo","hk_grp","public_misclass"},{"foreign_mnc","mainland_grp","lenovo","public_misclass"}),
 "V4 仅新加坡剔外资（不对称，上界）": ({"foreign_mnc","mainland_grp","lenovo","hk_grp"},set()),
}
res=[]
for y0 in (2015,2021):
  yrs=(y0,y0+1,y0+2)
  print(f"\n######## 窗口 {y0}-{y0+2}")
  for i in ("ai","biomed","fintech"):
    print(f"  -- {i}")
    for name,(dsg,dhk) in V.items():
        s=count(i,"sg",yrs,dsg); h=count(i,"hk",yrs,dhk)
        print(f"     {name:<48s} HK {h:5d}  SG {s:5d}  ratio {h/s:.3f}")
        res.append((y0,i,name,h,s,h/s))
    # V5: 商汤（香港集团）改归香港；其余同 V1
    s=count(i,"sg",yrs,{"foreign_mnc","mainland_grp","lenovo","hk_grp"}); h=count(i,"hk",yrs,{"foreign_mnc","mainland_grp","lenovo"})+moved(i,yrs,"hk_grp")
    print(f"     {'V5 = V1 + 商汤新加坡主体改归香港':<48s} HK {h:5d}  SG {s:5d}  ratio {h/s:.3f}")
    s0=count(i,"sg",yrs); h0=count(i,"hk",yrs)+moved(i,yrs,"hk_grp"); s0b=s0-moved(i,yrs,"hk_grp")
    print(f"     {'V6 基线 + 商汤改归香港（其余不剔）':<48s} HK {h0:5d}  SG {s0b:5d}  ratio {h0/s0b:.3f}")
# 分类覆盖：每格各类占族数
print("\n######## 各格企业族按类别（家族次，按申请人计，可重叠）")
for y0 in (2015,2021):
  yrs=(y0,y0+1,y0+2)
  for i in ("ai","biomed","fintech"):
    for c in ("hk","sg"):
        cc=collections.Counter(); tot=0
        for r in rows:
            if r["industry"]!=i or r["city"]!=c or year(r) not in yrs or not is_company_kept(r): continue
            tot+=1
            ks={cat(c,a) for a in fam_company_assignees(r)}
            key = list(ks)[0] if len(ks)==1 else "mixed"
            cc[key]+=1
        print(f"  {y0} {i:8s}{c} 共{tot:5d}: " + "  ".join(f"{k} {v}({v/tot:.0%})" for k,v in cc.most_common()))
