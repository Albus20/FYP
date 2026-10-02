import pandas as pd, numpy as np
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
# (1) 专利末端截断：各年下半年族数占全年比例（企业主口径+大学），两城对比
for kind in ["company_ali_ant_grp","university"]:
    d=pd.read_csv(G+f"raw/patents_families_by_quarter_{kind}.csv"); d["y"]=d.quarter.str[:4].astype(int); d["q"]=d.quarter.str[-1].astype(int)
    t=d.groupby(["city","y"]).apply(lambda g: g[g.q>=3].patent_families.sum()/g.patent_families.sum(),include_groups=False).unstack("y")
    print(kind,"下半年(Q3+Q4)占全年比例：\n",t.round(2).to_string())
    q=d[d.y==2023].groupby(["city","q"]).patent_families.sum().unstack("q"); print(" 2023 各季：\n",q.to_string())
# (2) 9/11 与 10/2 两版 OpenAlex 的论文港/星比值逐年
w9=pd.read_csv(G+"clean/intl_collab_by_quarter.csv"); w9["industry"]=w9.industry.replace({"fintech_kw":"fintech"}); w9["y"]=w9.quarter.str[:4].astype(int)
w10=pd.read_csv(G+"raw/openalex_intl_cn_by_quarter.csv"); w10["industry"]=w10.industry.replace({"fintech_kw":"fintech"}); w10["y"]=w10.quarter.str[:4].astype(int)
for name,w in [("9/11",w9),("10/2",w10)]:
    a=w.groupby(["industry","city","y"]).works.sum().unstack("city"); r=(a.hk/a.sg).unstack("y")
    print(f"\n论文港/星比值（{name} 版）：\n",r.round(2).to_string())
# (3) 机构层：港八大 vs 新加坡两校 总产出
inst=pd.read_csv(G+"clean/institutions_works_series.csv")
print(inst.to_string())
yrs=[str(y) for y in range(2015,2025)]
hk=inst[inst.group=="hk8"][yrs].sum(); sg=inst[inst.group=="sg"][yrs].sum()
print("\nHK8 合计 / SG 合计：", " ".join(f"{y}:{hk[y]/sg[y]:.2f}" for y in yrs))
