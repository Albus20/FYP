# -*- coding: utf-8 -*-
r"""rq1_patent_geo_sensitivity.py —— 专利港/星比值对「登记地」的敏感性（红队 P1 检查 ②，2026-10-02）

起因：docs/红队审查_2026-10-02.md。企业专利按申请人所在地计数，而新加坡 2021–23 年 AI 企业专利族至少 62% 属总部在外地的集团
（商汤新加坡主体、联想、字节 Lemon Inc. 等），香港 AI 企业专利 31% 来自宁德时代香港。比值的水平与走向是否经得起这些登记安排？

═══ 判读规则（审查报告中先写定，本脚本照做，不看结果改）═══
  水平：报告各对称口径下 2021–23 港/星比值的区间。区间上限 < 1 → 「各口径下香港都低于新加坡」。
  走向：log(港/星) 对年份的准二项 logit 斜率（2015–2023 年度，Pearson φ 放大标准误，95% CI）。
        只有**全部对称口径**的斜率 CI 上限都 < 0，才可称「比值下降」；全部 CI 下限 > 0 才可称「上升」；否则「走向不确定」。
        不对称口径（只剔一城）只作上界参考，不参与判读。

═══ 口径（企业专利；家族级规则与项目一致：某族全部企业申请人都属剔除对象才剔该族）═══
  V0   主口径：企业档、两城同剔阿里＋蚂蚁系
  V1   两城同剔「总部在本城以外」的已判定集团（外国跨国公司、内地集团、联想；新加坡侧的商汤也算外地）
  V2   V1 ＋ 两城同剔「不确定」
  V5   V1 ＋ 商汤新加坡主体改归香港
  V6   V0 ＋ 商汤新加坡主体改归香港
  T1/T3/T5/T10  两城各剔 2015–2023 年族数前 k 大的企业申请人（按名称，不做集团归并）
  VS   两城同剔已识别的「阶梯型主体」：新加坡商汤、万事达亚太、Smith & Nephew 亚太；香港宁德时代香港
  大学专利：U0 主口径；U1 两城各剔最大一所大学申请人；US 只剔浸会（阶梯型主体）；
            U3 两城各剔前 3 大学申请人只作展示——新加坡大学专利几乎全部来自 NUS、NTU，剔前 3 等于剔掉整个新加坡大学部门，不参与判读

分类表 config/patents_assignee_hq_class_draft.csv 来自红队挑战者 A 的人工判断（各格前 15 名及其他大户），**是草稿，待组员按
geo_rule 复核**（新加坡 14 条 uncertain）。复核后重跑本脚本即可更新。

输出：clean/rq1_patent_geo_sensitivity.csv（＋prov）；屏幕输出另存 logs/rq1_patent_geo_sensitivity_<日期>.txt
自检：V0、U0 的年度族数须与 raw/patents_families_by_quarter_company_ali_ant_grp.csv、..._university.csv 逐年一致。
R1：只用既有底稿做派生统计。
"""
import csv, json, math, pathlib, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS = ("ai", "biomed", "fintech")
IND_ZH = {"ai": "人工智能", "biomed": "生物医药", "fintech": "金融科技"}
YEARS = list(range(2015, 2024))


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


SMAP = {r["assignee"].strip(): r["sector"].strip() for r in read("config/patents_assignee_sector.csv")}
EX = {(g["city"], g["assignee"]) for g in read("config/patents_assignee_geo_exclude.csv")
      if g["exclude_level"] in ("ali_grp", "ant_grp")}
CLS = [(r["city"], re.compile(r["pattern"]), r["category"]) for r in read("config/patents_assignee_hq_class_draft.csv")]


def cat(city, a):
    for c, p, k in CLS:
        if c == city and p.search(a):
            return k
    return "unclassified"


FAM = []
for r in read("raw/patents_families_raw.csv"):
    ps = [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]
    cps = [a for a in ps if SMAP.get(a) == "company"]
    hit = [a for a in cps if (r["city"], a) in EX]
    kept = [a for a in cps if (r["city"], a) not in EX]
    FAM.append(dict(ind=r["industry"], city=r["city"], year=int(r["quarter"][:4]), fid=r["family_id"],
                    comp=bool(cps) and not (hit and len(hit) == len(cps)), comp_names=kept,
                    univ_names=[a for a in ps if SMAP.get(a) == "university"]))
for f in FAM:
    f["univ"] = bool(f["univ_names"])


# ── 计数 ─────────────────────────────────────────────────
def series(ind, kind, drop=lambda city, names: False, move_to_hk=None):
    """返回 {city: [各年族数]}。drop(city, names) 为真则剔该族；move_to_hk(names) 为真则把新加坡的该族改记香港。"""
    c = Counter()
    hk_fids = {f["fid"] for f in FAM if f["ind"] == ind and f["city"] == "hk" and f[kind]}
    for f in FAM:
        if f["ind"] != ind or not f[kind] or f["year"] not in YEARS:
            continue
        names = f["comp_names"] if kind == "comp" else f["univ_names"]
        city = f["city"]
        if city == "sg" and move_to_hk and names and move_to_hk(names):
            if f["fid"] in hk_fids:
                continue                      # 已在香港侧计过，避免双计
            city = "hk"
        elif drop(city, names):
            continue
        c[(city, f["year"])] += 1
    return {cc: [c[(cc, y)] for y in YEARS] for cc in ("hk", "sg")}


