# -*- coding: utf-8 -*-
r"""rq1_conversion_chain.py —— 转化链条与剪刀差：香港的落差出在哪一段（故事线证据，2026-10-02）

两张图、两张表：
  ① 转化链条：每个产业从上游（人才、研究）到下游（知识产权、企业）逐段列出 港/星 比值
       → clean/rq1_conversion_chain.csv、docs/fig/rq1_fig3_conversion_chain.png
  ② 剪刀差：2017–2024 年人才比值与专利比值（大学、企业）的走向
       → clean/rq1_scissors_by_year.csv、docs/fig/rq1_fig4_scissors.png
  屏幕输出另存 logs/rq1_conversion_chain_<日期>.txt

口径（全部沿用已定口径，不新设）：
  研究者存量   2024Q4 存量；剪刀差用各年 Q4，只用窗口完整的季度（2017Q4 起）
  论文数       2022–24 合计（9/11 OpenAlex 版本，clean/intl_collab_by_quarter.csv 的 works）
  高引占比     2022–24 合并（与 RQ1 表 1 同，取自 clean/rq1_levels_trajectories.csv）
  临床试验     2022–24 年均；企业申办 = leadSponsor.class 为 INDUSTRY（J10）
  专利         按申请人三分（企业／大学／公共研究机构），两城同剔阿里＋蚂蚁系（企业档）；末期 2021–23 年均；
               剪刀差用「截至该年的三年合计」（如 2023 = 2021–23），单年件数太少、比值跳动大
  快速支付     2022–24 年均笔数（BIS，J8），只有金融科技；性质是公共支付基础设施的使用，不是企业产出
自检：与 RQ1 表 1、产出篮子已发布的比值逐位核对，对不上就停。
R1：只用既有序列做派生统计。
"""
import csv, json, math, pathlib, statistics as st, sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS = ("ai", "biomed", "fintech")
IND_ZH = {"ai": "人工智能", "biomed": "生物医药", "fintech": "金融科技"}
norm = lambda s: "fintech" if s.startswith("fintech") else s


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ── 读序列 ───────────────────────────────────────────────
RQ1 = {(r["indicator"], r["industry"], r["city"], r["metric"]): float(r["value"])
       for r in read("clean/rq1_levels_trajectories.csv")}
RS = {(norm(r["industry"]), r["city"], r["quarter"]): r for r in read("clean/researchers_stock_by_quarter.csv")}


def pat(kind):
    d = defaultdict(float)
    for r in read(f"raw/patents_families_by_quarter_{kind}.csv"):
        d[(r["industry"], r["city"], int(r["quarter"][:4]))] += float(r["patent_families"])
    return d


PAT = {"企业专利": pat("company_ali_ant_grp"), "大学专利": pat("university"), "公共研究机构专利": pat("public_rd")}

works = defaultdict(float)
for r in read("clean/intl_collab_by_quarter.csv"):
    if 2022 <= int(r["quarter"][:4]) <= 2024:
        works[(norm(r["industry"]), r["city"])] += float(r["works"])

ct_all = defaultdict(float)
for r in read("raw/clinicaltrials_by_quarter.csv"):
    if 2022 <= int(r["quarter"][:4]) <= 2024:
        ct_all[r["city"]] += float(r["count"]) / 3
ct_ind = defaultdict(float)
for r in read("raw/clinicaltrials_sponsor_by_quarter.csv"):
    if 2022 <= int(r["quarter"][:4]) <= 2024 and r["sponsor_class"] == "INDUSTRY":
        ct_ind[r["city"]] += float(r["count"]) / 3
pay = {(r["city"], int(r["year"])): float(r["fast_payments_mn"]) for r in read("clean/payments_digital_by_year.csv") if r["fast_payments_mn"]}

# ── ① 转化链条 ────────────────────────────────────────────
GROUP_ZH = {"research": "研究端（人才、论文、临床）", "univ_ip": "大学知识产权", "firm": "企业端", "public": "公共支付基础设施",
            "research_aligned": "研究端（与专利同窗，只进表）"}
LOW_COUNT = 5        # 两城末期年均都低于此值的格，标为「量太小，不作结论」
chain = []


def add(ind, order, stage, group, window, hk, sg, src):
    r = hk / sg
    low = max(hk, sg) < LOW_COUNT and group != "research"
    chain.append(dict(industry=ind, order=order, stage=stage, group=group, window=window,
                      hk=hk, sg=sg, ratio=r, low_count=int(low), source=src))


