# -*- coding: utf-8 -*-
r"""idi_baskets.py —— 分产业产出篮子：同产业港星比较（组长本地运行，不联网）

口径与判读规则：docs/分产业产出篮子口径_2026-09-30.md（算数之前写定，本脚本逐条照做）

输入（缺哪个就停下并说明，J10 的文件缺了只把检查 e 的「企业申办」一项标为待补）：
    raw/patents_families_by_quarter_company_ali_ant_grp.csv   企业专利族（两城同剔阿里＋蚂蚁系）
    raw/patents_families_by_quarter_company_asis.csv          企业专利族（原样，检查 d）
    raw/clinicaltrials_by_quarter.csv                         临床试验（全部）
    raw/clinicaltrials_phase_by_quarter.csv                   临床试验按期别（检查 e：Phase 3，含 2/3 期联合）
    raw/clinicaltrials_sponsor_by_quarter.csv                 临床试验按申办方（检查 e：仅企业申办；J10，可缺）
    clean/payments_digital_by_year.csv                        快速支付笔数
    raw/worldbank_population_hk_sg.csv                        人口（检查 c）
    clean/rq1_levels_trajectories.csv                         人才侧研究者存量港/星比值（错配判定）
输出：clean/idi_baskets_by_industry.csv ＋ .prov.json；屏幕输出另存 logs/idi_baskets_<日期>.txt

R1：只用既有计数做派生统计，不产生新的数据值。
"""
import csv, json, math, pathlib, statistics as st, sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
CITIES = ("hk", "sg")
IND_ZH = {"ai": "人工智能", "biomed": "生物医药", "fintech": "金融科技"}
F = {
    "pat": "raw/patents_families_by_quarter_company_ali_ant_grp.csv",
    "pat_asis": "raw/patents_families_by_quarter_company_asis.csv",
    "ct": "raw/clinicaltrials_by_quarter.csv",
    "ct_phase": "raw/clinicaltrials_phase_by_quarter.csv",
    "ct_sponsor": "raw/clinicaltrials_sponsor_by_quarter.csv",
    "pay": "clean/payments_digital_by_year.csv",
    "pop": "raw/worldbank_population_hk_sg.csv",
    "rq1": "clean/rq1_levels_trajectories.csv",
}
OPTIONAL = {"ct_sponsor"}
missing = [k for k, rel in F.items() if k not in OPTIONAL and not (ROOT / rel).exists()]
if missing:
    sys.exit("⛔ 缺输入文件：" + "、".join(F[k] for k in missing))


