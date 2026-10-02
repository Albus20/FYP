# -*- coding: utf-8 -*-
"""裁判抽查 j5：人口比、各校每千篇论文专利族、m1_stock 同比序列自相关、全窗企业专利比值、香港分部门研发人力。只读仓库。"""
import csv, re, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")

p = pd.read_csv(ROOT / "raw/worldbank_population_hk_sg.csv").pivot(index="year", columns="city", values="population")
print("[1] 人口比 港/星：2024 %.4f；2022–24 %.4f；2021–23 %.4f" % (
    p.loc[2024].hk / p.loc[2024].sg, p.loc[2022:2024].hk.sum() / p.loc[2022:2024].sg.sum(),
    p.loc[2021:2023].hk.sum() / p.loc[2021:2023].sg.sum()))

d = pd.read_csv(ROOT / "clean/institutions_works_series.csv").set_index("institution")
w = d[["2021", "2022", "2023"]].sum(axis=1)
smap = {r["assignee"].strip(): r["sector"].strip() for r in csv.DictReader(open(ROOT / "config/patents_assignee_sector.csv", encoding="utf-8-sig"))}
rows = [r for r in csv.DictReader(open(ROOT / "raw/patents_families_raw.csv", encoding="utf-8-sig"))
        if r["industry"] in ("ai", "biomed") and 2021 <= int(r["quarter"][:4]) <= 2023]
pat = {"香港城市大学": ("hk", r"UNIV CITY|CITY UNIV|CITY INIV"), "香港大学": ("hk", r"^UNIV HONG KONG$|VERSITECH|^UNIV OF HONG KONG"),
       "香港中文大学": ("hk", r"CHINESE|CHINESS"), "香港科技大学": ("hk", r"SCI(ENCE)? & TECH"), "香港理工大学": ("hk", r"POLYTECHNIC"),
       "新加坡国立大学": ("sg", r"NAT(IONAL)? UNIV(ERSITY)? (OF )?SINGAPORE|^UNIV SINGAPORE"), "南洋理工大学": ("sg", r"NANYANG TECH")}
print("[2] 2021–23 AI+生医大学专利族 ÷ 全学科论文（8/26 机构快照），每千篇")
for inst, (city, rx) in pat.items():
    fam = {r["family_id"] for r in rows if r["city"] == city for a in r["assignees"].split(" | ")
           if smap.get(a.strip()) == "university" and re.search(rx, a, re.I)}
    print(f"    {inst} {len(fam)} 族 / {int(w[inst])} 篇 = {len(fam)/w[inst]*1000:.2f}")

rs = pd.read_csv(ROOT / "clean/researchers_stock_by_quarter.csv")
rs["industry"] = rs.industry.map(lambda s: "fintech" if s.startswith("fintech") else s)
rs = rs[rs.window_full.astype(str) == "True"]
print("[3] m1_stock 同比 Δlog(x+1) 一阶自相关（窗口完整季度）")
for (i, c), g in rs.groupby(["industry", "city"]):
    x = np.log(g.sort_values("quarter").unique_authors.values + 1); dd = x[4:] - x[:-4]
    print(f"    {i}/{c} n={len(dd)} rho1={np.corrcoef(dd[1:], dd[:-1])[0,1]:.2f}")

print("[4] 香港分部门研发人力（C&SD，仓库 clean/rnd_personnel_by_sector_series.csv）")
s = pd.read_csv(ROOT / "clean/rnd_personnel_by_sector_series.csv").set_index("sector")
for sec in ("business", "higher_education"):
    a, b = s.loc[sec, "2015"], s.loc[sec, "2023"]
    print(f"    {sec}: 2015 {a} → 2023 {b}（{b/a-1:+.3f}）")
