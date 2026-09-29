# -*- coding: utf-8 -*-
r"""RQ1 稳健性复查：方差分解与 γ 对「数据刻度」和「m1 窗口」是否敏感（2026-09-29）

═══ 为什么跑这个 ═══

RQ1 现有两条实质发现都来自「水平」刻度上的加法分解：
    m7 国际合著  biomed/hk  γ = +0.343
    m8 企业专利  fintech/hk γ = +0.329（两城同剔档）
加法分解在水平刻度上会把「差距的绝对值小」算成正交互。计数序列跨单元量级相差
十几倍（m8：fintech/hk 每季约 3 族，biomed/sg 约 64 族），这个问题在计数上最严重。
RQ2 对计数序列用的是 Δlog(x+1)，RQ1 却用水平——两处口径也不一致。

本脚本对同一套数据，在三种刻度下重做分解，看结论是否随刻度改变：
    计数（m1_stock、m1_flow、m8）  水平 ／ √x ／ log(x+1)
    比例（m4、m7）                  水平 ／ arcsin√p ／ 经验 logit
经验 logit = log((k+0.5)/(n−k+0.5))，用各季度的分子分母，避免 0 与 1 处发散。

另报两件事：
    ① m1 的两种窗口：全 40 期 vs prov 标注的可用窗口
       （m1_stock 用 window_full=True 的 29 期；m1_flow 用 new_authors_usable=True 的 28 期）
    ② 城市主效应：同产业港星水平均值。γ 把城市主效应整个减掉了，
       但「与新加坡相比处于何种相对位置」恰恰包含它。

═══ 方法（与 industry_vs_city_decomp.py、gamma_by_variant.py 一致）═══

    每个指标、每种刻度，先对「全部单元 × 全部季度」做 z 标准化（冻结参照集，R-A）
    z = 总均值 + 产业效应 + 城市效应 + 交互 + 时间残差
    γ = 单元均值 − 产业均值 − 城市均值 + 总均值
同一产业两城 γ 大小相等、符号相反，故只报香港侧。

本脚本直接读 clean/ 与 raw/ 的序列，不依赖 clean/indicator_rank_by_quarter.csv。
「水平 + 全 40 期 + ali_ant_grp」一档应逐位复现 docs/提案v4.3_方法章改稿 的方差分解表，
脚本末尾有自动核对。

R1：只读既有清洁序列，不产生任何新的数据值；输出为派生统计量。

用法：
    python scripts\rq1_scale_robustness.py
输出：
    clean/rq1_decomp_by_scale.csv  +  .prov.json
    屏幕输出（建议另存 logs/rq1_scale_robustness_<日期>.txt）
"""
import csv, json, math, pathlib, statistics as st, sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS = ("ai", "biomed", "fintech")
CITIES = ("hk", "sg")


def norm_ind(s):
    # 论文类序列用 fintech_kw，专利类用 fintech —— 跨源必须归一化
    return "fintech" if s.startswith("fintech") else s


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ─────────────────────────── 读数据 ───────────────────────────
def load_count(rel, col, qcol="quarter", flag=None):
    out = {}
    for r in read(rel):
        if flag and r.get(flag) != "True":
            continue
        if r[col] == "":
            continue
        out[(norm_ind(r["industry"]), r["city"], r[qcol])] = float(r[col])
    return out


def load_share(rel, kcol, ncol, pcol, qcol):
    """返回 {key: (p, k, n)}"""
    out = {}
    for r in read(rel):
        if r[pcol] == "":
            continue
        out[(norm_ind(r["industry"]), r["city"], r[qcol])] = (
            float(r[pcol]), float(r[kcol]), float(r[ncol]))
    return out


# ─────────────────────────── 刻度 ───────────────────────────
COUNT_SCALES = {
    "水平": lambda x: x,
    "√x": lambda x: math.sqrt(x),
    "log(x+1)": lambda x: math.log(x + 1),
}
SHARE_SCALES = {
    "水平": lambda p, k, n: p,
    "arcsin√p": lambda p, k, n: math.asin(math.sqrt(p)),
    "经验logit": lambda p, k, n: math.log((k + 0.5) / (n - k + 0.5)),
}


