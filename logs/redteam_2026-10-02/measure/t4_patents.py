# T4/T5: 专利计数口径与小样本 —— 从 raw/patents_families_raw.csv 重建三分序列，检查年份分布、2023 截断、件数
import pandas as pd, numpy as np
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
raw=pd.read_csv(R+"raw/patents_families_raw.csv",dtype=str)
smap=dict(pd.read_csv(R+"config/patents_assignee_sector.csv",dtype=str).apply(lambda r:(r.assignee.strip(),r.sector.strip()),axis=1).tolist())
gx=pd.read_csv(R+"config/patents_assignee_geo_exclude.csv",dtype=str)
EX={(r.city,r.assignee) for r in gx.itertuples()}
raw["parts"]=raw.assignees.fillna("").map(lambda s:[a.strip() for a in s.split(" | ") if a.strip()])
raw["secs"]=raw.parts.map(lambda ps:{smap.get(a) for a in ps})
def is_comp(r):
    cps=[a for a in r.parts if smap.get(a)=="company"]
    if not cps: return False
    hit=[a for a in cps if (r.city,a) in EX]
    return not (hit and len(hit)==len(cps))
raw["company"]=raw.apply(is_comp,axis=1)
raw["university"]=raw.secs.map(lambda s:"university" in s)
raw["public_rd"]=raw.secs.map(lambda s:"public_rd" in s)
raw["year"]=raw.quarter.str[:4].astype(int)
raw["ffy"]=raw.first_filing_in_window.str[:4].astype(int)
print("quarter 年 与 first_filing 年 一致：",(raw.year==raw.ffy).mean())
# 核对与仓库序列一致
for kind,col in (("company_ali_ant_grp","company"),("university","university"),("public_rd","public_rd")):
    ref=pd.read_csv(R+f"raw/patents_families_by_quarter_{kind}.csv")
    mine=raw[raw[col]].groupby(["industry","city","quarter"]).size()
    ref=ref.set_index(["industry","city","quarter"]).patent_families
    diff=(ref-mine.reindex(ref.index,fill_value=0)).abs().sum()
    print(f"重建 {kind} 与仓库序列差异合计：{diff}")
raw.to_pickle("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/measure/pat.pkl")
# 年度件数
for col in ("company","university","public_rd"):
    t=raw[raw[col]].groupby(["industry","city","year"]).size().unstack("year",fill_value=0)
    print(f"\n=== {col} 年度族数 ==="); print(t.to_string())
# 2023 截断检查：2023 / 2021–22 均值；Q4/Q1 份额
print("\n=== 2023 相对 2021–22 均值（全部申请人与分档）===")
for col in ("company","university"):
    t=raw[raw[col]].groupby(["industry","city","year"]).size().unstack("year",fill_value=0)
    out=pd.DataFrame({"y2021":t[2021],"y2022":t[2022],"y2023":t[2023],"r23_vs_2122":t[2023]/((t[2021]+t[2022])/2),"r22_vs_2021":t[2022]/((t[2020]+t[2021])/2),"r21_vs_1920":t[2021]/((t[2019]+t[2020])/2)})
    print(col); print(out.round(2).to_string())
# 季度：2023 下半年份额 vs 2022 下半年份额
print("\n=== 下半年（Q3+Q4）占全年比例 ===")
raw["q"]=raw.quarter.str[-1].astype(int)
for col in ("company","university"):
    s=raw[raw[col]&raw.year.isin([2019,2020,2021,2022,2023])]
    t=s.groupby(["industry","city","year"]).apply(lambda g:(g.q>=3).mean()).unstack("year")
    print(col); print(t.round(2).to_string())
# 月度分布 2023（全部申请人，两城）
raw["month"]=raw.first_filing_in_window.str[4:6].astype(int)
allf=raw.drop_duplicates(["city","family_id"])
m=allf[allf.year.isin([2021,2022,2023])].groupby(["city","year","month"]).size().unstack("month",fill_value=0)
print("\n=== 全部申请人去重族 月度 ==="); print(m.to_string())
