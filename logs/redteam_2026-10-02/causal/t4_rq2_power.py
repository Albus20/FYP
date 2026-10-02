# T4: RQ2 检验力再评估：各滞后的 n、可侦测 |r|、自相关修正后的有效样本量、观测 r 的置信区间、跨单元合并（探索性，非预注册）
import importlib.util, math, statistics as st, sys, numpy as np
D="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/"
spec=importlib.util.spec_from_file_location("rq2",D+"rq2_leadlag_copy.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
idi_raw=m.load(m.IDI_PATH,"patent_families"); idi_g={u:m.yoy(idi_raw[u],"count") for u in m.UNITS}
tais=[]
for label,path,col,qc,kind,keep in m.TAI_SPEC:
    d=m.load(path,col,qc,keep); tais.append((label,{u:m.yoy(d[u],kind) for u in m.UNITS}))
def rmin(n): return math.tanh((1.959964+0.841621)/math.sqrt(n-3)) if n>3 else float('nan')
def acf(x,k):
    x=np.asarray(x); x=x-x.mean(); return float((x[:-k]*x[k:]).sum()/(x*x).sum()) if len(x)>k else 0.0
print("各滞后的配对数与可侦测 |r|（名义，独立样本假设）")
for label,tg in tais:
    ns=[m.paired(tg[("ai","hk")],idi_g[("ai","hk")],L)[2] for L in range(9)]
    print(f"  {label:18s} n: {ns}  r_min: {[round(rmin(n),2) for n in ns]}")
print("\nL=4 自相关与有效样本量（Bartlett: n_eff = n / (1 + 2Σ_k ρx(k)ρy(k)), k=1..4）")
rows=[]
for label,tg in tais:
    for u in m.UNITS:
        x,y,n=m.paired(tg[u],idi_g[u],4); r=m.pearson(x,y)
        s=sum(acf(x,k)*acf(y,k) for k in range(1,5)); neff=n/(1+2*s) if 1+2*s>0 else n
        z=math.atanh(r); se=1/math.sqrt(max(neff,4)-3); lo,hi=math.tanh(z-1.96*se),math.tanh(z+1.96*se)
        se0=1/math.sqrt(n-3); lo0,hi0=math.tanh(z-1.96*se0),math.tanh(z+1.96*se0)
        rows.append((label,u,n,r,acf(x,1),acf(y,1),neff,lo0,hi0,lo,hi))
        print(f"  {label:16s}{u[0]+'/'+u[1]:11s} n={n:2d} r={r:+.2f} ρx1={acf(x,1):+.2f} ρy1={acf(y,1):+.2f} n_eff={neff:5.1f} 名义95%CI[{lo0:+.2f},{hi0:+.2f}] 修正CI[{lo:+.2f},{hi:+.2f}]  r_min(n_eff)={rmin(neff) if neff>3 else float('nan'):.2f}")
print("\n跨六单元合并（Fisher z 按 n-3 加权；探索性、非预注册；单元间不独立，CI 偏窄）")
for label,tg in tais:
    for L in [4,6,8]:
        zs=[];ws=[]
        for u in m.UNITS:
            x,y,n=m.paired(tg[u],idi_g[u],L); r=m.pearson(x,y)
            if r is None or n<=3: continue
            zs.append(math.atanh(r)*(n-3)); ws.append(n-3)
        zbar=sum(zs)/sum(ws); se=1/math.sqrt(sum(ws))
        print(f"  {label:16s} L{L}: 合并 r={math.tanh(zbar):+.2f}  名义95%CI[{math.tanh(zbar-1.96*se):+.2f},{math.tanh(zbar+1.96*se):+.2f}]  总 n={sum(ws)+3*len(ws)}")
# HK 研究者增长落在可检验窗口之外的份额
import pandas as pd
R=pd.read_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/clean/researchers_stock_by_quarter.csv").replace({"fintech_kw":"fintech"})
print("\n香港研究者存量 2017Q4→2024Q4 的对数增长中，发生在 2022Q4 之后（L=4 时对应专利季度已超出 2023Q4 窗口）的份额：")
for i in ["ai","biomed","fintech"]:
    s=R[(R.industry==i)&(R.city=="hk")].set_index("quarter").unique_authors
    tot=math.log(s["2024Q4"]/s["2017Q4"]); post=math.log(s["2024Q4"]/s["2022Q4"]); post8=math.log(s["2024Q4"]/s["2021Q4"])
    print(f"  {i}: L4 不可检验份额 {post/tot*100:.0f}%；L8 不可检验份额（2021Q4 之后）{post8/tot*100:.0f}%")
