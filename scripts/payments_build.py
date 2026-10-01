# -*- coding: utf-8 -*-
r"""payments_build.py —— 港星支付数字化年度表（J8 回传后，组长本地运行）

输入：raw/bis_cpmi_ct1_hk_sg.csv（BIS CPMI 零售支付统计，原样）
      raw/worldbank_population_hk_sg.csv（世界银行人口，人均分母）
输出：clean/payments_digital_by_year.csv ＋ .prov.json
      屏幕输出（另存 logs/payments_build_<日期>.txt）

═══ 选哪几条序列（按 SDMX 维度选，不按标题文字选）═══
    快速支付笔数   INDICATOR_CT=N  MEASURE=N  UNIT_MEASURE=N  INSTRUMENT_TYPE_CT=A   UNIT_MULT=3（千笔）
    电子货币笔数   INDICATOR_CT=M  MEASURE=N  UNIT_MEASURE=N  INSTRUMENT_TYPE_CT=I   UNIT_MULT=6（百万笔）
    借记卡笔数     INDICATOR_CT=M  MEASURE=N  UNIT_MEASURE=N  INSTRUMENT_TYPE_CT=F
    贷记卡笔数     INDICATOR_CT=M  MEASURE=N  UNIT_MEASURE=N  INSTRUMENT_TYPE_CT=H
    BIS 自算人均   同上但 UNIT_MEASURE=Q（只用来交叉核对世界银行分母，不进表）

只用「笔数」，不用「金额」：金额受汇率、消费券（香港 2021 起）影响，且 BIS 金额单位代码未在本仓库核实。
香港的「贷记转账」在这张表里没有报送（新加坡有），不对称，不用。

═══ 定位（组长 9/29 决定，见 docs/金融科技产出口径_2026-09-29.md）═══
    背景指标：只做年度港星对比，不进季度分析，不进任何合成指数。
    主看快速支付（FPS／FAST，账户间即时转账）；电子货币只作辅助——笔数里交通卡占大头，
    新加坡 2020 年起电子货币笔数大降、银行卡笔数上升（疫情＋公交可直接刷银行卡，原因待核实），两城不可比。

R1：只做单位换算与人均折算，不产生新的数据值。
"""
import csv, json, pathlib, sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIS = ROOT / "raw" / "bis_cpmi_ct1_hk_sg.csv"
WB = ROOT / "raw" / "worldbank_population_hk_sg.csv"
OUT = ROOT / "clean" / "payments_digital_by_year.csv"

SERIES = {   # 列名: (INDICATOR_CT, MEASURE, UNIT_MEASURE, INSTRUMENT_TYPE_CT)
    "fast": ("N", "N", "N", "A"),
    "emoney": ("M", "N", "N", "I"),
    "debit_card": ("M", "N", "N", "F"),
    "credit_card": ("M", "N", "N", "H"),
}
BIS_PERCAP = {"fast": ("N", "N", "Q", "A"), "emoney": ("M", "N", "Q", "I")}

WANTED = set(SERIES.values()) | set(BIS_PERCAP.values())

for p in (BIS, WB):
    if not p.exists():
        sys.exit(f"⛔ 找不到 {p.relative_to(ROOT)}")

bis = {}          # (key4, city, year) -> 笔数（已乘 UNIT_MULT）
with open(BIS, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        v = (r.get("OBS_VALUE") or "").strip()
        if not v or v.lower() == "nan":
            continue
        k = (r["INDICATOR_CT"], r["MEASURE"], r["UNIT_MEASURE"], r["INSTRUMENT_TYPE_CT"])
        if k not in WANTED or any(r.get(d, "Z") != "Z" for d in ("WITH_AND_DEP", "TERMINAL_TYPE_CT", "CARD_TYPE")):
            continue
        key = (k, r["REP_CTY"].lower(), int(r["TIME_PERIOD"]))
        if key in bis:
            sys.exit(f"⛔ 同一维度组合出现两次：{key}——序列选择规则不唯一，停下")
        bis[key] = float(v) * 10 ** int(r["UNIT_MULT"] or 0)

pop = {}
with open(WB, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        pop[(r["city"], int(r["year"]))] = int(r["population"])

rows, worst = [], 0.0
for city in ("hk", "sg"):
    for year in range(2012, 2025):
        pp = pop.get((city, year))
        vals = {n: bis.get((k, city, year)) for n, k in SERIES.items()}
        if not pp or all(v is None for v in vals.values()):
            continue
        per = {n: (v / pp if v is not None else None) for n, v in vals.items()}
        cards = (vals["debit_card"] + vals["credit_card"]
                 if vals["debit_card"] is not None and vals["credit_card"] is not None else None)
        for n, k in BIS_PERCAP.items():        # 与 BIS 自算人均交叉核对
            b = bis.get((k, city, year))
            if b and per[n]:
                worst = max(worst, abs(per[n] / b - 1))
        fmt = lambda x, d=2: "" if x is None else f"{x:.{d}f}"
        rows.append([city, year, pp,
                     fmt(vals["fast"] and vals["fast"] / 1e6, 3), fmt(per["fast"]),
                     fmt(vals["emoney"] and vals["emoney"] / 1e6, 3), fmt(per["emoney"]),
                     fmt(cards and cards / 1e6, 3), fmt(cards / pp if cards else None)])

hdr = ["city", "year", "population_wb", "fast_payments_mn", "fast_payments_per_cap",
       "emoney_payments_mn", "emoney_payments_per_cap", "card_payments_mn", "card_payments_per_cap"]
OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(hdr); w.writerows(rows)

# ── 屏幕输出 ──
get = {(r[0], r[1]): r for r in rows}
print("港星支付数字化（每人每年笔数；人口＝世界银行）")
print(f"交叉核对：世界银行分母 vs BIS 自算人均，最大偏差 {worst:.1%}")
print("\n年份   快速支付 港   星   港/星  │ 电子货币 港    星   │ 银行卡 港    星")
for y in range(2015, 2025):
    h, s = get.get(("hk", y)), get.get(("sg", y))
    f = lambda r, i: float(r[i]) if r and r[i] else None
    fh, fs = f(h, 4), f(s, 4)
    ratio = f"{fh / fs:5.2f}" if fh and fs else "   — "
    c = lambda x: f"{x:7.1f}" if x is not None else "      —"
    print(f"{y}  {c(fh)} {c(fs)} {ratio}  │ {c(f(h, 6))} {c(f(s, 6))}  │ {c(f(h, 8))} {c(f(s, 8))}")

prov = {
    "inputs": ["raw/bis_cpmi_ct1_hk_sg.csv", "raw/worldbank_population_hk_sg.csv"],
    "script": "scripts/payments_build.py",
    "method": "BIS WS_CPMI_CT1 按 SDMX 维度取笔数序列（快速支付 N/N/N/A；电子货币 M/N/N/I；借记卡 M/N/N/F；贷记卡 M/N/N/H），"
              "乘 UNIT_MULT 还原为笔，除以世界银行人口得每人每年笔数。不用金额。",
    "note": f"派生统计量（R1）。背景指标，只做年度港星对比。世界银行分母与 BIS 自算人均最大偏差 {worst:.1%}。"
            "香港快速支付 2018 年起（FPS 2018-09 上线），电子货币 2017 年起；电子货币含交通卡，两城不可比。",
    "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
with open(OUT.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump(prov, f, ensure_ascii=False, indent=1)
print(f"\n写入 {OUT.relative_to(ROOT)}（{len(rows)} 行）+ prov.json")
