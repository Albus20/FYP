import pandas as pd, numpy as np, re, importlib.util
D="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/causal/"
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
spec=importlib.util.spec_from_file_location("t5b",D+"t5b_influence.py")
P=pd.read_csv(D+"t2b_assignee_year_frac.csv")
GROUPS={"SENSETIME":"SENSETIME","SMITH & NEPHEW":"SMITH & NEPHEW","MASTERCARD":"MASTERCARD","LENOVO":"LENOVO","LEICA INSTR":"LEICA","AVAGO":"AVAGO/BROADCOM","MARVELL":"MARVELL","HCP HEALTHCARE":"HCP","GRABTAXI":"GRAB","ROTAM":"ROTAM","INSILICO":"INSILICO","MOFFETT":"MOFFETT","TOP VICTORY":"TOP VICTORY","THUNDER POWER":"THUNDER POWER"}
def grp(a):
    u=a.upper()
    for k,v in GROUPS.items():
        if k in u: return v
    return re.sub(r"[^A-Z0-9 ]","",u).strip()
P["grp"]=P.assignee.apply(grp)
for ind in ["ai","biomed","fintech"]:
    for c in ["hk","sg"]:
        s=P[(P.industry==ind)&(P.city==c)]
        t=s.groupby("grp").w.sum().sort_values(ascending=False).head(10)
        tot=s.w.sum()
        print(f"{ind}/{c} 前10（占窗内 {t.sum()/tot*100:.0f}%）：", "; ".join(f"{g[:30]} {v:.0f}" for g,v in t.items()))
# 大学专利：两城前列申请人逐年
raw=pd.read_csv(G+"raw/patents_families_raw.csv",dtype={"family_id":str}); raw["year"]=raw.quarter.str[:4].astype(int)
sec=pd.read_csv(G+"config/patents_assignee_sector.csv"); smap=dict(zip(sec.assignee.str.strip(),sec.sector.str.strip()))
rec=[]
for r in raw.itertuples():
    names=[a.strip() for a in str(r.assignees).split("|")]; un=[a for a in names if smap.get(a)=="university"]
    for a in un: rec.append((r.industry,r.city,r.year,a,1/len(un)))
U=pd.DataFrame(rec,columns=["industry","city","year","a","w"])
for ind in ["ai","biomed"]:
    for c in ["hk","sg"]:
        t=U[(U.industry==ind)&(U.city==c)].pivot_table(index="a",columns="year",values="w",aggfunc="sum",fill_value=0)
        t["tot"]=t.sum(axis=1); t=t.sort_values("tot",ascending=False).head(6)
        print(f"\n大学 {ind}/{c}:\n", t.round(0).astype(int).to_string())
