# T4/T5 补充：末期窗口替换、单年比值、过度离散放大后的水平区间、剪刀差斜率差检验
import pandas as pd, numpy as np
W="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/measure/"
pat=pd.read_pickle(W+"pat.pkl")
PHI={("university","ai"):3.10,("university","biomed"):2.07,("company","ai"):4.95,("company","biomed"):2.61,("company","fintech"):2.32}
print("=== 不同末期窗口的 港/星（族数比）===")
for col in ("university","company"):
    for i in ("ai","biomed","fintech"):
        s=pat[pat[col]&(pat.industry==i)].groupby(["city","year"]).size().unstack("year").reindex(columns=range(2015,2024),fill_value=0).fillna(0)
        h,g=s.loc["hk"],s.loc["sg"]
        w=lambda a,b:(h.loc[a:b].sum()/g.loc[a:b].sum() if g.loc[a:b].sum() else np.nan)
        single=" ".join(f"{y}:{h[y]/g[y]:.2f}" if g[y] else f"{y}:NA" for y in range(2015,2024))
        phi=PHI.get((col,i),np.nan)
        hh,gg=h.loc[2021:2023].sum(),g.loc[2021:2023].sum()
        se=np.sqrt(1/hh+1/gg)*np.sqrt(phi) if hh and gg and phi==phi else np.nan
        r=hh/gg if gg else np.nan
        print(f"{col:10s} {i:7s} 2021–23 {w(2021,2023):.3f} | 2020–22 {w(2020,2022):.3f} | 2019–21 {w(2019,2021):.3f} | 2022–23 {w(2022,2023):.3f}"
              + (f" | 2021–23 过度离散 95%区间 [{r*np.exp(-1.96*se):.2f},{r*np.exp(1.96*se):.2f}]" if se==se else ""))
        print(f"           单年：{single}")
# 剪刀差：专利斜率 vs 研究者斜率（研究者斜率当作已知常数）
print("\n=== 剪刀差检验：专利 log(港/星) 年斜率 是否显著低于 研究者 年斜率 ===")
slopes={"university":{"ai":(-0.064,-0.246,0.118),"biomed":(-0.007,-0.071,0.058)},
        "company":{"ai":(-0.067,-0.168,0.033),"biomed":(-0.089,-0.134,-0.043),"fintech":(0.039,-0.082,0.160)}}
rsl={"ai":0.054,"biomed":0.043,"fintech":0.113}
for col,d in slopes.items():
    for i,(b,lo,hi) in d.items():
        se=(hi-lo)/(2*1.96); z=(b-rsl[i])/se
        print(f"  {col:10s} {i:7s} 专利斜率 {b:+.3f}  研究者斜率 {rsl[i]:+.3f}  差 {b-rsl[i]:+.3f}  z={z:+.2f}  {'显著（单侧5%）' if z<-1.645 else '不显著'}")