def all_in(pred):
    return lambda city, names: bool(names) and all(pred(city, a) for a in names)


def topk_names(ind, kind, k):
    out = {}
    for city in ("hk", "sg"):
        c = Counter()
        for f in FAM:
            if f["ind"] == ind and f["city"] == city and f[kind] and f["year"] in YEARS:
                for a in set(f["comp_names"] if kind == "comp" else f["univ_names"]):
                    c[a] += 1
        out[city] = {a for a, _ in c.most_common(k)}
    return out


def qb_slope(h, s):
    """log(港/星) 年斜率：准二项 logit，Pearson φ 放大标准误（与红队裁判 j3 同法）。"""
    h, s = np.array(h, float), np.array(s, float)
    keep = (h + s) > 0
    h, s, t = h[keep], s[keep], np.array(YEARS, float)[keep] - 2019
    n = h + s
    X = np.column_stack([np.ones_like(t), t])
    b = np.zeros(2)
    for _ in range(100):
        p = 1 / (1 + np.exp(-(X @ b)))
        W = n * p * (1 - p)
        z = X @ b + (h - n * p) / W
        b = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * z))
    p = 1 / (1 + np.exp(-(X @ b)))
    W = n * p * (1 - p)
    cov = np.linalg.inv(X.T @ (W[:, None] * X))
    phi = max(1.0, float(np.sum((h - n * p) ** 2 / W) / (len(h) - 2)))
    se = math.sqrt(cov[1, 1] * phi)
    return float(b[1]), float(b[1] - 1.96 * se), float(b[1] + 1.96 * se), phi


def ratio(s, y0, y1):
    i0, i1 = YEARS.index(y0), YEARS.index(y1) + 1
    hs, ss = sum(s["hk"][i0:i1]), sum(s["sg"][i0:i1])
    return hs, ss, (hs / ss if ss else float("nan"))


# ── 自检：主口径逐年复现已发布序列 ─────────────────────────
pub = {}
for kind, rel in (("comp", "raw/patents_families_by_quarter_company_ali_ant_grp.csv"),
                  ("univ", "raw/patents_families_by_quarter_university.csv")):
    d = Counter()
    for r in read(rel):
        d[(r["industry"], r["city"], int(r["quarter"][:4]))] += int(float(r["patent_families"]))
    pub[kind] = d
bad = []
for kind in ("comp", "univ"):
    for i in INDS:
        s = series(i, kind)
        for c in ("hk", "sg"):
            for y, v in zip(YEARS, s[c]):
                if v != pub[kind][(i, c, y)]:
                    bad.append(f"{kind}/{i}/{c}/{y}: {v} vs {pub[kind][(i, c, y)]}")
if bad:
    sys.exit("⛔ 主口径复现不了已发布序列：\n   " + "\n   ".join(bad[:20]))

# ── 口径定义 ────────────────────────────────────────────
NONLOCAL_HK = {"foreign_mnc", "mainland_grp", "lenovo"}
NONLOCAL_SG = {"foreign_mnc", "mainland_grp", "lenovo", "hk_grp"}
ST = re.compile(r"^SENSE ?TIME", re.I)
STEP = {"sg": re.compile(r"^SENSE ?TIME|^MASTERCARD|^SMITH ?& ?NEP", re.I),
        "hk": re.compile(r"^CONTEMPORARY AMPEREX TECHNOLOGY HONG KONG", re.I)}


def nonlocal_drop(extra=frozenset()):
    return all_in(lambda city, a: cat(city, a) in ((NONLOCAL_HK if city == "hk" else NONLOCAL_SG) | extra))


def comp_variants(ind):
    v = [("V0", "主口径", series(ind, "comp"), True),
         ("V1", "两城同剔外地集团", series(ind, "comp", drop=nonlocal_drop()), True),
         ("V2", "V1＋同剔「不确定」", series(ind, "comp", drop=nonlocal_drop(frozenset({"uncertain"}))), True),
         ("V5", "V1＋商汤改归香港", series(ind, "comp", drop=all_in(lambda c, a: cat(c, a) in NONLOCAL_HK),
                                       move_to_hk=lambda ns: all(ST.search(a) for a in ns)), True),
         ("V6", "主口径＋商汤改归香港", series(ind, "comp", move_to_hk=lambda ns: all(ST.search(a) for a in ns)), True)]
    for k in (1, 3, 5, 10):
        tk = topk_names(ind, "comp", k)
        v.append((f"T{k}", f"两城各剔前 {k} 大申请人", series(ind, "comp", drop=all_in(lambda c, a, tk=tk: a in tk[c])), True))
    v.append(("VS", "两城同剔阶梯型主体", series(ind, "comp", drop=all_in(lambda c, a: bool(STEP[c].search(a)))), True))
    v.append(("V4", "只剔新加坡外地集团（不对称，上界）",
              series(ind, "comp", drop=all_in(lambda c, a: c == "sg" and cat(c, a) in NONLOCAL_SG)), False))
    return v