# ─────────────────────────── 分解 ───────────────────────────
def decompose(vals):
    """vals: {(ind, city, q): value}  →  份额与香港侧 γ"""
    allv = list(vals.values())
    mu, sd = st.mean(allv), st.pstdev(allv)
    z = {k: (v - mu) / sd for k, v in vals.items()}
    cells = {(i, c): [v for k, v in z.items() if k[0] == i and k[1] == c]
             for i in INDS for c in CITIES}
    if any(len(v) == 0 for v in cells.values()):
        raise ValueError("六单元不齐")
    n = {u: len(v) for u, v in cells.items()}
    um = {u: st.mean(v) for u, v in cells.items()}
    g = st.mean(um.values())
    im = {i: st.mean([um[(i, c)] for c in CITIES]) for i in INDS}
    cm = {c: st.mean([um[(i, c)] for i in INDS]) for c in CITIES}
    ss_tot = sum(v * v for v in z.values())
    ss_ind = sum(n[u] * (im[u[0]] - g) ** 2 for u in um)
    ss_city = sum(n[u] * (cm[u[1]] - g) ** 2 for u in um)
    ss_int = sum(n[u] * (um[u] - im[u[0]] - cm[u[1]] + g) ** 2 for u in um)
    gam = {i: um[(i, "hk")] - im[i] - cm["hk"] + g for i in INDS}
    periods = sorted({len(v) for v in cells.values()})
    return {
        "industry": ss_ind / ss_tot, "city": ss_city / ss_tot,
        "interaction": ss_int / ss_tot,
        "time": 1 - (ss_ind + ss_city + ss_int) / ss_tot,
        "gamma": gam, "periods": periods[0] if len(periods) == 1 else periods,
    }


# ─────────────────────────── 指标清单 ───────────────────────────
RS = "clean/researchers_stock_by_quarter.csv"
SPECS = [
    # (指标, 窗口/口径标签, 类型, 读取函数)
    ("m1_stock", "全40期", "count", lambda: load_count(RS, "unique_authors")),
    ("m1_stock", "可用29期", "count", lambda: load_count(RS, "unique_authors", flag="window_full")),
    ("m1_flow", "全40期", "count", lambda: load_count(RS, "new_authors")),
    ("m1_flow", "可用28期", "count", lambda: load_count(RS, "new_authors", flag="new_authors_usable")),
    ("m4", "全40期", "share", lambda: load_share("clean/top10pct_by_quarter.csv",
                                               "top10_works", "works_with_cnp", "top10_share", "period")),
    ("m7", "全40期", "share", lambda: load_share("clean/intl_collab_by_quarter.csv",
                                               "intl_works", "works", "intl_share", "quarter")),
    ("m8", "asis", "count", lambda: load_count("raw/patents_families_by_quarter_company_asis.csv", "patent_families")),
    ("m8", "ali_grp", "count", lambda: load_count("raw/patents_families_by_quarter_company_ali_grp.csv", "patent_families")),
    ("m8", "ali_ant_grp", "count", lambda: load_count("raw/patents_families_by_quarter_company_ali_ant_grp.csv", "patent_families")),
]
LABEL = {"m1_stock": "研究者存量", "m1_flow": "新增作者", "m4": "前10%高引占比",
         "m7": "国际合著比例", "m8": "企业专利族"}

results = []
levels = {}
for mk, variant, kind, loader in SPECS:
    raw = loader()
    scales = COUNT_SCALES if kind == "count" else SHARE_SCALES
    for sname, f in scales.items():
        vals = {k: (f(v) if kind == "count" else f(*v)) for k, v in raw.items()}
        d = decompose(vals)
        results.append({"indicator": mk, "variant": variant, "scale": sname, **d})
    # 水平均值，供城市主效应表
    lv = {k: (v if kind == "count" else v[0]) for k, v in raw.items()}
    levels[(mk, variant)] = {(i, c): st.mean([v for k, v in lv.items() if k[0] == i and k[1] == c])
                             for i in INDS for c in CITIES}

# ─────────────────────────── 打印 ───────────────────────────
print("═" * 92)
print("RQ1 稳健性复查：方差分解与 γ（香港侧）对刻度与窗口的敏感性")
print("═" * 92)
hdr = f"{'指标':10s}{'口径':12s}{'刻度':10s}{'产业':>8s}{'城市':>8s}{'交互':>8s}{'时间':>8s}" \
      f"{'γ ai/hk':>10s}{'γ bio/hk':>10s}{'γ fin/hk':>10s}{'期数':>6s}"
print(hdr)
print("─" * 92)
prev = None
for r in results:
    key = (r["indicator"], r["variant"])
    if prev and key[0] != prev[0]:
        print()
    prev = key
    g = r["gamma"]
    print(f"{r['indicator']:10s}{r['variant']:12s}{r['scale']:10s}"
          f"{r['industry']:8.1%}{r['city']:8.1%}{r['interaction']:8.1%}{r['time']:8.1%}"
          f"{g['ai']:+10.3f}{g['biomed']:+10.3f}{g['fintech']:+10.3f}{str(r['periods']):>6s}")

# 符号稳定性
print("\n" + "─" * 92)
print("符号稳定性（|γ| ≥ 0.10 的格，三种刻度下符号是否一致）")
print("─" * 92)
main = [("m1_stock", "全40期"), ("m1_flow", "全40期"), ("m4", "全40期"),
        ("m7", "全40期"), ("m8", "ali_ant_grp")]
for mk, var in main:
    rs = [r for r in results if r["indicator"] == mk and r["variant"] == var]
    for i in INDS:
        vs = [r["gamma"][i] for r in rs]
        if max(abs(v) for v in vs) >= 0.10:
            signs = {1 if v > 0 else -1 for v in vs}
            tag = "一致" if len(signs) == 1 else "**反号**"
            print(f"  {mk:9s}{i+'/hk':12s}" + "  ".join(f"{r['scale']} {r['gamma'][i]:+.3f}" for r in rs) + f"   → {tag}")

