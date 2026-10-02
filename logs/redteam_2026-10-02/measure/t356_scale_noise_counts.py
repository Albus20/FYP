# T3 人均；T5 小样本与趋势；T6 高引论文数
import pandas as pd, numpy as np
from scipy import optimize, stats
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
W="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/measure/"
chain=pd.read_csv(R+"clean/rq1_conversion_chain.csv")
pop=pd.read_csv(R+"raw/worldbank_population_hk_sg.csv").pivot(index="year",columns="city",values="population")
def popratio(years): return pop.loc[list(years),"hk"].mean()/pop.loc[list(years),"sg"].mean()
PR={"2024Q4":popratio([2024]),"2022–24 合计":popratio(range(2022,2025)),"2022–24 合并":popratio(range(2022,2025)),
    "2022–24 年均":popratio(range(2022,2025)),"2021–23 年均":popratio(range(2021,2024))}
print("人口比 港/星：",{k:round(v,4) for k,v in PR.items()})
chain["pop_ratio"]=chain.window.map(PR)
chain["is_share"]=chain.stage.eq("高引占比")
chain["ratio_pc"]=np.where(chain.is_share,chain.ratio,chain.ratio/chain.pop_ratio)
print("\n=== T3 链条各段 原值 vs 人均（高引占比是比例，不除人口）===")
print(chain[["industry","stage","window","ratio","pop_ratio","ratio_pc"]].round(3).to_string(index=False))
# 研究端 / 知识产权段 落差倍数（人均不变性）
for i in ("ai","biomed","fintech"):
    c=chain[chain.industry==i].set_index("stage")
    for ip in ("大学专利","企业专利"):
        if ip in c.index:
            print(f"  {i} 论文数→{ip} 落差倍数 原值 {c.loc[ip,'ratio']/c.loc['论文数','ratio']:.3f} 人均 {c.loc[ip,'ratio_pc']/c.loc['论文数','ratio_pc']:.3f}")
# 剪刀差 人均
sc=pd.read_csv(R+"clean/rq1_scissors_by_year.csv")
def pr_row(r):
    if r.series=="研究者存量": return popratio([r.year])
    return popratio(range(r.year-2,r.year+1))
sc["ratio_pc"]=sc.ratio/sc.apply(pr_row,axis=1)
print("\n=== T3 剪刀差 人均 ===")
print(sc.pivot_table(index=["industry","series"],columns="year",values="ratio_pc").round(2).to_string())

# ---- T6 高引论文数 ----
t=pd.read_csv(R+"clean/top10pct_by_year.csv")
t["industry"]=t.industry.str.replace(r"^fintech.*","fintech",regex=True)
t=t[t.period.astype(str).str.fullmatch(r"\d{4}")]
t["year"]=t.period.astype(int)
g=t[t.year.between(2022,2024)].groupby(["industry","city"])[["works","works_with_cnp","top10_works","top1_works"]].sum()
g["share10"]=g.top10_works/g.works_with_cnp; g["share1"]=g.top1_works/g.works_with_cnp
u=g.unstack("city")
out=pd.DataFrame({"top10_hk":u[("top10_works","hk")],"top10_sg":u[("top10_works","sg")],
  "top10_count_ratio":u[("top10_works","hk")]/u[("top10_works","sg")],
  "top10_share_ratio":u[("share10","hk")]/u[("share10","sg")],
  "top1_hk":u[("top1_works","hk")],"top1_sg":u[("top1_works","sg")],
  "top1_count_ratio":u[("top1_works","hk")]/u[("top1_works","sg")],
  "top1_share_ratio":u[("share1","hk")]/u[("share1","sg")],
  "cnp_cov_hk":u[("works_with_cnp","hk")]/u[("works","hk")],"cnp_cov_sg":u[("works_with_cnp","sg")]/u[("works","sg")]})
out["top10_count_ratio_pc"]=out.top10_count_ratio/popratio(range(2022,2025))
# 10/2 版本论文比值缩放（假设高引占比不变）
v911=pd.read_csv(R+"clean/intl_collab_by_quarter.csv"); v1002=pd.read_csv(R+"raw/openalex_intl_cn_by_quarter.csv")
def wr(d):
    d=d.copy(); d["industry"]=d.industry.str.replace(r"^fintech.*","fintech",regex=True)
    d=d[d.quarter.str[:4].astype(int).between(2022,2024)].groupby(["industry","city"]).works.sum().unstack(); return d.hk/d.sg
