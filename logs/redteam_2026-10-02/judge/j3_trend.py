# -*- coding: utf-8 -*-
"""裁判抽查 j3：企业专利港/星比值的年度趋势（准二项 logit，Pearson φ 放大标准误），
以及去掉单一主体（商汤、Smith & Nephew）后的趋势敏感性。只读仓库。"""
import csv, collections, pathlib, re, math
import numpy as np

ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")
rows = list(csv.DictReader(open(ROOT / "raw/patents_families_raw.csv", encoding="utf-8-sig")))
smap = {r["assignee"].strip(): r["sector"].strip()
        for r in csv.DictReader(open(ROOT / "config/patents_assignee_sector.csv", encoding="utf-8-sig"))}
EX = {(g["city"], g["assignee"]) for g in csv.DictReader(open(ROOT / "config/patents_assignee_geo_exclude.csv", encoding="utf-8-sig"))
      if g["exclude_level"] in ("ali_grp", "ant_grp")}
for r in rows:
    r["year"] = int(r["quarter"][:4])
    ps = [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]
    r["cps"] = [a for a in ps if smap.get(a) == "company"]
    hit = [a for a in r["cps"] if (r["city"], a) in EX]
    r["is_comp"] = bool(r["cps"]) and not (hit and len(hit) == len(r["cps"]))
    r["is_univ"] = "university" in {smap.get(a) for a in ps}

def counts(ind, flag="is_comp", drop_sg=None, move_sg_to_hk=None):
    c = collections.Counter()
    for r in rows:
        if r["industry"] != ind or not r[flag]:
            continue
        city = r["city"]
        if city == "sg" and drop_sg and r["cps"] and all(drop_sg.search(a) for a in r["cps"]):
            continue
        if city == "sg" and move_sg_to_hk and r["cps"] and all(move_sg_to_hk.search(a) for a in r["cps"]):
            city = "hk"
        c[(city, r["year"])] += 1
    yrs = list(range(2015, 2024))
    return np.array([c[("hk", y)] for y in yrs], float), np.array([c[("sg", y)] for y in yrs], float), yrs

def qb_logit(h, s, yrs):
    n = h + s; t = np.array(yrs, float) - 2019
    X = np.column_stack([np.ones_like(t), t]); b = np.zeros(2)
    for _ in range(50):
        eta = X @ b; p = 1 / (1 + np.exp(-eta)); W = n * p * (1 - p)
        z = eta + (h - n * p) / W
        b = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * z))
    p = 1 / (1 + np.exp(-(X @ b))); W = n * p * (1 - p)
    cov = np.linalg.inv(X.T @ (W[:, None] * X))
    phi = max(1.0, float(np.sum((h - n * p) ** 2 / W) / (len(h) - 2)))
    se = math.sqrt(cov[1, 1] * phi)
    # 港/星比值 = p/(1-p)，故 logit 斜率即 log(比值) 的年斜率
    return b[1], se, phi

ST = re.compile(r"SENSE ?TIME", re.I)
SN = re.compile(r"SMITH ?(&|AND) ?NEPHEW", re.I)
cases = [("ai", "企业", "is_comp", None, None), ("ai", "企业·商汤改归香港", "is_comp", None, ST),
         ("ai", "企业·剔新加坡商汤", "is_comp", ST, None),
         ("biomed", "企业", "is_comp", None, None), ("biomed", "企业·剔新加坡 S&N", "is_comp", SN, None),
         ("fintech", "企业", "is_comp", None, None),
         ("ai", "大学", "is_univ", None, None), ("biomed", "大学", "is_univ", None, None)]
print("log(港/星) 年斜率（2015–2023 年度，准二项 logit；95% CI = ±1.96·SE·√φ）")
for ind, lab, flag, d, m in cases:
    h, s, yrs = counts(ind, flag, d, m)
    b, se, phi = qb_logit(h, s, yrs)
    print(f"  {ind:8s} {lab:16s} 斜率 {b:+.3f} [{b-1.96*se:+.3f}, {b+1.96*se:+.3f}]  φ={phi:.2f}  "
          f"港 {h.astype(int).tolist()}  星 {s.astype(int).tolist()}")
