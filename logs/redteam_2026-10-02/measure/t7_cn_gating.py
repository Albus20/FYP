# T7：CN/JP 公开在 BigQuery 里没有申请人国别 → 香港族只能经 US/EP/WO/TW 等公开「进门」；归属日期 ≠ 族最早申请日
import pandas as pd
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
d=pd.read_csv(R+"raw/r4_cpc_diagnose.csv",dtype=str)
p=d.drop_duplicates("publication_number").copy()
p["has_cc"]=p.assignee_countries.notna()&(p.assignee_countries.fillna("").str.strip(",")!="")
print("抽样：",p.family_id.nunique(),"族",len(p),"件公开")
print(p.groupby("pub_country").agg(n=("publication_number","size"),with_cc=("has_cc","sum")).sort_values("n",ascending=False).to_string())
raw=pd.read_csv(R+"raw/patents_families_raw.csv",dtype=str)
fam_min=p.groupby("family_id").filing_date.min()
r=raw[raw.family_id.isin(fam_min.index)].drop_duplicates(["city","family_id"]).copy()
r["fam_earliest"]=r.family_id.map(fam_min)
r["lag_days"]=(pd.to_datetime(r.first_filing_in_window)-pd.to_datetime(r.fam_earliest)).dt.days
r["cn_member"]=r.family_id.map(p.groupby("family_id").pub_country.apply(lambda s:"CN" in set(s)))
def gate(row):
    g=p[(p.family_id==row.family_id)&p.assignee_countries.fillna("").str.contains(row.city.upper())]
    return ",".join(sorted(set(g.pub_country)))
r["coded_offices"]=r.apply(gate,axis=1)
print(r[["city","family_id","first_filing_in_window","fam_earliest","lag_days","cn_member","coded_offices","assignees"]].sort_values(["city","lag_days"]).to_string(index=False))
print(r.groupby("city").agg(n=("lag_days","size"),lag_pos=("lag_days",lambda s:(s>0).sum()),mean_lag=("lag_days","mean"),cn_member=("cn_member","sum"),
      cn_coded=("coded_offices",lambda s:s.str.contains("CN").sum())).to_string())