for i in INDS:
    add(i, 1, "研究者存量", "research", "2024Q4",
        RQ1[("m1_stock", i, "hk", "level_2024Q4")], RQ1[("m1_stock", i, "sg", "level_2024Q4")], "clean/rq1_levels_trajectories.csv")
    # 与专利窗口（止于 2023）对齐的研究者存量，只进表不进图（红队 C2，2026-10-02）
    add(i, 1.5, "研究者存量（2023Q4，与专利同窗）", "research_aligned", "2023Q4",
        float(RS[(i, "hk", "2023Q4")]["unique_authors"]), float(RS[(i, "sg", "2023Q4")]["unique_authors"]),
        "clean/researchers_stock_by_quarter.csv")
    add(i, 2, "论文数", "research", "2022–24 合计", works[(i, "hk")], works[(i, "sg")], "clean/intl_collab_by_quarter.csv")
    add(i, 3, "高引占比", "research", "2022–24 合并",
        RQ1[("m4", i, "hk", "share_2022_24")], RQ1[("m4", i, "sg", "share_2022_24")], "clean/rq1_levels_trajectories.csv")
    if i == "biomed":
        add(i, 4, "临床试验（全部）", "research", "2022–24 年均", ct_all["hk"], ct_all["sg"], "raw/clinicaltrials_by_quarter.csv")
    for o, name, grp in ((5, "大学专利", "univ_ip"), (6, "企业专利", "firm")):
        hk = sum(PAT[name][(i, "hk", y)] for y in (2021, 2022, 2023)) / 3
        sg = sum(PAT[name][(i, "sg", y)] for y in (2021, 2022, 2023)) / 3
        add(i, o, name, grp, "2021–23 年均", hk, sg, "raw/patents_families_by_quarter_*.csv")
    if i == "biomed":
        add(i, 7, "企业申办临床试验", "firm", "2022–24 年均", ct_ind["hk"], ct_ind["sg"], "raw/clinicaltrials_sponsor_by_quarter.csv")
    if i == "fintech":
        add(i, 8, "快速支付笔数", "public", "2022–24 年均",
            st.mean(pay[("hk", y)] for y in (2022, 2023, 2024)), st.mean(pay[("sg", y)] for y in (2022, 2023, 2024)),
            "clean/payments_digital_by_year.csv")

# 自检：与已发布的数逐位核对
CHECK = {("ai", "研究者存量"): RQ1[("m1_stock", "ai", "hk/sg", "ratio_level_2024Q4")],
         ("biomed", "企业专利"): RQ1[("m8", "biomed", "hk/sg", "ratio_annual_2021_23")],
         ("ai", "企业专利"): RQ1[("m8", "ai", "hk/sg", "ratio_annual_2021_23")],
         ("fintech", "企业专利"): RQ1[("m8", "fintech", "hk/sg", "ratio_annual_2021_23")],
         ("biomed", "临床试验（全部）"): RQ1[("m9_trials", "biomed", "hk/sg", "ratio_annual_2022_24")]}
bask = {(r["industry"], r["item"], r["variant"], r["metric"]): r["value"] for r in read("clean/idi_baskets_by_industry.csv")}
CHECK[("biomed", "企业申办临床试验")] = float(bask[("biomed", "trials", "trials_industry", "ratio")])
CHECK[("fintech", "快速支付笔数")] = float(bask[("fintech", "fast_payments", "main", "ratio")])
bad = []
for (i, stg), ref in CHECK.items():
    got = next(c["ratio"] for c in chain if c["industry"] == i and c["stage"] == stg)
    if abs(got - ref) > 1e-5:
        bad.append(f"{i}/{stg}: 本脚本 {got:.6f} vs 已发布 {ref:.6f}")
if bad:
    sys.exit("⛔ 与已发布的比值对不上：\n   " + "\n   ".join(bad))

print("① 转化链条：香港 ÷ 新加坡（从上游到下游）")
print("   自检：与 RQ1 表 1、产出篮子已发布的比值逐位一致 ✓")
for i in INDS:
    print(f"\n  {IND_ZH[i]}")
    for c in sorted((c for c in chain if c["industry"] == i), key=lambda c: c["order"]):
        flag = "   ← 量太小，不作结论" if c["low_count"] else ""
        print(f"    {c['stage']:<12}{c['ratio']:>6.2f}   （香港 {c['hk']:,.1f}，新加坡 {c['sg']:,.1f}；{c['window']}）{flag}")

