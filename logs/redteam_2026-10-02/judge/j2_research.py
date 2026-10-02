# -*- coding: utf-8 -*-
"""裁判抽查 j2：研究端（版本漂移、时序、内地合作、人均）+ R4 抽样的 CN 公开国别覆盖"""
import pathlib, math
import pandas as pd

ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")
norm = lambda s: "fintech" if str(s).startswith("fintech") else s

def load(rel, col):
    d = pd.read_csv(ROOT / rel)
    d["industry"] = d["industry"].map(norm)
    d["year"] = d["quarter"].str[:4].astype(int)
    return d.groupby(["industry", "city", "year"])[col].sum()

v0826 = load("raw/openalex_papers_by_quarter.csv", "count")
v0911 = load("clean/intl_collab_by_quarter.csv", "works")
v1002 = load("raw/openalex_intl_cn_by_quarter.csv", "works")

def r(s, ind, ys):
    h = sum(s.get((ind, "hk", y), 0) for y in ys); g = sum(s.get((ind, "sg", y), 0) for y in ys)
    return h, g, h / g

print("[A] 论文数港/星：8/26 | 9/11 | 10/2")
for ys, tag in (((2022, 2023, 2024), "2022–24"), ((2015, 2016, 2017), "2015–17"), ((2021, 2022, 2023), "2021–23")):
    for ind in ("ai", "biomed", "fintech"):
        a, b, c = r(v0826, ind, ys), r(v0911, ind, ys), r(v1002, ind, ys)
        print(f"   {tag} {ind:8s} {a[2]:.3f} | {b[2]:.3f} | {c[2]:.3f}    (hk: {a[0]:.0f}/{b[0]:.0f}/{c[0]:.0f}; sg: {a[1]:.0f}/{b[1]:.0f}/{c[1]:.0f})")
print("   生医香港 9/11 vs 10/2（2022–24）：", f"{r(v1002,'biomed',(2022,2023,2024))[0]/r(v0911,'biomed',(2022,2023,2024))[0]-1:+.3f}")
print("   生医逐年港/星（10/2）：", " ".join(f"{y}:{v1002[('biomed','hk',y)]/v1002[('biomed','sg',y)]:.3f}" for y in range(2015, 2025)))
print("   生医逐年港/星（9/11）：", " ".join(f"{y}:{v0911[('biomed','hk',y)]/v0911[('biomed','sg',y)]:.3f}" for y in range(2015, 2025)))

# [B] 内地合作（10/2 版）
cn = pd.read_csv(ROOT / "raw/openalex_intl_cn_by_quarter.csv")
cn["industry"] = cn["industry"].map(norm); cn["year"] = cn["quarter"].str[:4].astype(int)
g = cn.groupby(["industry", "city", "year"])[["works", "cn_any_works"]].sum()
print("\n[B] 剔除含内地机构论文后的港/星论文比值（10/2 版）")
for ind in ("ai", "biomed", "fintech"):
    out = []
    for ys in ((2015, 2016, 2017), (2022, 2023, 2024)):
        H = g.loc[[(ind, "hk", y) for y in ys]].sum(); S = g.loc[[(ind, "sg", y) for y in ys]].sum()
        out.append((H.works / S.works, (H.works - H.cn_any_works) / (S.works - S.cn_any_works),
                    H.cn_any_works / H.works, S.cn_any_works / S.works))
    (a0, b0, h0, s0), (a1, b1, h1, s1) = out
    share = (math.log(a1 / a0) - math.log(b1 / b0)) / math.log(a1 / a0)
    print(f"   {ind:8s} 全部 {a0:.3f}→{a1:.3f}；剔含内地 {b0:.3f}→{b1:.3f}；香港含内地占比 {h0:.3f}→{h1:.3f}；"
          f"新加坡 {s0:.3f}→{s1:.3f}；上升中可归于内地合作的份额 {share:.2f}")

# [C] 研究者比值时序（C1/C2）
rs = pd.read_csv(ROOT / "clean/researchers_stock_by_quarter.csv")
rs["industry"] = rs["industry"].map(norm)
rs = rs[rs.window_full.astype(str) == "True"]
p = rs.pivot_table(index=["industry", "quarter"], columns="city", values="unique_authors")
p["ratio"] = p.hk / p.sg
print("\n[C] 研究者存量港/星（Q4）与对数上升的时段分解")
for ind in ("ai", "biomed", "fintech"):
    q = lambda s: p.loc[(ind, s), "ratio"]
    r17, r21, r23, r24 = q("2017Q4"), q("2021Q4"), q("2023Q4"), q("2024Q4")
    tot = math.log(r24 / r17)
    first = p.loc[ind][p.loc[ind].ratio >= 1].index.min()
    print(f"   {ind:8s} 2017Q4 {r17:.3f} 2021Q4 {r21:.3f} 2023Q4 {r23:.3f} 2024Q4 {r24:.3f}；"
          f"2021Q4 后份额 {math.log(r24/r21)/tot:.2f}，2023Q4 后份额 {math.log(r24/r23)/tot:.2f}；首次≥1：{first}")

# [D] 人口比
pop = pd.read_csv(ROOT / "raw/worldbank_population_hk_sg.csv")
print("\n[D] 人口文件列：", list(pop.columns))
print(pop.head(3).to_string())

# [E] R4 抽样：各专利局公开的申请人国别覆盖
d = pd.read_csv(ROOT / "raw/r4_cpc_diagnose.csv", dtype=str)
print("\n[E] r4_cpc_diagnose 列：", list(d.columns))
gg = d.drop_duplicates(["family_id", "publication_number"]).copy()
gg["has_cc"] = gg.assignee_countries.fillna("").str.replace(",", "").str.strip().str.len() > 0
gg["has_name"] = gg.assignees.fillna("").str.strip().str.len() > 0
print(gg.groupby("pub_country").agg(n=("has_cc", "size"), has_name=("has_name", "sum"), has_cc=("has_cc", "sum")).to_string())
