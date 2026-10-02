# -*- coding: utf-8 -*-
r"""rq1_city_main_effect.py —— RQ1 城市主效应：三个产业合起来看，香港与新加坡差在哪里

口径（2026-10-02 组长定稿）：计数指标取 log(x+1)，比例指标用原值；研究者两项只用窗口完整的季度。
城市效应占变异与 scripts/rq1_scale_robustness.py 同一分解（本脚本内置同一函数，并逐位核对 clean/rq1_decomp_by_scale.csv）。

输出：clean/rq1_city_main_effect.csv ＋ .prov.json；屏幕输出另存 logs/rq1_city_main_effect_<日期>.txt
    hk_vs_sg：计数指标 = 各季港/星比值的几何平均（log 刻度下港星差的平均再取 exp）；
              比例指标 = 各季港星之差的平均（百分点）。先在产业内平均，再三产业等权平均。
R1：只用既有序列做派生统计。
"""
import csv, json, math, pathlib, statistics as st, sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS, CITIES = ("ai", "biomed", "fintech"), ("hk", "sg")
norm = lambda s: "fintech" if s.startswith("fintech") else s


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load(rel, col, qcol="quarter", flag=None):
    out = {}
    for r in read(rel):
        if flag and r.get(flag) != "True":
            continue
        if r[col] == "":
            continue
        out[(norm(r["industry"]), r["city"], r[qcol])] = float(r[col])
    return out


def load_b(rel):
    """J7b：扣除只与内地两方合作后的跨境合作比例（10/2 采集）。"""
    out = {}
    for r in read(rel):
        w = int(r["works"])
        if w:
            out[(norm(r["industry"]), r["city"], r["quarter"])] = (int(r["intl_works"]) - int(r["cn_only_works"])) / w
    return out


def city_share(vals):
    """与 rq1_scale_robustness.decompose 同式：城市效应平方和 ÷ 总平方和（z 标准化后）。"""
    allv = list(vals.values())
    mu, sd = st.mean(allv), st.pstdev(allv)
    z = {k: (v - mu) / sd for k, v in vals.items()}
    cells = {(i, c): [v for k, v in z.items() if k[0] == i and k[1] == c] for i in INDS for c in CITIES}
    n = {u: len(v) for u, v in cells.items()}
    um = {u: st.mean(v) for u, v in cells.items()}
    g = st.mean(um.values())
    cm = {c: st.mean([um[(i, c)] for i in INDS]) for c in CITIES}
    ss_tot = sum(v * v for v in z.values())
    return sum(n[u] * (cm[u[1]] - g) ** 2 for u in um) / ss_tot


SPECS = [  # (代号, 名称, 维度, 类型, 序列, 与 rq1_decomp_by_scale.csv 核对的键)
    ("m1_stock", "研究者存量", "规模", "count",
     lambda: load("clean/researchers_stock_by_quarter.csv", "unique_authors", flag="window_full"), ("m1_stock", "可用29期", "log(x+1)")),
    ("m1_flow", "新增作者", "规模", "count",
     lambda: load("clean/researchers_stock_by_quarter.csv", "new_authors", flag="new_authors_usable"), ("m1_flow", "可用28期", "log(x+1)")),
    ("m4", "前10%高引占比", "质量", "share",
     lambda: load("clean/top10pct_by_quarter.csv", "top10_share", "period"), ("m4", "全40期", "水平")),
    ("m7", "国际合著（含港—内地）", "网络", "share",
     lambda: load("clean/intl_collab_by_quarter.csv", "intl_share"), ("m7", "全40期", "水平")),
    ("m7_excl_cn", "国际合著（扣除只与内地合作，10/2 采集）", "网络", "share",
     lambda: load_b("raw/openalex_intl_cn_by_quarter.csv"), None),
    ("m8", "企业专利族", "创新", "count",
     lambda: {k: v for k, v in load("raw/patents_families_by_quarter_company_ali_ant_grp.csv", "patent_families").items()},
     ("m8", "ali_ant_grp", "log(x+1)")),
]

