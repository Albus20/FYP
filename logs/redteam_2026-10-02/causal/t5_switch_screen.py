# T5: 申请主体切换/阶梯变化筛查 + 未归类申请人的时间分布
import pandas as pd, numpy as np, re
G="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
raw=pd.read_csv(G+"raw/patents_families_raw.csv",dtype={"family_id":str}); raw["year"]=raw.quarter.str[:4].astype(int)
sec=pd.read_csv(G+"config/patents_assignee_sector.csv"); smap=dict(zip(sec.assignee.str.strip(),sec.sector.str.strip()))
raw["names"]=raw.assignees.astype(str).str.split("|").apply(lambda l:[a.strip() for a in l])
raw["secs"]=raw.names.apply(lambda l:[smap.get(a,"UNMAPPED") for a in l])
raw["all_unmapped"]=raw.secs.apply(lambda l: all(s=="UNMAPPED" for s in l))
raw["any_unmapped"]=raw.secs.apply(lambda l: any(s=="UNMAPPED" for s in l))
print("== 全部申请人未归类（因而不进任何三分序列）的族数，按城市×年")
print(raw[raw.all_unmapped].groupby(["city","year"]).size().unstack("year").fillna(0).astype(int).to_string())
print("各城全部族数：");print(raw.groupby(["city","year"]).size().unstack("year").to_string())
um=raw[raw.all_unmapped].explode("names").names.value_counts().head(15)
print("未归类申请人前 15：\n",um.to_string())
# 集团关键词扫描（两城）
KW=["SENSETIME","LENOVO","LEMON","BYTEDANCE","TIKTOK","BIGO","TENCENT","TENPAY","HUAWEI","ZTE","XIAOMI","DJI","PING AN","CONTEMPORARY AMPEREX","ALIBABA","ALIPAY","ANT ","ADVANCED NOVA","ADVANCED NEW","SHOPEE","SEA ","GRAB","SMITH & NEPHEW","MASTERCARD","VISA","RESMED","LEICA","AVAGO","BROADCOM","MARVELL","MEDIATEK","INSILICO","HCP","ROTAM","TOP VICTORY","OPPO","VIVO","HONOR","NETEASE","BAIDU","JD ","MEITUAN","DIDI","UBTECH","HKUST","APPLIED MAT","DYSON","PHILIPS","NOVARTIS","ROCHE","ILLUMINA","MSD","WUXI","BEIGENE","HUTCHISON","HUTCHMED","CK ","PCCW","HSBC","STANDARD CHARTERED","AIA","PRUDENTIAL","DBS","OCBC","UOB","SINGTEL","TELEPATH"]
rows=[]
for r in raw.itertuples():
    for a in r.names:
        for k in KW:
            if k in a.upper(): rows.append((k,r.city,r.industry,a,r.year,smap.get(a,"UNMAPPED")))
K=pd.DataFrame(rows,columns=["kw","city","industry","assignee","year","sector"])
t=K.groupby(["kw","city","assignee","sector","year"]).size().unstack("year").fillna(0).astype(int)
pd.set_option("display.width",300); pd.set_option("display.max_rows",500)
print(t.to_string())
