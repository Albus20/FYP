# T2b: 新加坡（及香港）企业专利增量由哪些申请人驱动；按族分数归属（一族多个企业申请人时均分）
import pandas as pd, numpy as np
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
raw=pd.read_csv(G+"raw/patents_families_raw.csv",dtype={"family_id":str})
sec=pd.read_csv(G+"config/patents_assignee_sector.csv"); smap=dict(zip(sec.assignee.str.strip(),sec.sector.str.strip()))
exc=pd.read_csv(G+"config/patents_assignee_geo_exclude.csv"); print(exc.columns.tolist())
raw["year"]=raw.quarter.str[:4].astype(int)
rows=[]
for r in raw.itertuples():
    names=[a.strip() for a in str(r.assignees).split("|")]
    secs=[smap.get(a,"UNMAPPED") for a in names]
    comp=[a for a,s in zip(names,secs) if s=="company"]
    rows.append((r.industry,r.city,r.year,r.family_id,names,secs,comp))
F=pd.DataFrame(rows,columns=["industry","city","year","family_id","names","secs","comp"])
print("未归类申请人出现的族数：",sum("UNMAPPED" in s for s in F.secs))
# 复现 build 的 sector 判定：看 patents_build/geo_variants 逻辑再决定；这里先用「含企业申请人」近似并与官方序列核对
F["has_comp"]=F.comp.str.len()>0
exset=set(zip(exc.city,exc.assignee.str.strip())) if "city" in exc.columns else set()
F["all_excl"]=F.apply(lambda r: r.has_comp and all((r.city,a) in exset for a in r.comp),axis=1)
C=F[F.has_comp & ~F.all_excl]
chk=C.groupby(["industry","city","year"]).size().unstack("year")
print("近似重建（含企业申请人、非全被剔）年度族数：\n",chk.to_string())
# 按申请人分数归属
recs=[]
for r in C.itertuples():
    w=1/len(r.comp)
    for a in r.comp: recs.append((r.industry,r.city,r.year,a,w))
P=pd.DataFrame(recs,columns=["industry","city","year","assignee","w"])
P.to_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/t2b_assignee_year_frac.csv",index=False)
def per(ind,city,top=15):
    s=P[(P.industry==ind)&(P.city==city)]
    a=s.pivot_table(index="assignee",columns="year",values="w",aggfunc="sum",fill_value=0)
    for y in range(2015,2024):
        if y not in a.columns: a[y]=0
    a=a[list(range(2015,2024))]
    a["p0"]=a[[2015,2016,2017]].sum(1); a["p1"]=a[[2021,2022,2023]].sum(1); a["delta"]=a.p1-a.p0
    tot=a.delta.sum()
    print(f"\n==== {ind}/{city}：2015–17 合计 {a.p0.sum():.0f} → 2021–23 合计 {a.p1.sum():.0f}，净增 {tot:+.0f}；企业申请人数 {(a.p0>0).sum()} → {(a.p1>0).sum()}")
    b=a.sort_values("delta",ascending=False)
    print("  增量最大的申请人：")
    for n,x in b.head(top).iterrows():
        print(f"   {n[:55]:55s} {x.p0:6.1f} → {x.p1:6.1f}  Δ {x.delta:+6.1f}（占净增 {x.delta/tot*100:5.1f}%） 年度 {' '.join(f'{v:.0f}' for v in x[list(range(2015,2024))])}")
    print("  降幅最大：")
    for n,x in b.tail(5).iterrows():
        print(f"   {n[:55]:55s} {x.p0:6.1f} → {x.p1:6.1f}  Δ {x.delta:+6.1f} 年度 {' '.join(f'{v:.0f}' for v in x[list(range(2015,2024))])}")
    top5=b.head(5).delta.sum(); top10=b.head(10).delta.sum()
    print(f"  前 5 名增量合计 {top5:+.0f}（占净增 {top5/tot*100:.0f}%）；前 10 名 {top10:+.0f}（{top10/tot*100:.0f}%）")
    return a
A={}
for ind in ["ai","biomed","fintech"]:
    for c in ["sg","hk"]:
        A[(ind,c)]=per(ind,c)
import pickle; pickle.dump(A,open("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/t2b_tables.pkl","wb"))