REF = {(r["indicator"], r["variant"], r["scale"]): float(r["share_city"]) for r in read("clean/rq1_decomp_by_scale.csv")}

rows, bad = [], []
print("RQ1 城市主效应（2015–2024，三产业平均；口径：计数 log(x+1)、比例原值、研究者两项只用窗口完整的季度）\n")
print(f"{'指标':<34}{'城市效应占变异':>12}{'三产业平均':>14}   各产业                      同向")
for code, name, dim, kind, fn, refkey in SPECS:
    raw = fn()
    tr = (lambda x: math.log(x + 1)) if kind == "count" else (lambda x: x)
    vals = {k: tr(v) for k, v in raw.items()}
    share = city_share(vals)
    if refkey is not None:
        ref = REF.get(refkey)
        if ref is None or abs(round(share, 4) - ref) > 1e-4:
            bad.append(f"{code}: 本脚本 {share:.4f} vs rq1_decomp_by_scale {ref}")
    per = {}
    for i in INDS:
        qs = sorted({q for (ii, c, q) in vals if ii == i and c == "hk"} & {q for (ii, c, q) in vals if ii == i and c == "sg"})
        per[i] = st.mean(vals[(i, "hk", q)] - vals[(i, "sg", q)] for q in qs)
    avg = st.mean(per.values())
    same = all(v > 0 for v in per.values()) or all(v < 0 for v in per.values())
    if kind == "count":
        fmt = lambda d: f"{math.exp(d):.2f} 倍"
        hk_vs = math.exp(avg)
    else:
        fmt = lambda d: f"{d * 100:+.1f} 个百分点"
        hk_vs = avg * 100
    print(f"{name:<34}{share:>12.1%}{fmt(avg):>14}   " + "，".join(f"{i} {fmt(v)}" for i, v in per.items()) + f"   {'是' if same else '否'}")
    rows.append([code, name, dim, kind, f"{share:.4f}", f"{hk_vs:.4f}", "ratio" if kind == "count" else "pp",
                 *[f"{(math.exp(per[i]) if kind == 'count' else per[i] * 100):.4f}" for i in INDS], int(same)])

if bad:
    sys.exit("⛔ 城市效应占变异与 clean/rq1_decomp_by_scale.csv 对不上：\n   " + "\n   ".join(bad))
print("\n自检：城市效应占变异与 clean/rq1_decomp_by_scale.csv 逐位一致 ✓")

out = ROOT / "clean" / "rq1_city_main_effect.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["indicator", "name", "dimension", "kind", "share_city", "hk_vs_sg", "hk_vs_sg_unit",
                "hk_vs_sg_ai", "hk_vs_sg_biomed", "hk_vs_sg_fintech", "same_direction"])
    w.writerows(rows)
with open(out.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump({
        "inputs": ["clean/researchers_stock_by_quarter.csv", "clean/top10pct_by_quarter.csv",
                   "clean/intl_collab_by_quarter.csv", "raw/openalex_intl_cn_by_quarter.csv",
                   "raw/patents_families_by_quarter_company_ali_ant_grp.csv", "clean/rq1_decomp_by_scale.csv（仅作核对）"],
        "script": "scripts/rq1_city_main_effect.py",
        "method": "城市效应占变异：与 rq1_scale_robustness.py 同一方差分解。hk_vs_sg：产业内各季港星之差（计数为 log(x+1) 之差）取平均，"
                  "三产业等权平均；计数指标取 exp 得几何平均比值，比例指标为百分点。",
        "note": "派生统计量（R1）。口径为 2026-10-02 组长定稿。城市效应只有 1 个自由度，是描述量而非检验结果。",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, f, ensure_ascii=False, indent=1)
print(f"写入 {out.relative_to(ROOT).as_posix()}（{len(rows)} 行）+ prov.json")
