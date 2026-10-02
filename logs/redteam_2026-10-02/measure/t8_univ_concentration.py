# T8：大学专利的机构集中度 vs 论文份额（全学科论文，openalex_institutions_counts 8/26 快照）
import pandas as pd
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
W="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/measure/"
pat=pd.read_pickle(W+"pat.pkl")
iw=pd.read_csv(R+"clean/institutions_works_series.csv").set_index("institution")
works=iw[["2021","2022","2023"]].sum(axis=1)
MAP={"香港城市大学":["UNIV CITY HONG KONG","UNIV CITY"],"香港大学":["UNIV HONG KONG","VERSITECH LTD"],
     "香港中文大学":["UNIV HONG KONG CHINESE","THE CHINESE UNIV OF HONG KONG"],"香港理工大学":["UNIV HONG KONG POLYTECHNIC"],
     "香港科技大学":["UNIV HONG KONG SCIENCE & TECH"],"新加坡国立大学":["NAT UNIV SINGAPORE","THE NATIONAL UNIV OF SINGAPORE"],
     "南洋理工大学":["UNIV NANYANG TECH","NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE","NANYANG TECH UNVERSITY"]}
s=pat[pat.university&pat.year.between(2021,2023)&pat.industry.isin(["ai","biomed"])].drop_duplicates(["city","family_id"])
rows=[]
for inst,names in MAP.items():
    c="sg" if inst in ("新加坡国立大学","南洋理工大学") else "hk"
    n=s[(s.city==c)&s.parts.map(lambda ps:any(a in names for a in ps))].shape[0]
    rows.append(dict(inst=inst,city=c,univ_families_ai_bio_2021_23=n,works_all_fields_2021_23=int(works[inst])))
d=pd.DataFrame(rows)
for c in ("hk","sg"):
    tot_f=s[s.city==c].shape[0]
    grp=iw[iw.group==("hk8" if c=="hk" else "sg")]
    tot_w=grp[["2021","2022","2023"]].sum().sum()
    d.loc[d.city==c,"share_of_city_univ_families"]=d.univ_families_ai_bio_2021_23/tot_f
    d.loc[d.city==c,"share_of_city_univ_works"]=d.works_all_fields_2021_23/tot_w
    d.loc[d.city==c,"families_per_1000_works"]=d.univ_families_ai_bio_2021_23/d.works_all_fields_2021_23*1000
    print(c,"去重大学族（AI+生医，2021–23）",tot_f,"大学论文（全学科）",int(tot_w))
print(d.round(3).to_string(index=False))