# 申请人三分的补充（不进图：公共研究机构专利两城体制差异大，见文末说明）
print("\n  补充：公共研究机构专利 2021–23 年均（香港 ÷ 新加坡）")
for i in INDS:
    hk = sum(PAT["公共研究机构专利"][(i, "hk", y)] for y in (2021, 2022, 2023)) / 3
    sg = sum(PAT["公共研究机构专利"][(i, "sg", y)] for y in (2021, 2022, 2023)) / 3
    print(f"    {IND_ZH[i]:<6} 香港 {hk:.1f}，新加坡 {sg:.1f}" + (f"，比值 {hk / sg:.2f}" if sg else "，新加坡为 0"))

# ── ② 剪刀差 ─────────────────────────────────────────────
YEARS = range(2017, 2025)
sc = []
for i in INDS:
    for y in YEARS:
        h, s = RS[(i, "hk", f"{y}Q4")], RS[(i, "sg", f"{y}Q4")]
        if h["window_full"] == "True" and s["window_full"] == "True":
            hk, sg = float(h["unique_authors"]), float(s["unique_authors"])
            sc.append(dict(industry=i, series="研究者存量", year=y, hk=hk, sg=sg, ratio=hk / sg, note="Q4 存量"))
        for name in ("大学专利", "企业专利"):
            if y > 2023:
                continue
            hk = sum(PAT[name][(i, "hk", t)] for t in (y - 2, y - 1, y))
            sg = sum(PAT[name][(i, "sg", t)] for t in (y - 2, y - 1, y))
            if sg == 0 or max(hk, sg) / 3 < LOW_COUNT:
                continue          # 量太小（金融科技大学专利），不进图
            sc.append(dict(industry=i, series=name, year=y, hk=hk, sg=sg, ratio=hk / sg, note=f"{y - 2}–{y} 三年合计"))

print("\n② 剪刀差：港/星比值走向（研究者为各年 Q4；专利为截至该年的三年合计）")
for i in INDS:
    print(f"\n  {IND_ZH[i]}")
    for name in ("研究者存量", "大学专利", "企业专利"):
        pts = [c for c in sc if c["industry"] == i and c["series"] == name]
        if not pts:
            print(f"    {name:<8}（量太小，不画）")
            continue
        first, last = pts[0], pts[-1]
        print(f"    {name:<8}{first['year']} {first['ratio']:.2f} → {last['year']} {last['ratio']:.2f}   "
              + " ".join(f"{p['ratio']:.2f}" for p in pts))

