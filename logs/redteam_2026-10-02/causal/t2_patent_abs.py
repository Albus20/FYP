# T2: 企业/大学/公共研究机构专利 两城绝对年度序列 + 比值变化分解
import pandas as pd, numpy as np
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/raw/"
out=[]
for kind in ["company_ali_ant_grp","company_ali_grp","company_asis","university","public_rd"]:
    d=pd.read_csv(R+f"patents_families_by_quarter_{kind}.csv"); d["year"]=d.quarter.str[:4].astype(int)
    a=d.groupby(["industry","city","year"]).patent_families.sum().unstack("year"); a["kind"]=kind
    out.append(a.reset_index())
A=pd.concat(out)
pd.set_option("display.width",250)
for kind in ["company_ali_ant_grp","university","public_rd","company_asis"]:
    print(f"\n######## {kind}（年度族数）")
    print(A[A.kind==kind].drop(columns="kind").set_index(["industry","city"]).to_string())
A.to_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/t2_patent_annual.csv",index=False)
# 分解：三年合计 2015–17 vs 2021–23 的 ln 比值变化 = ln(HK 增长) - ln(SG 增长)
print("\n######## 分解：2015–17 → 2021–23 三年合计")
for kind in ["company_ali_ant_grp","university","public_rd"]:
    for ind in ["ai","biomed","fintech"]:
        s=A[(A.kind==kind)&(A.industry==ind)].set_index("city")
        h0=s.loc["hk",[2015,2016,2017]].sum(); h1=s.loc["hk",[2021,2022,2023]].sum()
        g0=s.loc["sg",[2015,2016,2017]].sum(); g1=s.loc["sg",[2021,2022,2023]].sum()
        if min(h0,g0,h1,g1)==0: 
            print(f"  {kind:22s}{ind:8s} HK {h0:.0f}→{h1:.0f}  SG {g0:.0f}→{g1:.0f}  （有零，跳过分解）"); continue
        dh=np.log(h1/h0); dg=np.log(g1/g0); dr=dh-dg
        print(f"  {kind:22s}{ind:8s} HK {h0:.0f}→{h1:.0f} ({(h1/h0-1)*100:+.0f}%, Δln {dh:+.2f})  SG {g0:.0f}→{g1:.0f} ({(g1/g0-1)*100:+.0f}%, Δln {dg:+.2f})  比值 {h0/g0:.2f}→{h1/g1:.2f} Δln {dr:+.2f}；新加坡增长占比值下降的 {(dg/(-dr))*100 if dr<0 else float('nan'):.0f}%")
# 峰值后：香港企业专利是否绝对下降
print("\n######## 企业专利（剔阿里蚂蚁）各城 峰值年与 2023 相对峰值")
for ind in ["ai","biomed","fintech"]:
    for c in ["hk","sg"]:
        s=A[(A.kind=="company_ali_ant_grp")&(A.industry==ind)].set_index("city").loc[c,list(range(2015,2024))]
        print(f"  {ind}/{c}: 峰值 {s.idxmax()} = {s.max():.0f}；2023 = {s[2023]:.0f}（峰值的 {s[2023]/s.max()*100:.0f}%）；2015–17 均 {s[[2015,2016,2017]].mean():.1f} → 2021–23 均 {s[[2021,2022,2023]].mean():.1f}")
