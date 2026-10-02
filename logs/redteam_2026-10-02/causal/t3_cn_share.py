# T3: 香港/新加坡论文中有内地机构参与的比例（10/2 版 OpenAlex）
import pandas as pd, numpy as np
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
d=pd.read_csv(G+"raw/openalex_intl_cn_by_quarter.csv"); d["industry"]=d.industry.replace({"fintech_kw":"fintech"})
d["year"]=d.quarter.str[:4].astype(int)
y=d.groupby(["industry","city","year"])[["works","intl_works","cn_any_works","cn_only_works"]].sum().reset_index()
y["cn_any_share"]=y.cn_any_works/y.works; y["cn_only_share"]=y.cn_only_works/y.works
y["noncn_works"]=y.works-y.cn_any_works
y.to_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/t3_cn_share_by_year.csv",index=False)
pd.set_option("display.width",250)
for ind in ["ai","biomed","fintech"]:
    print(f"\n=== {ind}")
    t=y[y.industry==ind].pivot(index="year",columns="city",values=["works","cn_any_share","noncn_works"])
    t[("ratio","works")]=t[("works","hk")]/t[("works","sg")]
    t[("ratio","noncn")]=t[("noncn_works","hk")]/t[("noncn_works","sg")]
    print(t.round(3).to_string())
    a=y[(y.industry==ind)].set_index(["city","year"])
    for c in ["hk","sg"]:
        w0=a.loc[(c,slice(2015,2017)),"works"].sum(); w1=a.loc[(c,slice(2022,2024)),"works"].sum()
        c0=a.loc[(c,slice(2015,2017)),"cn_any_works"].sum(); c1=a.loc[(c,slice(2022,2024)),"cn_any_works"].sum()
        print(f"  {c}: 2015–17 → 2022–24 论文 {w0}→{w1}（+{w1-w0}）；含内地 {c0}→{c1}（+{c1-c0}）；增量中含内地占 {(c1-c0)/(w1-w0)*100:.0f}%；含内地占比 {c0/w0:.3f}→{c1/w1:.3f}")
    h=a.loc["hk"]; s=a.loc["sg"]
    r_all0=h.loc[2015:2017,"works"].sum()/s.loc[2015:2017,"works"].sum(); r_all1=h.loc[2022:2024,"works"].sum()/s.loc[2022:2024,"works"].sum()
    r_n0=h.loc[2015:2017,"noncn_works"].sum()/s.loc[2015:2017,"noncn_works"].sum(); r_n1=h.loc[2022:2024,"noncn_works"].sum()/s.loc[2022:2024,"noncn_works"].sum()
    print(f"  港/星论文比值 2015–17 {r_all0:.2f} → 2022–24 {r_all1:.2f}；剔除含内地论文后 {r_n0:.2f} → {r_n1:.2f}")
    print(f"  ln 比值变化：全部 {np.log(r_all1/r_all0):+.3f}；非内地 {np.log(r_n1/r_n0):+.3f}；→ 比值上升中可由内地合作扩张解释的份额 ≈ {(1-np.log(r_n1/r_n0)/np.log(r_all1/r_all0))*100:.0f}%")
# 与 9/11 版 works 对比
w9=pd.read_csv(G+"clean/intl_collab_by_quarter.csv"); w9["industry"]=w9.industry.replace({"fintech_kw":"fintech"}); w9["year"]=w9.quarter.str[:4].astype(int)
w9y=w9.groupby(["industry","city","year"]).works.sum()
cmp=y.set_index(["industry","city","year"]).works.to_frame("v1002").join(w9y.rename("v0911"))
cmp["diff%"]=(cmp.v1002/cmp.v0911-1)*100
print("\n10/2 vs 9/11 works 差异（%）：\n",cmp["diff%"].unstack("year").round(1).to_string())