# ── 写表 ─────────────────────────────────────────────────
for name, data, cols in (("rq1_conversion_chain.csv", chain,
                          ["industry", "order", "stage", "group", "window", "hk", "sg", "ratio", "low_count", "source"]),
                         ("rq1_scissors_by_year.csv", sc, ["industry", "series", "year", "hk", "sg", "ratio", "note"])):
    out = ROOT / "clean" / name
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in data:
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})
    with open(out.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
        json.dump({"inputs": sorted({c.get("source", "") for c in data} - {""}) or
                   ["clean/researchers_stock_by_quarter.csv", "raw/patents_families_by_quarter_university.csv",
                    "raw/patents_families_by_quarter_company_ali_ant_grp.csv"],
                   "script": "scripts/rq1_conversion_chain.py",
                   "method": "港/星比值。窗口与口径见脚本文件头；专利按申请人三分，企业档两城同剔阿里＋蚂蚁系。",
                   "note": "派生统计量（R1）。与 RQ1 表 1、产出篮子已发布比值逐位核对。",
                   "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, f, ensure_ascii=False, indent=1)
print(f"\n写入 clean/rq1_conversion_chain.csv（{len(chain)} 行）、clean/rq1_scissors_by_year.csv（{len(sc)} 行）+ prov.json")

# ── 图 ───────────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
# 色（dataviz 校验：#4a3aa7,#e87ba4,#eda100 all-pairs 通过；后两色对比度 < 3:1 → 全部直接标注数值＋形状区分）
G_COLOR = {"research": "#4a3aa7", "univ_ip": "#e87ba4", "firm": "#eda100", "public": "#8a8984"}
G_MARK = {"research": "o", "univ_ip": "s", "firm": "^", "public": "D"}
TICKS = [0.1, 0.2, 0.5, 1, 2]
fmt = FuncFormatter(lambda v, _: f"{v:g}")
figdir = ROOT / "docs" / "fig"
figdir.mkdir(parents=True, exist_ok=True)
SHORT = {"研究者存量": "研究者\n存量", "论文数": "论文数", "高引占比": "高引\n占比", "临床试验（全部）": "临床试验\n（全部）",
         "大学专利": "大学\n专利", "企业专利": "企业\n专利", "企业申办临床试验": "企业申办\n临床试验", "快速支付笔数": "快速支付\n笔数"}

# 登记地敏感性区间（scripts/rq1_patent_geo_sensitivity.py 的对称口径，2021–23）
RANGE = {}
_sens = ROOT / "clean" / "rq1_patent_geo_sensitivity.csv"
if _sens.exists():
    _acc = defaultdict(list)
    for r in read("clean/rq1_patent_geo_sensitivity.csv"):
        if r["symmetric"] == "1":
            _acc[(r["industry"], "企业专利" if r["kind"] == "comp" else "大学专利")].append(float(r["ratio_2021_23"]))
    RANGE = {k: (min(v), max(v)) for k, v in _acc.items()}
    print("\n  登记地敏感性区间（对称口径，2021–23）：" + "；".join(f"{IND_ZH[i]}{st} {lo:.2f}–{hi:.2f}" for (i, st), (lo, hi) in sorted(RANGE.items())))

# 图 3：转化链条
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=True, gridspec_kw={"width_ratios": [5, 7, 6]})
for ax, i in zip(axes, INDS):
    pts = sorted((c for c in chain if c["industry"] == i and c["group"] != "research_aligned"), key=lambda c: c["order"])
    xs = list(range(len(pts)))
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    for x, p in zip(xs, pts):
        rg = RANGE.get((i, p["stage"]))
        if rg and not p["low_count"]:
            ax.plot([x, x], rg, color=G_COLOR[p["group"]], lw=1.4, alpha=0.55, zorder=2, solid_capstyle="round")
    chain_pts = [(x, p["ratio"]) for x, p in zip(xs, pts) if p["group"] != "public"]   # 公共支付基础设施不在转化链上，不连线
    ax.plot([x for x, _ in chain_pts], [r for _, r in chain_pts], color=GRID, lw=2, zorder=2)
    for x, p in zip(xs, pts):
        hollow = p["low_count"] == 1
        ax.scatter([x], [p["ratio"]], s=64, marker=G_MARK[p["group"]], zorder=3,
                   facecolor="#fcfcfb" if hollow else G_COLOR[p["group"]], edgecolor=G_COLOR[p["group"]], linewidth=1.6)
        lab = f"{p['ratio']:.2f}" + ("*" if hollow else "")
        ax.annotate(lab, (x, p["ratio"]), xytext=(0, 9 if p["ratio"] >= 0.3 else -14), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([SHORT[p["stage"]] for p in pts], fontsize=8)
    ax.set_xlim(-0.6, len(pts) - 0.4)
    ax.set_yscale("log")
    ax.set_ylim(0.1, 2.5)
    ax.yaxis.set_major_locator(FixedLocator(TICKS))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(fmt)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_title(IND_ZH[i], fontsize=10, color=INK, loc="left")
    ax.tick_params(length=0)
axes[0].set_ylabel("香港 ÷ 新加坡（对数刻度）")
axes[0].annotate("持平", (len([c for c in chain if c["industry"] == "ai"]) - 0.45, 1), xytext=(0, 3),
                 textcoords="offset points", fontsize=7.5, color=MUTED, ha="right")
handles = [plt.Line2D([], [], marker=G_MARK[g], ls="", markersize=7, markerfacecolor=G_COLOR[g],
                      markeredgecolor=G_COLOR[g], label=GROUP_ZH[g]) for g in ("research", "univ_ip", "firm", "public")]
fig.legend(handles=handles, loc="upper right", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.99, 0.985))
fig.suptitle("图 3　转化链条：香港的落差集中在「研究 → 知识产权」这一段", x=0.01, y=0.985, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.01, "研究者 2024Q4；论文、高引占比 2022–24；临床试验与快速支付 2022–24 年均；专利 2021–23 年均（企业档两城同剔阿里＋蚂蚁系）。"
         "\n专利点上的竖线：按申请人登记地的各种对称口径（两城同剔外地集团、商汤改归香港、各剔前 k 大申请人等）下的区间，见 clean/rq1_patent_geo_sensitivity.csv。"
         "\n* 金融科技大学专利两城每年都不足 1 件，不作结论。快速支付是公共支付基础设施的使用量，不是企业产出。", fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.09, 1, 0.92))
f3 = figdir / "rq1_fig3_conversion_chain.png"
fig.savefig(f3, dpi=200)
plt.close(fig)

# 图 4：剪刀差
S_STYLE = {"研究者存量": ("research", "-"), "大学专利": ("univ_ip", (0, (4, 2))), "企业专利": ("firm", "-")}
import numpy as np


def _phi(ind, name):
    """年度族数的准二项离散度 φ（与红队裁判 j3 同法），用来放宽三年合计比值的区间。"""
    h = np.array([PAT[name][(ind, "hk", y)] for y in range(2015, 2024)], float)
    s = np.array([PAT[name][(ind, "sg", y)] for y in range(2015, 2024)], float)
    n, t = h + s, np.arange(2015, 2024) - 2019.0
    X = np.column_stack([np.ones_like(t), t]); b = np.zeros(2)
    for _ in range(100):
        pr = 1 / (1 + np.exp(-(X @ b))); W = n * pr * (1 - pr)
        b = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * (X @ b + (h - n * pr) / W)))
    pr = 1 / (1 + np.exp(-(X @ b))); W = n * pr * (1 - pr)
    return max(1.0, float(np.sum((h - n * pr) ** 2 / W) / (len(h) - 2)))


