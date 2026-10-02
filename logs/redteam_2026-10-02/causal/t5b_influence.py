# T5b: 企业专利比值对申请主体进出/切换的敏感性（ali_ant_grp 主口径为基线；分数归属）
import pandas as pd, numpy as np, re
D="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/"
P=pd.read_csv(D+"t2b_assignee_year_frac.csv")
# 名称归并：去标点、统一常见后缀；已知集团变体手工并组（只并同城同集团的拼写/实体变体）
GROUPS={"SENSETIME":"SENSETIME","SMITH & NEPHEW":"SMITH & NEPHEW","MASTERCARD":"MASTERCARD","LENOVO":"LENOVO","LEICA INSTR":"LEICA",
        "AVAGO":"AVAGO/BROADCOM","MARVELL":"MARVELL","HCP HEALTHCARE":"HCP","GRABTAXI":"GRAB","ROTAM":"ROTAM","INSILICO":"INSILICO",
        "MOFFETT":"MOFFETT","TOP VICTORY":"TOP VICTORY","THUNDER POWER":"THUNDER POWER","ALIBABA":"ALIBABA","ALIPAY":"ANT","ANTCHAIN":"ANT","ADVANCED NOVA":"ANT"}
def grp(a):
    u=a.upper()
    for k,v in GROUPS.items():
        if k in u: return v
    return re.sub(r"[^A-Z0-9 ]","",u).strip()
P["grp"]=P.assignee.apply(grp)
def win(s,a,b): return s[(s.year>=a)&(s.year<=b)]
def ratios(sub):
    out={}
    for c in ["hk","sg"]:
        s=sub[sub.city==c]; out[c]=(win(s,2015,2017).w.sum(),win(s,2021,2023).w.sum())
    r0=out["hk"][0]/out["sg"][0]; r1=out["hk"][1]/out["sg"][1]
    return out,r0,r1
print("口径核对（分数归属合计应等于官方 3 年合计）：")
for ind in ["ai","biomed","fintech"]:
    o,r0,r1=ratios(P[P.industry==ind]); print(f"  {ind}: HK {o['hk'][0]:.0f}→{o['hk'][1]:.0f}  SG {o['sg'][0]:.0f}→{o['sg'][1]:.0f}  比值 {r0:.3f}→{r1:.3f}  Δln {np.log(r1/r0):+.3f}")

print("\n== A. 只看两端都在申请的「在位申请人」（集团归并后）：消除进入/退出/改名切换")
for ind in ["ai","biomed","fintech"]:
    s=P[P.industry==ind]; res={}
    for c in ["hk","sg"]:
        sc=s[s.city==c]; g0=win(sc,2015,2017).groupby("grp").w.sum(); g1=win(sc,2021,2023).groupby("grp").w.sum()
        inc=g0.index.intersection(g1.index); ent=g1.index.difference(g0.index); ext=g0.index.difference(g1.index)
        res[c]=dict(i0=g0[inc].sum(),i1=g1[inc].sum(),ent=g1[ent].sum(),ext=g0[ext].sum(),n_inc=len(inc),n_ent=len(ent),n_ext=len(ext))
        print(f"  {ind}/{c}: 在位 {len(inc)} 个 {res[c]['i0']:.0f}→{res[c]['i1']:.0f}；新进入 {len(ent)} 个贡献 {res[c]['ent']:.0f}；退出 {len(ext)} 个原有 {res[c]['ext']:.0f}")
    ri0=res['hk']['i0']/res['sg']['i0']; ri1=res['hk']['i1']/res['sg']['i1']
    re1=res['hk']['ent']/res['sg']['ent']; rx0=res['hk']['ext']/res['sg']['ext']
    print(f"   → 在位申请人比值 {ri0:.2f}→{ri1:.2f}（Δln {np.log(ri1/ri0):+.2f}）；新进入者 港/星 {re1:.2f}；退出者 港/星 {rx0:.2f}")

print("\n== B. 两城各剔除窗口内前 k 大企业申请人（集团归并后，对称、机械）")
for ind in ["ai","biomed","fintech"]:
    s=P[P.industry==ind]
    line=[]
    for k in [0,1,3,5,10]:
        keep=[]
        for c in ["hk","sg"]:
            sc=s[s.city==c]; top=sc.groupby("grp").w.sum().sort_values(ascending=False).head(k).index
            keep.append(sc[~sc.grp.isin(top)])
        o,r0,r1=ratios(pd.concat(keep)); line.append(f"k={k}: {r0:.2f}→{r1:.2f}")
    print(f"  {ind}: "+" | ".join(line))

print("\n== C. 逐个剔除（两城各自）对 Δln 比值（2015–17→2021–23）影响 ≥0.10 的申请主体")
for ind in ["ai","biomed","fintech"]:
    s=P[P.industry==ind]; o,r0,r1=ratios(s); base=np.log(r1/r0)
    for c in ["hk","sg"]:
        for g,tot in s[s.city==c].groupby("grp").w.sum().sort_values(ascending=False).head(40).items():
            o2,a0,a1=ratios(s[~((s.city==c)&(s.grp==g))]); d=np.log(a1/a0)-base
            if abs(d)>=0.10:
                yr=s[(s.city==c)&(s.grp==g)].groupby("year").w.sum().reindex(range(2015,2024),fill_value=0)
                print(f"  {ind}/{c} {g[:45]:45s} 窗内 {tot:5.0f}  剔除后比值 {a0:.2f}→{a1:.2f}（Δln 变化 {d:+.2f}）年度 {' '.join(f'{v:.0f}' for v in yr)}")

print("\n== D. 阶梯型主体（集团 IP 实体切换/设立）两城同剔后的剪刀差逐年路径（三年合计比值）")
STEP={"sg":["SENSETIME","LEMON INC","BIGO TECH PTE LTD","SMITH & NEPHEW","RESMED ASIA PTE LTD","MASTERCARD","HCP"],
      "hk":["CONTEMPORARY AMPEREX TECHNOLOGY HONG KONG LTD"]}
def path(sub):
    out=[]
    for y in range(2017,2024):
        h=sub[(sub.city=="hk")&(sub.year.between(y-2,y))].w.sum(); g=sub[(sub.city=="sg")&(sub.year.between(y-2,y))].w.sum()
        out.append(h/g)
    return out
for ind in ["ai","biomed","fintech"]:
    s=P[P.industry==ind]
    m=s.apply(lambda r: r.grp in STEP[r.city],axis=1)
    print(f"  {ind}: 基线   "+" ".join(f"{v:.2f}" for v in path(s)))
    print(f"  {ind}: 同剔后 "+" ".join(f"{v:.2f}" for v in path(s[~m]))+f"   （剔除族数 HK {s[m&(s.city=='hk')].w.sum():.0f}，SG {s[m&(s.city=='sg')].w.sum():.0f}）")
    for c in ["sg"]:
        only=[g for g in STEP[c] if g in set(s[s.city==c].grp)]