# 城市主效应
print("\n" + "─" * 92)
print("城市主效应：同产业港星水平均值（γ 把这一层整个减掉了）")
print("─" * 92)
for mk, var in [("m1_stock", "全40期"), ("m1_flow", "全40期"), ("m4", "全40期"),
                ("m7", "全40期"), ("m8", "ali_ant_grp")]:
    m = levels[(mk, var)]
    fmt = (lambda x: f"{x:.1%}") if mk in ("m4", "m7") else (lambda x: f"{x:,.1f}")
    cells = "   ".join(f"{i}: 港 {fmt(m[(i,'hk')])} / 星 {fmt(m[(i,'sg')])}" for i in INDS)
    print(f"  {mk:9s}{cells}")

# ─────────────────────────── 复现核对 ───────────────────────────
# 方法章改稿（2026-09-27 版）的方差分解表：40 季 + m8 两城同剔档
EXPECT = {
    ("m1_stock", "全40期"): (0.830, 0.001, 0.001),
    ("m1_flow", "全40期"): (0.874, 0.000, 0.000),
    ("m4", "全40期"): (0.367, 0.002, 0.000),
    ("m7", "全40期"): (0.017, 0.144, 0.059),
    ("m8", "ali_ant_grp"): (0.349, 0.278, 0.060),
}
EXPECT_GAMMA = {("m7", "全40期"): (-0.157, +0.343, -0.186),
                ("m8", "ali_ant_grp"): (-0.256, -0.073, +0.329),
                ("m8", "asis"): (-0.216, -0.237, +0.453),
                ("m8", "ali_grp"): (-0.254, -0.058, +0.312)}
print("\n" + "─" * 92)
print("复现核对：水平刻度应逐位等于既有文档数字")
print("─" * 92)
ok = True
for key, (a, b, c) in EXPECT.items():
    r = next(x for x in results if (x["indicator"], x["variant"]) == key and x["scale"] == "水平")
    got = (round(r["industry"], 3), round(r["city"], 3), round(r["interaction"], 3))
    hit = all(abs(x - y) < 0.0006 for x, y in zip(got, (a, b, c)))
    ok &= hit
    print(f"  {key[0]:9s}{key[1]:12s}产业/城市/交互 {got}  {'✓' if hit else '✗ 期望 ' + str((a, b, c))}")
for key, exp in EXPECT_GAMMA.items():
    r = next(x for x in results if (x["indicator"], x["variant"]) == key and x["scale"] == "水平")
    got = tuple(round(r["gamma"][i], 3) for i in INDS)
    hit = all(abs(x - y) < 0.0006 for x, y in zip(got, exp))
    ok &= hit
    print(f"  {key[0]:9s}{key[1]:12s}γ {got}  {'✓' if hit else '✗ 期望 ' + str(exp)}")
print("  → 全部复现" if ok else "  → 有不一致，先查清再引用本脚本数字")

# ─────────────────────────── 落盘 ───────────────────────────
out = ROOT / "clean" / "rq1_decomp_by_scale.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["indicator", "variant", "scale", "share_industry", "share_city",
                "share_interaction", "share_time", "gamma_ai_hk", "gamma_biomed_hk",
                "gamma_fintech_hk", "periods"])
    for r in results:
        g = r["gamma"]
        w.writerow([r["indicator"], r["variant"], r["scale"],
                    f"{r['industry']:.4f}", f"{r['city']:.4f}", f"{r['interaction']:.4f}",
                    f"{r['time']:.4f}", f"{g['ai']:.4f}", f"{g['biomed']:.4f}",
                    f"{g['fintech']:.4f}", r["periods"]])
prov = {
    "inputs": [RS, "clean/top10pct_by_quarter.csv", "clean/intl_collab_by_quarter.csv",
               "raw/patents_families_by_quarter_company_asis.csv",
               "raw/patents_families_by_quarter_company_ali_grp.csv",
               "raw/patents_families_by_quarter_company_ali_ant_grp.csv"],
    "script": "scripts/rq1_scale_robustness.py",
    "method": "每指标×口径×刻度：全部单元×季度 z 标准化后做 产业/城市/交互/时间 分解；γ=单元均值−产业均值−城市均值+总均值（香港侧）。"
              "计数刻度：水平/√x/log(x+1)；比例刻度：水平/arcsin√p/经验 logit log((k+0.5)/(n−k+0.5))。",
    "note": "派生统计量，不产生新的数据值（R1）。水平+全40期+ali_ant_grp 一档复现方法章改稿（2026-09-27）的方差分解表。",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
}
with open(out.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump(prov, f, ensure_ascii=False, indent=1)
print(f"\n写入 {out.relative_to(ROOT)}（{len(results)} 行）+ prov.json")