fig, axes = plt.subplots(1, 3, figsize=(11, 4.0), sharey=True)
for ax, i in zip(axes, INDS):
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.axvspan(2023.5, 2026.4, color=GRID, alpha=0.45, lw=0, zorder=0)
    ax.text(2023.62, 2.2, "专利数据\n止于 2023", fontsize=6.5, color=MUTED, va="top")
    for name, (g, ls) in S_STYLE.items():
        pts = [c for c in sc if c["industry"] == i and c["series"] == name]
        if not pts:
            continue
        if name != "研究者存量":
            ph = _phi(i, name)
            lo = [math.exp(math.log(p["ratio"]) - 1.96 * math.sqrt(ph * (1 / p["hk"] + 1 / p["sg"]))) for p in pts]
            hi = [math.exp(math.log(p["ratio"]) + 1.96 * math.sqrt(ph * (1 / p["hk"] + 1 / p["sg"]))) for p in pts]
            ax.fill_between([p["year"] for p in pts], lo, hi, color=G_COLOR[g], alpha=0.13, lw=0, zorder=2)
        ax.plot([p["year"] for p in pts], [p["ratio"] for p in pts], color=G_COLOR[g], lw=2, ls=ls,
                marker=G_MARK[g], markersize=5, zorder=3)
        last = pts[-1]
        ax.annotate(f"{name} {last['ratio']:.2f}", (last["year"], last["ratio"]), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=7.5, color=INK)
    ax.set_yscale("log")
    ax.set_ylim(0.1, 2.5)
    ax.yaxis.set_major_locator(FixedLocator(TICKS))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(fmt)
    ax.set_xlim(2016.6, 2026.4)
    ax.set_xticks([2017, 2019, 2021, 2023])
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_title(IND_ZH[i], fontsize=10, color=INK, loc="left")
    ax.tick_params(length=0)
    if i == "fintech":
        ax.text(2016.8, 0.12, "大学专利每年不足 1 件，不画", fontsize=7, color=MUTED)
axes[0].set_ylabel("香港 ÷ 新加坡（对数刻度）")
handles = [plt.Line2D([], [], color=G_COLOR[g], lw=2, ls=ls, marker=G_MARK[g], markersize=5, label=n)
           for n, (g, ls) in S_STYLE.items()]
fig.legend(handles=handles, loc="upper right", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.99, 0.985))
fig.suptitle("图 4　人才比值追近 1，专利比值一直在低位（专利走向对登记地敏感，只作描述）", x=0.01, y=0.985, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.01, "研究者存量为各年 Q4（只用三年窗口完整的季度，2017Q4 起）；专利为截至该年的三年合计（如 2023 = 2021–23），企业档两城同剔阿里＋蚂蚁系。"
         "\n条带：专利比值的 95% 区间（泊松，按年度离散度 φ 放宽）；灰底：专利数据窗口之外。专利比值的走向随个别申请人的登记地改变，见 clean/rq1_patent_geo_sensitivity.csv。",
         fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.08, 1, 0.92))
f4 = figdir / "rq1_fig4_scissors.png"
fig.savefig(f4, dpi=200)
plt.close(fig)
print(f"图：{f3.relative_to(ROOT).as_posix()}、{f4.relative_to(ROOT).as_posix()}")
