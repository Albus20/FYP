# T1: 研究者存量比值上升的时间分布（只用 window_full=True）
import pandas as pd, numpy as np
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
d=pd.read_csv(R+"clean/researchers_stock_by_quarter.csv")
d["industry"]=d.industry.replace({"fintech_kw":"fintech"})
d=d[d.window_full==True]
print("window_full 起始季：",d.quarter.min())
q4=d[d.quarter.str.endswith("Q4")].copy(); q4["year"]=q4.quarter.str[:4].astype(int)
p=q4.pivot_table(index=["industry","year"],columns="city",values="unique_authors").reset_index()
p["ratio"]=p.hk/p.sg; p["lnr"]=np.log(p.ratio)
for i,g in p.groupby("industry"):
    g=g.set_index("year")
    print(f"\n== {i}")
    print(g[["hk","sg","ratio"]].round(3).to_string())
    tot=g.lnr[2024]-g.lnr[2017]
    print(f"  log 比值总变化 2017→2024: {tot:+.3f}（比值 {g.ratio[2017]:.2f}→{g.ratio[2024]:.2f}）")
    for a,b in [(2017,2020),(2017,2021),(2021,2024),(2020,2024),(2021,2023),(2023,2024)]:
        ch=g.lnr[b]-g.lnr[a]; print(f"  {a}→{b}: Δln比值 {ch:+.3f}  占总变化 {ch/tot*100:5.1f}%")
    # 年度增量
    print("  逐年 Δln比值：", {y:round(g.lnr[y]-g.lnr[y-1],3) for y in range(2018,2025)})
    # 分解：香港增长 vs 新加坡增长
    for a,b in [(2017,2021),(2021,2024),(2017,2024)]:
        print(f"  {a}→{b}: 香港 Δln {np.log(g.hk[b]/g.hk[a]):+.3f}（{(g.hk[b]/g.hk[a]-1)*100:+.1f}%）；新加坡 Δln {np.log(g.sg[b]/g.sg[a]):+.3f}（{(g.sg[b]/g.sg[a]-1)*100:+.1f}%）")
    # 与专利窗口对齐：研究者 2023Q4（窗口 2021–23）与专利 2021–23 同窗口；滞后 1/2 年
    print(f"  同窗对齐：研究者 2023Q4（2021–23 窗口）比值 {g.ratio[2023]:.2f}；滞后 1 年 2022Q4 {g.ratio[2022]:.2f}；滞后 2 年 2021Q4 {g.ratio[2021]:.2f}")
p.to_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/t1_talent_ratio_q4.csv",index=False)
# 季度级：比值的季度路径
dd=d.pivot_table(index=["industry","quarter"],columns="city",values="unique_authors").reset_index()
dd["ratio"]=dd.hk/dd.sg
for i,g in dd.groupby("industry"):
    print(i, " ".join(f"{q}:{r:.2f}" for q,r in zip(g.quarter,g.ratio) if q.endswith(("Q2","Q4"))))
