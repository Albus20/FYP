# -*- coding: utf-8 -*-
r"""
external_calibration.py —— 外部校准（原姜2，10/4 由 Claude 接手；口径按 tasks/姜同学.md 9/24 写定的三条约束）

问题：人才规模维（研究者存量，学术作者口径）与香港的外部年度序列走势是否一致？
  ① 政府统计处研发人员，按执行界别（高等教育／企业／政府／合计）   clean/rnd_personnel_by_sector_series.csv
  ② InvestHK 初创企业总人数                                         clean/investhk_total_staff_by_year.csv
  ③ 机构层论文产出（港八校合计；另附新加坡两校，作补充）             clean/institutions_works_series.csv

三条口径约束（9/24 写定）：
  · 外部序列为年度，对照在年度层面进行——研究者存量取每年第四季度（三年窗口），2017 年起窗口完整
  · 外部序列无产业细分，校准在「香港整体」层面进行——三个产业分别对照，并报三产业合计（同一作者可能跨产业重复计）
  · 判断依据为趋势方向，不是数值接近

每一对报告：期间年化增速、逐年增长同号的比例、水平相关、增长相关（Δlog）、增长差距最大的年份。
相关只有 7 个增长点，只作描述，不作检验。

    python scripts\external_calibration.py > logs\external_calibration_2026-10-04.txt
    → clean/external_calibration_hk.csv（+ .prov.json）、docs/fig/calib_fig1_index.png

R1：只读既有清洁序列，不产生新的数据值。
"""
import csv
import datetime
import hashlib
import json
import math
import pathlib
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
F_STOCK = ROOT / "clean" / "researchers_stock_by_quarter.csv"
F_RND = ROOT / "clean" / "rnd_personnel_by_sector_series.csv"
F_IHK = ROOT / "clean" / "investhk_total_staff_by_year.csv"
F_WORKS = ROOT / "clean" / "institutions_works_series.csv"
OUT = ROOT / "clean" / "external_calibration_hk.csv"
FIG = ROOT / "docs" / "fig" / "calib_fig1_index.png"
YEARS = list(range(2017, 2025))          # 研究者存量窗口完整的年份
IND_ZH = {"ai": "AI", "biomed": "生物医药", "fintech": "金融科技"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── 人才侧 ──
tai = {}
for r in csv.DictReader(open(F_STOCK, encoding="utf-8-sig")):
    ind = r["industry"].replace("_kw", "")
    y = int(r["quarter"][:4])
    if r["quarter"].endswith("Q4") and r["window_full"] == "True" and y in YEARS:
        tai.setdefault((ind, r["city"]), {})[y] = int(r["unique_authors"])
TAI = {f"研究者存量·{IND_ZH[i]}": tai[(i, "hk")] for i in ("ai", "biomed", "fintech")}
TAI["研究者存量·三产业合计"] = {y: sum(tai[(i, "hk")][y] for i in ("ai", "biomed", "fintech")) for y in YEARS}

# ── 外部侧 ──
EXT = {}
rnd = {r["sector"]: r for r in csv.DictReader(open(F_RND, encoding="utf-8-sig"))}
for sec, zh in (("higher_education", "研发人员·高等教育"), ("business", "研发人员·企业"), ("government", "研发人员·政府"), ("total", "研发人员·合计")):
    EXT[zh] = {y: int(rnd[sec][str(y)]) for y in YEARS}
EXT["InvestHK 初创总人数"] = {int(r["year"]): int(r["count"]) for r in csv.DictReader(open(F_IHK, encoding="utf-8-sig")) if int(r["year"]) in YEARS}
works = list(csv.DictReader(open(F_WORKS, encoding="utf-8-sig")))
EXT["论文·港八校合计"] = {y: sum(int(r[str(y)]) for r in works if r["group"] == "hk8") for y in YEARS}
SUPP = {"论文·新加坡两校合计": {y: sum(int(r[str(y)]) for r in works if r["group"] == "sg") for y in YEARS}}
for k, v in {**EXT, **SUPP}.items():
    assert sorted(v) == YEARS, (k, sorted(v))


def growth(s):
    return {y: math.log(s[y]) - math.log(s[y - 1]) for y in YEARS[1:]}


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return sab / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def cagr(s):
    return (s[YEARS[-1]] / s[YEARS[0]]) ** (1 / (YEARS[-1] - YEARS[0])) - 1


rows = []
print(f"外部校准 · 香港 · {YEARS[0]}–{YEARS[-1]} 年（研究者存量取每年第四季度、三年窗口；外部序列为年度）\n")
print("一、各序列期间年化增速")
for k, v in {**TAI, **EXT, **SUPP}.items():
    print(f"  {k:18s} {v[YEARS[0]]:>8,} → {v[YEARS[-1]]:>8,}   年化 {cagr(v):+6.1%}")

print("\n二、逐对比较（增长同号 = 两条序列在同一年同涨或同跌的年数）")
print(f"  {'人才序列':16s}{'外部序列':18s}{'增速差(人才−外部)':>14}{'增长同号':>9}{'水平相关':>9}{'增长相关':>9}   增长差距最大的年份")
for tk, tv in TAI.items():
    for ek, ev in EXT.items():
        gt, ge = growth(tv), growth(ev)
        ys = YEARS[1:]
        same = sum(1 for y in ys if (gt[y] > 0) == (ge[y] > 0))
        rl = corr([tv[y] for y in YEARS], [ev[y] for y in YEARS])
        rg = corr([gt[y] for y in ys], [ge[y] for y in ys])
        ymax = max(ys, key=lambda y: abs(gt[y] - ge[y]))
        gap = gt[ymax] - ge[ymax]
        rows.append({"tai_series": tk, "ext_series": ek, "years": f"{YEARS[0]}-{YEARS[-1]}",
                     "tai_cagr": round(cagr(tv), 4), "ext_cagr": round(cagr(ev), 4),
                     "growth_same_sign": f"{same}/{len(ys)}", "r_level": round(rl, 3), "r_growth": round(rg, 3),
                     "max_gap_year": ymax, "max_gap_dlog": round(gap, 3)})
        print(f"  {tk:16s}{ek:18s}{cagr(tv) - cagr(ev):>+14.1%}{same:>5}/{len(ys)}{rl:>9.2f}{rg:>9.2f}   {ymax}（{gap:+.2f}）")
    print()

print("三、补充：新加坡（只有论文一条外部序列）")
sg_tai = {y: sum(tai[(i, "sg")][y] for i in ("ai", "biomed", "fintech")) for y in YEARS}
gw, gs = growth(sg_tai), growth(SUPP["论文·新加坡两校合计"])
ys = YEARS[1:]
print(f"  研究者存量·三产业合计（新加坡）年化 {cagr(sg_tai):+.1%}；两校论文年化 {cagr(SUPP['论文·新加坡两校合计']):+.1%}；"
      f"增长同号 {sum(1 for y in ys if (gw[y] > 0) == (gs[y] > 0))}/{len(ys)}；增长相关 {corr([gw[y] for y in ys], [gs[y] for y in ys]):.2f}")

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
OUT.with_suffix(".csv.prov.json").write_text(json.dumps({
    "inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in (F_STOCK, F_RND, F_IHK, F_WORKS)},
    "script": "scripts/external_calibration.py",
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "notes": "口径约束见 tasks/姜同学.md 姜2（9/24 写定）；10/4 由 Claude 接手"}, ensure_ascii=False, indent=1), encoding="utf-8")

# ── 图：2017 = 100 ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
SER = [  # (名称, 序列, 颜色, 线宽, 线型)
    ("研究者存量·三产业合计", TAI["研究者存量·三产业合计"], "#2a78d6", 2.4, "-"),
    ("论文·港八校合计", EXT["论文·港八校合计"], "#2a78d6", 1.4, "--"),
    ("研发人员·高等教育", EXT["研发人员·高等教育"], "#1baf7a", 2.0, "-"),
    ("InvestHK 初创总人数", EXT["InvestHK 初创总人数"], "#eb6834", 1.4, "--"),
    ("研发人员·企业", EXT["研发人员·企业"], "#0b0b0b", 2.0, "-"),
]
fig, ax = plt.subplots(figsize=(8.4, 4.0))
fig.subplots_adjust(left=0.08, right=0.74, top=0.84, bottom=0.17)
ax.axhline(100, color=GRID, lw=1, zorder=0)
for name, s, col, lw, ls in SER:
    v = [100 * s[y] / s[YEARS[0]] for y in YEARS]
    ax.plot(YEARS, v, color=col, lw=lw, ls=ls, marker="o", ms=2.6)
    ax.text(YEARS[-1] + 0.15, v[-1], f"{name} {v[-1]:.0f}", fontsize=8, color=col, va="center", clip_on=False)
ax.set_xticks(YEARS)
ax.set_ylabel(f"{YEARS[0]} 年 = 100")
ax.grid(axis="y", color=GRID, lw=0.6)
fig.suptitle("附图 2　香港：学术人才与大学一侧同步增长，企业研发人员基本持平", x=0.01, y=0.975, ha="left", fontsize=10.5, color=INK)
fig.text(0.01, 0.905, "研究者存量为三年窗口内的不同作者数（学术作者，三产业相加，同一作者可能重复计）；研发人员为政府统计处按执行界别的人数。",
         fontsize=7.6, color=INK2, va="top")
fig.text(0.01, 0.02, "数据：OpenAlex（9/11 采集；港八校论文为 8/26 快照）、政府统计处表 710-86003、InvestHK 初创调查。本图：scripts/external_calibration.py。",
         fontsize=6.6, color=MUTED)
fig.savefig(FIG, dpi=200)
print(f"\n已写出 {OUT.relative_to(ROOT).as_posix()}（{len(rows)} 行）、{FIG.relative_to(ROOT).as_posix()}")
