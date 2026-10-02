# T2: OpenAlex 版本漂移 —— 2022–24 论文数 港/星 在 8/26、9/11、10/2 三个版本下
import pandas as pd
R="/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/"
norm=lambda s: "fintech" if s.startswith("fintech") else s
def load(path,col):
    d=pd.read_csv(R+path); d["industry"]=d["industry"].map(norm); d["year"]=d["quarter"].str[:4].astype(int)
    return d.rename(columns={col:"n"})[["industry","city","year","quarter","n"]]
v911=load("clean/intl_collab_by_quarter.csv","works")
v1002=load("raw/openalex_intl_cn_by_quarter.csv","works")
v826=load("raw/openalex_papers_by_quarter.csv","count")
def ratio(d,y0,y1):
    s=d[(d.year>=y0)&(d.year<=y1)].groupby(["industry","city"]).n.sum().unstack()
    s["ratio"]=s.hk/s.sg; return s
for y0,y1 in ((2022,2024),(2015,2024),(2015,2017),(2021,2023)):
    print(f"\n=== {y0}-{y1} 合计论文数 ===")
    out=pd.concat({"v0826":ratio(v826,y0,y1),"v0911":ratio(v911,y0,y1),"v1002":ratio(v1002,y0,y1)},axis=1)
    print(out.round(3).to_string())
# 每年比值
print("\n=== 逐年 港/星（9/11 vs 10/2）===")
for v,name in ((v911,"0911"),(v1002,"1002"),(v826,"0826")):
    s=v.groupby(["industry","year","city"]).n.sum().unstack(); s["r"]=s.hk/s.sg
    print(name); print(s["r"].unstack(0).round(3).to_string())
# 版本间单元变化 2022-24
a=v911[v911.year>=2022].groupby(["industry","city"]).n.sum(); b=v1002[v1002.year>=2022].groupby(["industry","city"]).n.sum()
print("\n10/2 相对 9/11 变化（2022–24）:"); print(((b/a-1)*100).round(1).to_string())
a=v911.groupby(["industry","city"]).n.sum(); b=v1002.groupby(["industry","city"]).n.sum()
print("\n10/2 相对 9/11 变化（2015–24）:"); print(((b/a-1)*100).round(1).to_string())