scale=wr(v1002)/wr(v911)
out["top10_count_ratio_v1002_scaled"]=out.top10_count_ratio*scale
print("\n=== T6 高引论文数（2022–24）===")
print(out.round(3).T.to_string())
# 每 100 篇论文的专利（转化率）港/星
print("\n=== T6 替代：每千篇论文的专利族（2021–23 专利 vs 2021–23 论文，9/11 版本）===")
v=v911.copy(); v["industry"]=v.industry.str.replace(r"^fintech.*","fintech",regex=True)
pp=v[v.quarter.str[:4].astype(int).between(2021,2023)].groupby(["industry","city"]).works.sum()
pat=pd.read_pickle(W+"pat.pkl")
for col in ("university","company"):
    pc=pat[pat[col]&pat.year.between(2021,2023)].groupby(["industry","city"]).size()
    rate=(pc/pp*1000).unstack()
    rate["ratio"]=rate.hk/rate.sg
    print(col); print(rate.round(2).to_string())

# ---- T5 小样本：比值的泊松置信区间与趋势 ----
print("\n=== T5 2021–23 三年合计 比值与 95% 区间（条件二项精确区间）===")
def ratio_ci(h,s,alpha=0.05):
    n=h+s
    lo=stats.beta.ppf(alpha/2,h,s+1) if h>0 else 0.0
    hi=stats.beta.ppf(1-alpha/2,h+1,s) if s>0 else np.inf
    return h/s if s else np.nan, lo/(1-lo), hi/(1-hi)
rows=[]
for col,name in (("university","大学专利"),("company","企业专利"),("public_rd","公共研究机构专利")):
    for i in ("ai","biomed","fintech"):
        for (y0,y1) in ((2015,2017),(2021,2023)):
            s=pat[pat[col]&pat.year.between(y0,y1)&(pat.industry==i)].groupby("city").size()
            h,sg=int(s.get("hk",0)),int(s.get("sg",0))
            r,lo,hi=ratio_ci(h,sg)
            rows.append(dict(series=name,industry=i,window=f"{y0}-{y1}",hk=h,sg=sg,ratio=r,lo=lo,hi=hi))
ci=pd.DataFrame(rows); print(ci.round(3).to_string(index=False))
ci.to_csv(W+"t5_ratio_ci.csv",index=False)

# 趋势：年度 logit(p_hk) ~ a + b*year，二项 MLE + Pearson 过度离散校正；b≈log(港/星) 的年斜率
def trend(h,s,years):
    h=np.array(h,float); s=np.array(s,float); n=h+s; x=np.array(years,float)-np.mean(years)
    def nll(th):
        a,b=th; p=1/(1+np.exp(-(a+b*x))); p=np.clip(p,1e-12,1-1e-12)
        return -np.sum(h*np.log(p)+s*np.log(1-p))
    res=optimize.minimize(nll,[np.log((h.sum()+.5)/(s.sum()+.5)),0.0],method="BFGS")
    a,b=res.x; p=1/(1+np.exp(-(a+b*x)))
    # Fisher info
    w=n*p*(1-p); I=np.array([[w.sum(),(w*x).sum()],[(w*x).sum(),(w*x*x).sum()]]); cov=np.linalg.inv(I)
    pearson=np.sum((h-n*p)**2/(n*p*(1-p))); df=len(h)-2; phi=max(1.0,pearson/df)
    se=np.sqrt(cov[1,1]*phi)
    return b,se,phi
print("\n=== T5 年度趋势：log(港/星) 年斜率（二项 logit；se 已按过度离散 φ 放大）===")
YRS=list(range(2015,2024))
for col,name in (("university","大学专利"),("company","企业专利")):
    for i in ("ai","biomed","fintech"):
        s=pat[pat[col]&(pat.industry==i)].groupby(["city","year"]).size().unstack("year").reindex(columns=YRS,fill_value=0).fillna(0)
        if s.loc["sg"].sum()<20: 
            print(f"  {name} {i}: 量太小跳过 hk={int(s.loc['hk'].sum())} sg={int(s.loc['sg'].sum())}"); continue
        b,se,phi=trend(s.loc["hk"],s.loc["sg"],YRS)
        print(f"  {name} {i}: 斜率 {b:+.3f}/年  95%CI [{b-1.96*se:+.3f},{b+1.96*se:+.3f}]  φ={phi:.2f}  （隐含 9 年变化倍数 {np.exp(b*8):.2f}）")
# 研究者存量 斜率 2017Q4–2024Q4
rs=pd.read_csv(R+"clean/researchers_stock_by_quarter.csv"); rs["industry"]=rs.industry.str.replace(r"^fintech.*","fintech",regex=True)
rs=rs[rs.window_full.astype(str)=="True"]
print("\n  研究者存量 log(港/星) 年斜率（2017Q4–2024Q4 Q4 点 OLS）")
for i in ("ai","biomed","fintech"):
    q=rs[(rs.industry==i)&rs.quarter.str.endswith("Q4")].pivot(index="quarter",columns="city",values="unique_authors")
    y=np.log(q.hk/q.sg); x=q.index.str[:4].astype(int)
    b=np.polyfit(x,y,1)[0]; print(f"  {i}: {b:+.3f}/年")