def read(key):
    with open(ROOT / F[key], encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ── 读序列：{(city, 期): 值}；季度期 = "2015Q1"，年度期 = 2015 ──────────────
def patents(key, ind):
    return {(r["city"], r["quarter"]): float(r["patent_families"]) for r in read(key)
            if (r["industry"] == ind or r["industry"].startswith(ind + "_"))}


def trials_all():
    return {(r["city"], r["quarter"]): float(r["count"]) for r in read("ct")}


def trials_phase3():
    out = {}
    for r in read("ct_phase"):
        k = (r["city"], r["quarter"])
        out[k] = out.get(k, 0.0) + (float(r["count"]) if "PHASE3" in r["phase"].split("|") else 0.0)
    return out


def trials_industry():
    if not (ROOT / F["ct_sponsor"]).exists():
        return None
    out = {}
    for r in read("ct_sponsor"):
        k = (r["city"], r["quarter"])
        out[k] = out.get(k, 0.0) + (float(r["count"]) if r["sponsor_class"] == "INDUSTRY" else 0.0)
    return out


def fast_payments():
    return {(r["city"], int(r["year"])): float(r["fast_payments_mn"]) * 1e6
            for r in read("pay") if r["fast_payments_mn"]}


POP = {(r["city"], int(r["year"])): float(r["population"]) for r in read("pop")}


# ── 每一项的定义（第二节表格）───────────────────────────────────────────
def item(ind, name, label, freq, series, late, trend):
    return {"ind": ind, "name": name, "label": label, "freq": freq, "s": series, "late": late, "trend": trend}


def patents_item(ind, key="pat"):
    return item(ind, "patents", "企业专利族", "Q", patents(key, ind), (2021, 2023), (2015, 2023))


def trials_item(series, label="临床试验"):
    return item("biomed", "trials", label, "Q", series, (2022, 2024), (2015, 2024))


BASKETS = {
    "ai": [patents_item("ai")],
    "biomed": [patents_item("biomed"), trials_item(trials_all())],
    "fintech": [item("fintech", "fast_payments", "快速支付笔数", "A", fast_payments(), (2022, 2024), (2019, 2024)),
                patents_item("fintech")],
}


def annual(it, city, y):
    """某城某年的年值；季度序列须四季齐全，否则返回 None。"""
    s = it["s"]
    if it["freq"] == "A":
        return s.get((city, y))
    qs = [s.get((city, f"{y}Q{q}")) for q in range(1, 5)]
    return None if any(v is None for v in qs) else sum(qs)


def late_avg(it, city):
    y0, y1 = it["late"]
    vals = [annual(it, city, y) for y in range(y0, y1 + 1)]
    if any(v is None for v in vals):
        raise RuntimeError(f"{it['ind']}/{it['name']}/{city} 末期 {y0}–{y1} 有缺年，停下")
    return sum(vals) / len(vals)


def slope(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    mx, my = st.mean(xs), st.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def trend_logdiff(it):
    """港/星比值每年的 log 变化（= 两城 log 斜率之差，季度序列 ×4 年化）。与 RQ1 的 ann_trend 同法。"""
    y0, y1 = it["trend"]
    out = {}
    for c in CITIES:
        if it["freq"] == "Q":
            pts = [((int(q[:4]) - 2015) * 4 + int(q[-1]) - 1, math.log(v + 1))
                   for (cc, q), v in it["s"].items() if cc == c and y0 <= int(q[:4]) <= y1]
            out[c] = 4 * slope(pts)
        else:
            pts = [(y, math.log(v + 1)) for (cc, y), v in it["s"].items() if cc == c and y0 <= y <= y1]
            out[c] = slope(pts)
    return out["hk"] - out["sg"], out


def z_gap(it):
    """对照算法：两城各年 log(x+1) 合在一起标准化，末期香港均值 − 新加坡均值。"""
    y0, y1 = it["trend"]
    pts = {(c, y): math.log(annual(it, c, y) + 1) for c in CITIES for y in range(y0, y1 + 1)
           if annual(it, c, y) is not None}
    mu, sd = st.mean(pts.values()), st.pstdev(pts.values())
    l0, l1 = it["late"]
    z = lambda c: st.mean((pts[(c, y)] - mu) / sd for y in range(l0, l1 + 1))
    return z("hk") - z("sg")


def pop_ratio(late):
    y0, y1 = late
    h = st.mean(POP[("hk", y)] for y in range(y0, y1 + 1))
    s = st.mean(POP[("sg", y)] for y in range(y0, y1 + 1))
    return h / s


def ratio(it):
    return late_avg(it, "hk") / late_avg(it, "sg")


def basket_index(items, pc=False):
    lr = [math.log(ratio(it) / (pop_ratio(it["late"]) if pc else 1)) for it in items]
    return math.exp(st.mean(lr))


sgn = lambda x: (x > 0) - (x < 0)
DIR = {1: "高于", -1: "低于", 0: "持平"}

# ── 人才侧对照（错配判定）──────────────────────────────────────────────
TAI = {r["industry"]: float(r["value"]) for r in read("rq1")
       if r["indicator"] == "m1_stock" and r["metric"] == "ratio_level_2024Q4"}

# ── 自检：分项比值必须与 RQ1 表逐位一致（同一数据、同一窗口）──────────────
RQ1_RATIO = {(r["indicator"], r["industry"]): float(r["value"]) for r in read("rq1")
             if r["metric"] in ("ratio_annual_2021_23", "ratio_annual_2022_24")}
chk = [(("m8", i), ratio(patents_item(i))) for i in IND_ZH] + [(("m9_trials", "biomed"), ratio(trials_item(trials_all())))]
bad = [f"{k}: 本脚本 {v:.6f} vs RQ1 {RQ1_RATIO.get(k)}" for k, v in chk
       if k not in RQ1_RATIO or abs(v - RQ1_RATIO[k]) > 1e-5]
if bad:
    sys.exit("⛔ 分项比值与 RQ1 表对不上，停下：\n   " + "\n   ".join(bad))

# ── 计算 ────────────────────────────────────────────────────────────────
rows, verdicts = [], {}
put = lambda ind, it, var, m, v: rows.append([ind, it, var, m, v if isinstance(v, str) else f"{v:.6f}"])
print("分产业产出篮子：同产业港星比较（港/星；> 1 表示香港高）")
print("口径：docs/分产业产出篮子口径_2026-09-30.md｜自检：分项比值与 RQ1 表一致 ✓")

for ind, items in BASKETS.items():
    print(f"\n━━ {IND_ZH[ind]} ━━")
    print(f"  {'分项':<12}{'香港末期年均':>14}{'新加坡末期年均':>16}{'港/星':>8}{'比值年变化':>12}{'z 差':>8}")
    lrs, tds, zs = [], [], []
    for it in items:
        h, s = late_avg(it, "hk"), late_avg(it, "sg")
        r = h / s
        td, _ = trend_logdiff(it)
        zg = z_gap(it)
        lrs.append(math.log(r)); tds.append(td); zs.append(zg)
        win = f"{it['late'][0]}–{str(it['late'][1])[2:]}"
        unit = 1e6 if it["name"] == "fast_payments" else 1
        uz = "（百万笔）" if unit > 1 else ""
        print(f"  {it['label'] + uz:<12}{h / unit:>14,.1f}{s / unit:>16,.1f}{r:>8.2f}{math.exp(td) - 1:>+12.1%}{zg:>+8.2f}   末期 {win}")
        for m, v in (("hk_late", h), ("sg_late", s), ("ratio", r), ("ratio_change_ann", math.exp(td) - 1), ("z_gap", zg)):
            put(ind, it["name"], "main", m, v)
    lnI = st.mean(lrs)
    I, T, Z = math.exp(lnI), math.exp(st.mean(tds)) - 1, st.mean(zs)
    d = sgn(lnI)
    put(ind, "basket", "main", "index", I); put(ind, "basket", "main", "index_change_ann", T); put(ind, "basket", "main", "z_gap", Z)

    # 稳健性检查
    checks = {}
    checks["a"] = ("z 分数对照", sgn(Z) == d, f"z 差 {Z:+.2f}")
    if len(items) > 1:
        checks["b"] = ("每一项单独看", all(sgn(x) == d for x in lrs),
                       "、".join(f"{it['label']} {math.exp(x):.2f}" for it, x in zip(items, lrs)))
    Ipc = basket_index(items, pc=True)
    checks["c"] = ("改用人均", sgn(math.log(Ipc)) == d, f"{Ipc:.2f}")
    alt = [patents_item(ind, "pat_asis") if it["name"] == "patents" else it for it in items]
    Ias = basket_index(alt)
    checks["d"] = ("专利不剔阿里系", sgn(math.log(Ias)) == d, f"{Ias:.2f}")
    put(ind, "basket", "percap", "index", Ipc); put(ind, "basket", "patents_asis", "index", Ias)
    pending = []
    if ind == "biomed":
        alt3 = [trials_item(trials_phase3(), "Phase 3") if it["name"] == "trials" else it for it in items]
        I3 = basket_index(alt3)
        put(ind, "basket", "trials_phase3", "index", I3)
        put(ind, "trials", "trials_phase3", "ratio", ratio(alt3[1]))
        ok3 = sgn(math.log(I3)) == d
        ti = trials_industry()
        if ti is None:
            checks["e"] = ("临床试验改为 Phase 3／仅企业申办", ok3, f"Phase 3：{I3:.2f}；企业申办：待 J10")
            pending.append("e 的企业申办一项待 J10")
        else:
            alti = [trials_item(ti, "企业申办") if it["name"] == "trials" else it for it in items]
            Ii = basket_index(alti)
            put(ind, "basket", "trials_industry", "index", Ii)
            put(ind, "trials", "trials_industry", "ratio", ratio(alti[1]))
            checks["e"] = ("临床试验改为 Phase 3／仅企业申办", ok3 and sgn(math.log(Ii)) == d,
                           f"Phase 3：{I3:.2f}；企业申办：{Ii:.2f}")

    # 判读（第四节）
    core = [k for k in checks if k != "b"]
    if d == 0 or not all(checks[k][1] for k in core):
        verdict = "无法判定"
    elif "b" in checks and not checks["b"][1]:
        verdict = f"综合值{DIR[d]}新加坡，但分项方向相反"
    else:
        verdict = f"稳健地{DIR[d]}新加坡"
    if pending:
        verdict += f"（暂定：{'；'.join(pending)}）"
    tai = TAI.get(ind)
    lag = [it["label"] for it, x in zip(items, lrs) if x < 0]
    if verdict.startswith("无法判定") or tai is None:
        mism = "无法判定"
    elif tai >= 1 and verdict.startswith("稳健地低于"):
        mism = "错配成立"
    elif tai >= 1 and "分项方向相反" in verdict:
        mism = f"错配只对落后分项成立：{'、'.join(lag)}"
    else:
        mism = "不构成错配"
    verdicts[ind] = (I, T, verdict, tai, mism)
    put(ind, "basket", "main", "verdict", verdict); put(ind, "basket", "main", "mismatch", mism)

    print(f"  篮子指数 {I:.2f}（比值每年变化 {T:+.1%}）")
    for k, (name, ok, detail) in checks.items():
        print(f"    检查 {k} {name:<20} {'同向' if ok else '反向'}   {detail}")
    print(f"  → 判读：{verdict}")
    print(f"  → 人才侧研究者存量港/星 {tai:.2f}；错配：{mism}")

# ── 汇总 ────────────────────────────────────────────────────────────────
print("\n━━ 汇总 ━━")
print(f"  {'产业':<8}{'篮子指数':>8}{'年变化':>9}  {'人才侧':>6}  判读 ／ 错配")
for ind, (I, T, v, tai, m) in verdicts.items():
    print(f"  {IND_ZH[ind]:<8}{I:>8.2f}{T:>+9.1%}  {tai:>6.2f}  {v} ／ {m}")

out = ROOT / "clean" / "idi_baskets_by_industry.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["industry", "item", "variant", "metric", "value"]); w.writerows(rows)
prov = {
    "inputs": [rel for k, rel in F.items() if (ROOT / rel).exists()],
    "script": "scripts/idi_baskets.py",
    "method": "各项港/星比值（总量、末期年均）等权几何平均；比值年变化＝两城 log(x+1) OLS 斜率之差（季度×4）；"
              "z 差＝两城各年 log(x+1) 合并标准化后末期港−星；检查 a–e 与判读规则按 docs/分产业产出篮子口径_2026-09-30.md。",
    "note": "派生统计量（R1）。只做同产业港星对比，不跨产业、不进方差分解。分项比值已与 clean/rq1_levels_trajectories.csv 逐位核对。",
    "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
with open(out.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump(prov, f, ensure_ascii=False, indent=1)
print(f"\n写入 {out.relative_to(ROOT).as_posix()}（{len(rows)} 行）+ prov.json")
