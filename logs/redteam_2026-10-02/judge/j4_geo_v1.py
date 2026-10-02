# -*- coding: utf-8 -*-
"""裁判抽查 j4：用挑战者 A 的人工分类表（redteam/geo/geo_class.csv，只读引用），
以裁判自己的代码独立重算 V1（两城同剔外地集团实体）比值，并统计新加坡 AI 企业族中三家大户占比、
香港申请人名中是否含 SHENZHEN。只读仓库。"""
import csv, collections, pathlib, re
import pandas as pd

ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")
GEO = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/geo/geo_class.csv")
rows = list(csv.DictReader(open(ROOT / "raw/patents_families_raw.csv", encoding="utf-8-sig")))
smap = {r["assignee"].strip(): r["sector"].strip()
        for r in csv.DictReader(open(ROOT / "config/patents_assignee_sector.csv", encoding="utf-8-sig"))}
EX = {(g["city"], g["assignee"]) for g in csv.DictReader(open(ROOT / "config/patents_assignee_geo_exclude.csv", encoding="utf-8-sig"))
      if g["exclude_level"] in ("ali_grp", "ant_grp")}
gc = pd.read_csv(GEO)
pats = [(r.city, re.compile(r.pattern, re.I), r.category) for r in gc.itertuples()]

def cat(city, a):
    for c, rx, k in pats:
        if c == city and rx.search(a):
            return k
    return "unclassified"

for r in rows:
    r["year"] = int(r["quarter"][:4])
    ps = [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]
    r["ps"] = ps
    r["cps"] = [a for a in ps if smap.get(a) == "company"]
    hit = [a for a in r["cps"] if (r["city"], a) in EX]
    r["is_comp"] = bool(r["cps"]) and not (hit and len(hit) == len(r["cps"]))
    r["cats"] = [cat(r["city"], a) for a in r["cps"]]

E, L = (2015, 2016, 2017), (2021, 2022, 2023)
NONLOCAL = {"foreign_mnc", "mainland_grp", "lenovo", "hk_grp"}

def ratio(ind, drop_hk, drop_sg, move_st=False):
    out = {}
    for ys, tag in ((E, "E"), (L, "L")):
        n = collections.Counter()
        for r in rows:
            if r["industry"] != ind or not r["is_comp"] or r["year"] not in ys:
                continue
            drop = drop_hk if r["city"] == "hk" else drop_sg
            if move_st and r["city"] == "sg" and all(k == "hk_grp" for k in r["cats"]):
                n["hk"] += 1
                continue
            if r["cats"] and all(k in drop for k in r["cats"]):
                continue
            n[r["city"]] += 1
        out[tag] = (n["hk"], n["sg"], n["hk"] / n["sg"])
    return out

print("V0/V1（独立重算，分类表来自挑战者 A）")
for ind in ("ai", "biomed", "fintech"):
    v0 = ratio(ind, set(), set())
    v1 = ratio(ind, NONLOCAL, NONLOCAL)
    v6 = ratio(ind, set(), set(), move_st=True)
    print(f"  {ind:8s} V0 {v0['E'][2]:.3f}→{v0['L'][2]:.3f} | V1 {v1['E'][0]}/{v1['E'][1]}={v1['E'][2]:.3f}"
          f" → {v1['L'][0]}/{v1['L'][1]}={v1['L'][2]:.3f} | 商汤改归香港 {v6['E'][2]:.3f}→{v6['L'][2]:.3f}")

# 新加坡 AI 企业族 2021–23 各类构成（族内企业申请人全属该类才计入该类）
c = collections.Counter()
for r in rows:
    if r["industry"] == "ai" and r["city"] == "sg" and r["is_comp"] and r["year"] in L:
        ks = set(r["cats"])
        c[ks.pop() if len(ks) == 1 else "mixed"] += 1
tot = sum(c.values())
print("\n新加坡 AI 企业族 2021–23 构成：", {k: f"{v} ({v/tot:.2f})" for k, v in c.most_common()}, "合计", tot)
nl = sum(v for k, v in c.items() if k in NONLOCAL)
print(f"  外地集团（foreign_mnc+mainland_grp+lenovo+hk_grp）合计 {nl}/{tot} = {nl/tot:.3f}")

# 香港申请人名中含 SHENZHEN 的数目（geo-5）
sz = {a for r in rows if r["city"] == "hk" for a in r["ps"] if re.search(r"SHENZHEN|SHEN ZHEN", a, re.I)}
print("\n香港一侧申请人名含 SHENZHEN：", len(sz), sorted(sz)[:10])
szs = {a for r in rows if r["city"] == "sg" for a in r["ps"] if re.search(r"SHENZHEN|SUZHOU|CHONGQING|NUSRI", a, re.I)}
print("新加坡一侧申请人名含 SHENZHEN/SUZHOU/CHONGQING/NUSRI：", len(szs), sorted(szs)[:10])
# 大学档中是否出现 company 以外的跨国公司——按构造：大学族的大学申请人都是 university sector