HKBU = re.compile(r"BAPTIST", re.I)


def univ_variants(ind):
    v = [("U0", "主口径", series(ind, "univ"), True)]
    tk = topk_names(ind, "univ", 1)
    v.append(("U1", "两城各剔最大一所大学申请人", series(ind, "univ", drop=all_in(lambda c, a, tk=tk: a in tk[c])), True))
    # U3 只作展示：新加坡大学专利 92–96% 来自 NUS、NTU 两校，剔前 3 个申请人名称等于剔掉整个新加坡大学部门，
    # 而香港有 8 所大学——这不是「对称」口径，不参与判读（2026-10-02 跑出后发现并说明，规则本身未改）
    tk = topk_names(ind, "univ", 3)
    v.append(("U3", "两城各剔前 3 大学申请人（退化，仅展示）", series(ind, "univ", drop=all_in(lambda c, a, tk=tk: a in tk[c])), False))
    v.append(("US", "只剔浸会（阶梯型主体）", series(ind, "univ", drop=all_in(lambda c, a: c == "hk" and bool(HKBU.search(a)))), True))
    return v


# ── 计算与输出 ───────────────────────────────────────────
rows, verdicts = [], []
print("专利港/星比值的登记地敏感性（2015–2023；分类表为草稿，待组员复核）")
print("自检：主口径企业、大学族数与已发布序列逐年一致 ✓")
for kind, label, fn in (("comp", "企业专利", comp_variants), ("univ", "大学专利", univ_variants)):
    for ind in INDS:
        if kind == "univ" and ind == "fintech":
            continue                           # 两城每年都不足 1 件
        print(f"\n━━ {IND_ZH[ind]} · {label} ━━")
        print(f"  {'口径':<26}{'2015–17':>16}{'2021–23':>16}{'年斜率 [95% CI]':>28}")
        sym_lo, sym_hi, lv = [], [], []
        for code, name, s, sym in fn(ind):
            h0, s0, r0 = ratio(s, 2015, 2017)
            h1, s1, r1 = ratio(s, 2021, 2023)
            b, lo, hi, phi = qb_slope(s["hk"], s["sg"])
            mark = "" if sym else "  （不参与判读）"
            print(f"  {code:<4}{name:<22}{h0:>5}/{s0:<5}{r0:>5.2f}{h1:>6}/{s1:<5}{r1:>5.2f}   {b:+.3f} [{lo:+.3f}, {hi:+.3f}]{mark}")
            rows.append([kind, ind, code, name, int(sym), h0, s0, f"{r0:.4f}", h1, s1, f"{r1:.4f}",
                         f"{b:.4f}", f"{lo:.4f}", f"{hi:.4f}", f"{phi:.3f}"] + s["hk"] + s["sg"])
            if sym:
                sym_lo.append(lo); sym_hi.append(hi); lv.append(r1)
        trend = ("比值下降（全部对称口径 CI 上限 < 0）" if max(sym_hi) < 0 else
                 "比值上升（全部对称口径 CI 下限 > 0）" if min(sym_lo) > 0 else "走向不确定")
        level = f"2021–23 区间 {min(lv):.2f}–{max(lv):.2f}" + ("，各口径香港都低于新加坡" if max(lv) < 1 else "")
        print(f"  → 水平：{level}")
        print(f"  → 走向：{trend}")
        verdicts.append((label, ind, level, trend))

print("\n━━ 汇总 ━━")
for label, ind, level, trend in verdicts:
    print(f"  {IND_ZH[ind]:<6}{label:<6} {level}；{trend}")

out = ROOT / "clean" / "rq1_patent_geo_sensitivity.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["kind", "industry", "variant", "variant_name", "symmetric", "hk_2015_17", "sg_2015_17", "ratio_2015_17",
                "hk_2021_23", "sg_2021_23", "ratio_2021_23", "slope", "slope_lo", "slope_hi", "phi"]
               + [f"hk_{y}" for y in YEARS] + [f"sg_{y}" for y in YEARS])
    w.writerows(rows)
with open(out.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump({"inputs": ["raw/patents_families_raw.csv", "config/patents_assignee_sector.csv",
                          "config/patents_assignee_geo_exclude.csv", "config/patents_assignee_hq_class_draft.csv（草稿，待复核）"],
               "script": "scripts/rq1_patent_geo_sensitivity.py",
               "method": "家族级剔除／改归；log(港/星) 年斜率为准二项 logit（Pearson φ），95% CI。判读规则见脚本文件头（红队报告中先写定）。",
               "note": "派生统计量（R1）。主口径与已发布序列逐年核对一致。",
               "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, f, ensure_ascii=False, indent=1)
print(f"\n写入 clean/rq1_patent_geo_sensitivity.csv（{len(rows)} 行）+ prov.json")
