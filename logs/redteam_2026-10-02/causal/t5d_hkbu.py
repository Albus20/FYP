# T5d: 浸会大学申请主体消失对大学专利比值的影响（按族计：族内只要有一个大学申请人即计入，与官方 university 序列核对）
import pandas as pd
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
raw=pd.read_csv(G+"raw/patents_families_raw.csv",dtype={"family_id":str}); raw["year"]=raw.quarter.str[:4].astype(int)
sec=pd.read_csv(G+"config/patents_assignee_sector.csv"); smap=dict(zip(sec.assignee.str.strip(),sec.sector.str.strip()))
raw["un"]=raw.assignees.astype(str).apply(lambda s:[a.strip() for a in s.split("|") if smap.get(a.strip())=="university"])
U=raw[raw.un.str.len()>0].copy()
off=pd.read_csv(G+"raw/patents_families_by_quarter_university.csv"); off["year"]=off.quarter.str[:4].astype(int)
o=off.groupby(["industry","city","year"]).patent_families.sum()
m=U.groupby(["industry","city","year"]).size()
print("与官方 university 序列一致：", bool((o.reindex(m.index)==m).all()), "；官方总数", int(o.sum()), "重建", int(m.sum()))
U["hkbu_only"]=U.un.apply(lambda l: all("BAPTIST" in a for a in l))
for ind in ["biomed","ai"]:
    s=U[U.industry==ind]
    def w(df,c,a,b): return len(df[(df.city==c)&df.year.between(a,b)])
    h0,h1,g0,g1=w(s,"hk",2015,2017),w(s,"hk",2021,2023),w(s,"sg",2015,2017),w(s,"sg",2021,2023)
    x=s[~s.hkbu_only]; H0,H1=w(x,"hk",2015,2017),w(x,"hk",2021,2023)
    print(f"{ind}: 基线 HK {h0}→{h1} SG {g0}→{g1} 比值 {h0/g0:.2f}→{h1/g1:.2f}；剔除仅浸会申请的族 HK {H0}→{H1} 比值 {H0/g0:.2f}→{H1/g1:.2f}；浸会族数 {h0-H0}→{h1-H1}")
