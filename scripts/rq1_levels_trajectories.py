# -*- coding: utf-8 -*-
r"""RQ1 第一问：香港三产业各指标的水平与轨迹，以及与新加坡同产业的相对位置（2026-09-29）

═══ 为什么单独做这一节 ═══

提案 v4.2 的 RQ1 有三问：① 各自呈现何种水平与轨迹 ② TAI–IDI 匹配或错配 ③ 与新加坡的相对位置。
γ 分析（产业效应 vs 城市效应）只回答了③的一部分，且把「香港整体比新加坡高／低」这层城市主效应减掉了。
本脚本直接回答①②③，只做**同产业港星对比**与**单元内时序**，不做跨产业高低比较（学科效应）。

═══ 口径 ═══

    m1 研究者存量    只用三年窗口已满的季度（2017Q4 起 29 期）；末期 = 2024Q4
    m1 新增作者      只用 new_authors_usable 的季度（2018Q1 起 28 期）；末期 = 2024 全年合计
    m4 前10%高引占比  期初 2015–2017、期末 2022–2024，各自按篇数合并计算（Σ高引 ÷ Σ有百分位的论文）
    m5 顶刊份额      同上，core 档；只有 AI、生医
    m7 国际合著比例  同上（Σ国际合著 ÷ Σ论文）；含港—内地合著，待 J7
    m8 企业专利族    两城同剔阿里+蚂蚁系；末期 = 2021–2023 年均；数据截至 2023Q4
    m9 临床试验      只有生医；末期 = 2022–2024 年均；另报 Phase 3（含 2/3 期联合）
    牌照            只有香港金融科技；报累计数

    年化趋势（计数类）：对 log(x+1) 做季度 OLS，年化 = exp(4·斜率) − 1。
    与 rq3_scenarios.py 的基线斜率同法，m8 一行应与 RQ3 文档逐位一致（脚本末尾自动核对）。

R1：只读既有序列，产出派生统计量，不产生新的数据值。

用法：
    python scripts\rq1_levels_trajectories.py
输出：
    clean/rq1_levels_trajectories.csv ＋ .prov.json
    docs/fig/rq1_fig1_hk_sg_ratio.png、docs/fig/rq1_fig2_hk_sg_series.png（装了 matplotlib 才画）
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
CITIES = ("hk", "sg")
IND_ZH = {"ai": "AI", "biomed": "生物医药", "fintech": "金融科技"}
norm = lambda s: "fintech" if s.startswith("fintech") else s


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ann_trend(pairs):
    """pairs: [(季度序号, 值)]，对 log(x+1) 做 OLS，返回年化增长率。"""
    xs = [p[0] for p in pairs]; ys = [math.log(p[1] + 1) for p in pairs]
    mx, my = st.mean(xs), st.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return math.exp(4 * b) - 1


def qidx(q):
    return (int(q[:4]) - 2015) * 4 + int(q[-1]) - 1


def pooled(rows, num, den, years, yearkey):
    n = sum(float(r[num]) for r in rows if int(r[yearkey][:4]) in years and r[num] != "")
    d = sum(float(r[den]) for r in rows if int(r[yearkey][:4]) in years and r[den] != "")
    return n / d if d else None


EARLY, LATE = range(2015, 2018), range(2022, 2025)
out = []           # (indicator, industry, city, metric, value)
put = lambda *a: out.append(a)

# ── m1 ──
rs = read("clean/researchers_stock_by_quarter.csv")
series = defaultdict(dict)
for r in rs:
    series[(norm(r["industry"]), r["city"])][r["quarter"]] = r
for (i, c), d in series.items():
    full = [(qidx(q), float(v["unique_authors"])) for q, v in d.items() if v["window_full"] == "True"]
    put("m1_stock", i, c, "level_2024Q4", float(d["2024Q4"]["unique_authors"]))
    put("m1_stock", i, c, "trend_ann", ann_trend(full))
    put("m1_stock", i, c, "periods", len(full))
    usable = [(qidx(q), float(v["new_authors"])) for q, v in d.items() if v["new_authors_usable"] == "True"]
    put("m1_flow", i, c, "level_2024", sum(float(v["new_authors"]) for q, v in d.items() if q.startswith("2024")))
    put("m1_flow", i, c, "trend_ann", ann_trend(usable))

# ── m4 / m7 / m5 ──
def shares(ind_key, rel, num, den, yearkey, filt=lambda r: True):
    rows = [r for r in read(rel) if filt(r)]
    for i in INDS:
        for c in CITIES:
            u = [r for r in rows if norm(r["industry"]) == i and r["city"] == c]
            if not u:
                continue
            e, l = pooled(u, num, den, EARLY, yearkey), pooled(u, num, den, LATE, yearkey)
            put(ind_key, i, c, "share_2015_17", e)
            put(ind_key, i, c, "share_2022_24", l)
            put(ind_key, i, c, "change_pp", None if e is None or l is None else (l - e) * 100)

shares("m4", "clean/top10pct_by_quarter.csv", "top10_works", "works_with_cnp", "period")
shares("m7", "clean/intl_collab_by_quarter.csv", "intl_works", "works", "quarter")
shares("m5", "clean/topjournal_share_by_year.csv", "local_works", "global_works", "year",
       lambda r: r["tier"] == "core")

# ── m8 ──
for variant, rel in (("m8", "raw/patents_families_by_quarter_company_ali_ant_grp.csv"),
                     ("m8_asis", "raw/patents_families_by_quarter_company_asis.csv")):
    d = defaultdict(dict)
    for r in read(rel):
        d[(norm(r["industry"]), r["city"])][r["quarter"]] = float(r["patent_families"])
    for (i, c), s in d.items():
        late = [v for q, v in s.items() if 2021 <= int(q[:4]) <= 2023]
        early = [v for q, v in s.items() if 2015 <= int(q[:4]) <= 2017]
        put(variant, i, c, "annual_2021_23", sum(late) / 3)
        put(variant, i, c, "annual_2015_17", sum(early) / 3)
        put(variant, i, c, "trend_ann", ann_trend([(qidx(q), v) for q, v in s.items()]))

# ── m9 临床试验（生医）──
ct = defaultdict(dict)
for r in read("raw/clinicaltrials_by_quarter.csv"):
    ct[r["city"]][r["quarter"]] = float(r["count"])
p3 = defaultdict(float)
for r in read("raw/clinicaltrials_phase_by_quarter.csv"):
    if "PHASE3" in r["phase"]:
        p3[(r["city"], r["quarter"][:4])] += float(r["count"])
for c, s in ct.items():
    put("m9_trials", "biomed", c, "annual_2022_24", sum(v for q, v in s.items() if q[:4] in ("2022", "2023", "2024")) / 3)
    put("m9_trials", "biomed", c, "annual_2015_17", sum(v for q, v in s.items() if q[:4] in ("2015", "2016", "2017")) / 3)
    put("m9_trials", "biomed", c, "trend_ann", ann_trend([(qidx(q), v) for q, v in s.items()]))
    put("m9_phase3", "biomed", c, "annual_2022_24", sum(p3[(c, y)] for y in ("2022", "2023", "2024")) / 3)
    put("m9_phase3", "biomed", c, "annual_2015_17", sum(p3[(c, y)] for y in ("2015", "2016", "2017")) / 3)

# ── 牌照（港金科）──
lic = {r["quarter"]: float(r["licenses_cumulative"]) for r in read("clean/fintech_licenses_by_quarter.csv")}
for q in ("2017Q4", "2019Q4", "2024Q4"):
    put("licenses", "fintech", "hk", f"cumulative_{q}", lic[q])

# ── 港/星 比值 ──
V = {(a, i, c, m): v for a, i, c, m, v in out}
RATIO_SPEC = [("m1_stock", "level_2024Q4"), ("m1_flow", "level_2024"), ("m4", "share_2022_24"),
              ("m5", "share_2022_24"), ("m7", "share_2022_24"), ("m8", "annual_2021_23"),
              ("m8_asis", "annual_2021_23"), ("m9_trials", "annual_2022_24"), ("m9_phase3", "annual_2022_24")]
for ind_key, metric in RATIO_SPEC:
    for i in INDS:
        h, s = V.get((ind_key, i, "hk", metric)), V.get((ind_key, i, "sg", metric))
        if h is not None and s:
            put(ind_key, i, "hk/sg", "ratio_" + metric, h / s)
V = {(a, i, c, m): v for a, i, c, m, v in out}

# ── 打印 ──
def f(v, kind):
    if v is None:
        return "—"
    return {"int": f"{v:,.0f}", "1": f"{v:,.1f}", "pct": f"{v:.1%}", "pp": f"{v:+.1f}",
            "g": f"{v:+.1%}", "r": f"{v:.2f}"}[kind]

print("═" * 96)
print("RQ1 · 香港三产业的水平与轨迹（与新加坡同产业对照）")
print("═" * 96)
blocks = [
    ("m1_stock 研究者存量（人，三年窗口）", "m1_stock", [("level_2024Q4", "int", "2024Q4"), ("trend_ann", "g", "年化趋势")]),
    ("m1_flow 新增作者（人）", "m1_flow", [("level_2024", "int", "2024 全年"), ("trend_ann", "g", "年化趋势")]),
    ("m4 前10%高引占比", "m4", [("share_2015_17", "pct", "2015–17"), ("share_2022_24", "pct", "2022–24"), ("change_pp", "pp", "变化(百分点)")]),
    ("m5 顶刊份额（core）", "m5", [("share_2015_17", "pct", "2015–17"), ("share_2022_24", "pct", "2022–24"), ("change_pp", "pp", "变化(百分点)")]),
    ("m7 国际合著比例", "m7", [("share_2015_17", "pct", "2015–17"), ("share_2022_24", "pct", "2022–24"), ("change_pp", "pp", "变化(百分点)")]),
    ("m8 企业专利族（两城同剔，族/年）", "m8", [("annual_2015_17", "1", "2015–17 年均"), ("annual_2021_23", "1", "2021–23 年均"), ("trend_ann", "g", "年化趋势")]),
    ("m8 企业专利族（原样，族/年）", "m8_asis", [("annual_2021_23", "1", "2021–23 年均"), ("trend_ann", "g", "年化趋势")]),
    ("m9 临床试验（件/年，仅生医）", "m9_trials", [("annual_2015_17", "1", "2015–17 年均"), ("annual_2022_24", "1", "2022–24 年均"), ("trend_ann", "g", "年化趋势")]),
    ("m9 其中 Phase 3（件/年）", "m9_phase3", [("annual_2015_17", "1", "2015–17 年均"), ("annual_2022_24", "1", "2022–24 年均")]),
]
for title, key, cols in blocks:
    print(f"\n{title}")
    print(f"  {'':10s}" + "".join(f"{lab:>14s}{'':2s}" for _, _, lab in cols))
    for i in INDS:
        for c in CITIES:
            if not any((key, i, c, m) in V for m, _, _ in cols):
                continue
            print(f"  {i + '/' + c:10s}" + "".join(f"{f(V.get((key, i, c, m)), k):>14s}{'':2s}" for m, k, _ in cols))

print("\n港/星 比值（>1 表示香港高于新加坡）")
print(f"  {'指标':28s}" + "".join(f"{IND_ZH[i]:>10s}" for i in INDS))
for ind_key, metric in RATIO_SPEC:
    vals = [V.get((ind_key, i, "hk/sg", "ratio_" + metric)) for i in INDS]
    if any(v is not None for v in vals):
        print(f"  {ind_key + ' ' + metric:28s}" + "".join(f"{f(v, 'r'):>10s}" for v in vals))
print("\n香港金融科技牌照累计：" + "，".join(f"{q} {V[('licenses', 'fintech', 'hk', 'cumulative_' + q)]:.0f}"
                                   for q in ("2017Q4", "2019Q4", "2024Q4")))

# 与 RQ3 对账
RQ3 = {("ai", "hk"): 7.5, ("ai", "sg"): 15.3, ("biomed", "hk"): 4.1, ("biomed", "sg"): 13.1,
       ("fintech", "hk"): -3.9, ("fintech", "sg"): -7.9}
ok = all(abs(V[("m8", i, c, "trend_ann")] * 100 - v) < 0.051 for (i, c), v in RQ3.items())
print("\n对账：m8 年化趋势与 docs/RQ3情景展望_2026-09-27.md " + ("逐位一致 ✓" if ok else "不一致 ✗——先查清再引用"))

# ── 落盘 ──
dst = ROOT / "clean" / "rq1_levels_trajectories.csv"
with open(dst, "w", encoding="utf-8-sig", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["indicator", "industry", "city", "metric", "value"])
    for a, i, c, m, v in out:
        w.writerow([a, i, c, m, "" if v is None else (f"{v:.6f}" if isinstance(v, float) else v)])
with open(dst.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as fo:
    json.dump({
        "inputs": ["clean/researchers_stock_by_quarter.csv", "clean/top10pct_by_quarter.csv",
                   "clean/topjournal_share_by_year.csv", "clean/intl_collab_by_quarter.csv",
                   "raw/patents_families_by_quarter_company_ali_ant_grp.csv",
                   "raw/patents_families_by_quarter_company_asis.csv",
                   "raw/clinicaltrials_by_quarter.csv", "raw/clinicaltrials_phase_by_quarter.csv",
                   "clean/fintech_licenses_by_quarter.csv"],
        "script": "scripts/rq1_levels_trajectories.py",
        "method": "同产业港星水平、期初(2015–17)/期末(2022–24 或 2021–23)合并比例、log(x+1) 季度 OLS 年化趋势、港/星比值。"
                  "m1 只用窗口已满的季度；新增作者只用 usable 季度。",
        "note": "派生统计量（R1）。m8 年化趋势与 RQ3 文档同法。",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }, fo, ensure_ascii=False, indent=1)
print(f"\n写入 {dst.relative_to(ROOT)}（{len(out)} 行）+ prov.json")

# ── 图（可选）──
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
except ImportError:
    print("未安装 matplotlib，跳过画图")
    sys.exit(0)

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#7d7b75", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
HK, SG = "#2a78d6", "#eb6834"
IND_COLOR = {"ai": "#2a78d6", "biomed": "#eb6834", "fintech": "#1baf7a"}
IND_MARK = {"ai": "o", "biomed": "s", "fintech": "D"}
figdir = ROOT / "docs" / "fig"
figdir.mkdir(parents=True, exist_ok=True)

# 图 1：港/星比值点图
rows_fig = [("m1_stock", "level_2024Q4", "研究者存量", "TAI·规模"),
            ("m1_flow", "level_2024", "新增作者", "TAI·规模"),
            ("m4", "share_2022_24", "前10%高引占比", "TAI·质量"),
            ("m7", "share_2022_24", "国际合著比例*", "TAI·网络"),
            ("m8", "annual_2021_23", "企业专利族", "IDI·创新"),
            ("m9_trials", "annual_2022_24", "临床试验", "IDI·创新")]
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
ys = list(range(len(rows_fig)))[::-1]
ax.axvline(1.0, color="#c3c2b7", lw=1)
ax.axhspan(ys[-1] - 0.5, ys[3] + 0.5 - 1 + 0.0, color="#f3f3f0", zorder=0)
for y, (k, m, lab, dim) in zip(ys, rows_fig):
    ax.axhline(y, color=GRID, lw=0.8, zorder=0)
    for j, i in enumerate(INDS):
        v = V.get((k, i, "hk/sg", "ratio_" + m))
        if v is None:
            continue
        ax.scatter([v], [y + (j - 1) * 0.18], s=34, marker=IND_MARK[i], color=IND_COLOR[i],
                   edgecolor="white", linewidth=1.2, zorder=3, label=IND_ZH[i] if y == ys[0] else None)
        ax.annotate(f"{v:.2f}", (v, y + (j - 1) * 0.18), xytext=(6, -3), textcoords="offset points",
                    fontsize=7, color=INK2)
ax.set_xscale("log")
ax.set_xlim(0.12, 2.2)
ax.set_xticks([0.125, 0.25, 0.5, 1, 2])
ax.set_xticklabels(["1/8", "1/4", "1/2", "持平", "2 倍"])
ax.set_yticks(ys)
ax.set_yticklabels([f"{lab}  {dim}" for _, _, lab, dim in rows_fig], color=INK)
ax.tick_params(axis="y", length=0)
ax.set_xlabel("香港 ÷ 新加坡（对数刻度；1 = 持平）", color=INK2)
ax.legend(loc="upper left", frameon=False, fontsize=8, handletextpad=0.3)
ax.set_title("图 1　同产业港星比值：人才基础持平或更高，企业专利远低于新加坡", loc="left", fontsize=10, color=INK)
fig.text(0.01, 0.005, "末期值：存量 2024Q4；新增作者 2024；比例 2022–24 合并；专利 2021–23 年均（两城同剔阿里+蚂蚁系）；临床试验 2022–24 年均，仅生医。"
         "\n*含港—内地合著；两城同扣「只与内地两方合作」的论文后，2022–24 港/星为 AI 0.86、生医 0.78、金融科技 0.84（2026-10-02 采集，见正文）。", fontsize=6.5, color=MUTED, va="bottom")
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(figdir / "rq1_fig1_hk_sg_ratio.png", facecolor="white")
plt.close(fig)

# 图 2：港星季度序列小多图
Q = [f"{y}Q{q}" for y in range(2015, 2025) for q in range(1, 5)]
def qser(rel, col, qcol="quarter", flt=lambda r: True):
    d = defaultdict(dict)
    for r in read(rel):
        if flt(r) and r[col] != "":
            d[(norm(r["industry"]), r["city"])][r[qcol]] = float(r[col])
    return d
panels = [("研究者存量（人）", qser("clean/researchers_stock_by_quarter.csv", "unique_authors",
                                   flt=lambda r: r["window_full"] == "True"), "int"),
          ("前10%高引占比", qser("clean/top10pct_by_quarter.csv", "top10_share", "period"), "pct"),
          ("国际合著比例*", qser("clean/intl_collab_by_quarter.csv", "intl_share"), "pct"),
          ("企业专利族（族/季）", qser("raw/patents_families_by_quarter_company_ali_ant_grp.csv", "patent_families"), "int")]
fig, axes = plt.subplots(len(panels), 3, figsize=(7.4, 8.2), dpi=200, sharex=True)
for r_i, (lab, d, kind) in enumerate(panels):
    for c_i, i in enumerate(INDS):
        ax = axes[r_i][c_i]
        ax.grid(axis="y", color=GRID, lw=0.7)
        for cc, col, name in (("hk", HK, "香港"), ("sg", SG, "新加坡")):
            s = d.get((i, cc), {})
            xs = [Q.index(q) for q in Q if q in s]
            ysv = [s[q] for q in Q if q in s]
            if not xs:
                continue
            ax.plot(xs, ysv, color=col, lw=1.4, solid_capstyle="round", label=name)
            ax.scatter([xs[-1]], [ysv[-1]], s=12, color=col, edgecolor="white", linewidth=0.8, zorder=3)
        if kind == "pct":
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
        else:
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
                lambda v, _: f"{v / 1000:.0f}k" if v >= 1000 else f"{v:.0f}"))
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(3))
        ax.tick_params(labelsize=7, length=0)
        if r_i == 0:
            ax.set_title(IND_ZH[i], fontsize=9, color=INK)
        if c_i == 0:
            ax.set_ylabel(lab, fontsize=8, color=INK2)
        ax.set_xticks([0, 20, 36])
        ax.set_xticklabels(["2015", "2020", "2024"])
        ax.set_xlim(-1, 40)
handles, labels = axes[0][0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper right", ncol=2, frameon=False, fontsize=8)
fig.suptitle("图 2　港星同产业季度序列（各格纵轴独立，只比同格两线）", x=0.01, ha="left", fontsize=10, color=INK)
fig.text(0.01, 0.005, "研究者存量只画三年窗口已满的季度（2017Q4 起）；专利截至 2023Q4，两城同剔阿里+蚂蚁系；金融科技论文早期季度篇数少，比例跳动大。*含港—内地合著。",
         fontsize=6.5, color=MUTED, va="bottom", wrap=True)
fig.tight_layout(rect=(0, 0.03, 1, 0.965))
fig.savefig(figdir / "rq1_fig2_hk_sg_series.png", facecolor="white")
plt.close(fig)
print(f"图：{(figdir / 'rq1_fig1_hk_sg_ratio.png').relative_to(ROOT)}、{(figdir / 'rq1_fig2_hk_sg_series.png').relative_to(ROOT)}")
