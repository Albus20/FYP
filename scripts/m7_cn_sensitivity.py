# -*- coding: utf-8 -*-
r"""m7_cn_sensitivity.py —— 扣掉「只和中国内地合作」的论文后，m7 的发现还在不在（J7 回传后运行）

输入：raw/openalex_intl_cn_by_quarter.csv（oa_intl_cn_probe.py 产出）
      clean/intl_collab_by_quarter.csv（9/11 统一采集包的现行 m7，只用于一致性对照）
输出：clean/intl_collab_cn_variants_by_quarter.csv ＋ .prov.json
      屏幕输出（建议另存 logs/m7_cn_sensitivity_<日期>.txt）

═══ 三个口径 ═══
    A     现行：intl_works / works（本次同批重采，与 B 可直接比较）
    B     两城同规则：(intl_works − cn_only_works) / works
          只有「本城 + 中国内地」两方的论文不算国际合著，香港、新加坡都这样扣
    B_hk  只扣香港：香港按 B，新加坡按 A
          （新加坡—内地合作毫无疑问是跨境合作；这一档只作敏感性对照）

═══ 预先写定的判读规则（数据回来之前定，避免看了结果再挑说法）═══
    看 B 口径下 γ(biomed/hk)，与 A 口径比：
      仍 ≥ +0.20 且同号          → 「香港生医国际合著偏高」不依赖港—内地合作，m7 可升格
      降到 +0.10 以下或反号       → 主要由港—内地合作驱动，报告改写为「香港生医与内地联系紧密」
      介于两者之间                → 部分由其驱动，两种说法并列、按比例交代
    同时报告 arcsin√p 刻度下的结果（RQ1 稳健性复查的做法）。

R1：只用既有计数做派生统计，不产生新的数据值。
"""
import csv, json, math, pathlib, statistics as st, sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "openalex_intl_cn_by_quarter.csv"
REF = ROOT / "clean" / "intl_collab_by_quarter.csv"
OUT = ROOT / "clean" / "intl_collab_cn_variants_by_quarter.csv"
INDS, CITIES = ("ai", "biomed", "fintech"), ("hk", "sg")
norm = lambda s: "fintech" if s.startswith("fintech") else s

if not RAW.exists():
    sys.exit(f"⛔ 找不到 {RAW.relative_to(ROOT)}——先让賈贇跑 scripts/oa_intl_cn_probe.py --full")

rows = []
with open(RAW, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        rows.append({"ind": norm(r["industry"]), "label": r["industry"], "city": r["city"], "q": r["quarter"],
                     **{k: int(r[k]) for k in ("works", "intl_works", "cn_any_works", "cn_only_works")}})
cells = {(r["ind"], r["city"]) for r in rows}
if cells != {(i, c) for i in INDS for c in CITIES}:
    sys.exit(f"⛔ 单元不齐：{sorted(cells)}")

ref = {}
if REF.exists():
    with open(REF, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ref[(norm(r["industry"]), r["city"], r["quarter"])] = float(r["intl_share"])


def share(num, den):
    return num / den if den else None


for r in rows:
    r["A"] = share(r["intl_works"], r["works"])
    r["B"] = share(r["intl_works"] - r["cn_only_works"], r["works"])
    r["B_hk"] = r["B"] if r["city"] == "hk" else r["A"]


def decompose(vals):
    allv = list(vals.values()); mu, sd = st.mean(allv), st.pstdev(allv)
    z = {k: (v - mu) / sd for k, v in vals.items()}
    um = {(i, c): st.mean([v for k, v in z.items() if k[0] == i and k[1] == c]) for i in INDS for c in CITIES}
    n = {u: sum(1 for k in z if (k[0], k[1]) == u) for u in um}
    g = st.mean(um.values())
    im = {i: st.mean([um[(i, c)] for c in CITIES]) for i in INDS}
    cm = {c: st.mean([um[(i, c)] for i in INDS]) for c in CITIES}
    ss = sum(v * v for v in z.values())
    inter = sum(n[u] * (um[u] - im[u[0]] - cm[u[1]] + g) ** 2 for u in um) / ss
    city = sum(n[u] * (cm[u[1]] - g) ** 2 for u in um) / ss
    return {i: um[(i, "hk")] - im[i] - cm["hk"] + g for i in INDS}, inter, city


print("═" * 84)
print("m7 国际合著：扣掉「只和中国内地合作」的论文之后")
print("═" * 84)

# ① 一致性：本次 A 与 9/11 现行 m7
if ref:
    diffs = [r["A"] - ref[(r["ind"], r["city"], r["q"])] for r in rows
             if r["A"] is not None and (r["ind"], r["city"], r["q"]) in ref]
    print(f"\n① 一致性：本次口径 A 与 9/11 现行 m7 逐格差，均值 {st.mean(diffs) * 100:+.2f} 个百分点，"
          f"最大绝对差 {max(abs(d) for d in diffs) * 100:.1f}")
    print("   （OpenAlex 会回溯改数，且 countries_distinct_count 与自数口径略有出入；均值在 ±2 以内可放心比较）")

# ② 构成：十年合计
print("\n② 构成（2015–2024 合计）")
print(f"{'单元':<12}{'论文':>9}{'国际合著':>10}{'含内地':>10}{'仅港/星+内地':>14}{'口径A':>9}{'口径B':>9}")
pooled = {}
for i in INDS:
    for c in CITIES:
        rs = [r for r in rows if r["ind"] == i and r["city"] == c]
        W = sum(r["works"] for r in rs); I = sum(r["intl_works"] for r in rs)
        CA = sum(r["cn_any_works"] for r in rs); CO = sum(r["cn_only_works"] for r in rs)
        pooled[(i, c)] = (W, I, CA, CO)
        print(f"{i + '/' + c:<12}{W:>9,}{I:>10,}{CA / max(I, 1):>10.1%}{CO / max(I, 1):>14.1%}"
              f"{I / W:>9.1%}{(I - CO) / W:>9.1%}")
print("   含内地、仅港/星+内地 两列是占国际合著的比例")

# ③ γ 对照
print("\n③ γ（香港侧）与交互占比")
asq = lambda p: math.asin(math.sqrt(min(max(p, 0.0), 1.0)))
res = {}
print(f"{'口径':<8}{'刻度':<10}{'γ ai/hk':>10}{'γ bio/hk':>10}{'γ fin/hk':>10}{'交互':>8}{'城市':>8}")
for v in ("A", "B", "B_hk"):
    for sname, f in (("水平", lambda x: x), ("arcsin√p", asq)):
        vals = {(r["ind"], r["city"], r["q"]): f(r[v]) for r in rows if r[v] is not None}
        g, inter, city = decompose(vals)
        res[(v, sname)] = g
        print(f"{v:<8}{sname:<10}{g['ai']:>+10.3f}{g['biomed']:>+10.3f}{g['fintech']:>+10.3f}{inter:>8.1%}{city:>8.1%}")

# ④ 按预设规则判读
a, b = res[("A", "水平")]["biomed"], res[("B", "水平")]["biomed"]
a2, b2 = res[("A", "arcsin√p")]["biomed"], res[("B", "arcsin√p")]["biomed"]
print("\n④ 判读（规则写在文件头，数据回来前已定）")
print(f"   γ(biomed/hk)：A {a:+.3f} → B {b:+.3f}（水平）；A {a2:+.3f} → B {b2:+.3f}（arcsin√p）")
if b >= 0.20 and b2 >= 0.20 and a * b > 0:
    verdict = "不依赖港—内地合作：扣掉之后香港生医的国际合著仍明显偏高，m7 可以升格为 RQ1 核心发现。"
elif b < 0.10 or b2 < 0.10:
    verdict = "主要由港—内地合作驱动：报告应写成「香港生医与内地联系紧密」，而不是「国际网络更强」。"
else:
    verdict = "部分由港—内地合作驱动：两种说法并列，按 ② 的比例交代各占多少。"
print("   → " + verdict)

# ⑤ 落盘
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["industry", "city", "quarter", "works", "intl_works", "cn_any_works", "cn_only_works",
                "share_A", "share_B", "share_B_hk"])
    for r in rows:
        w.writerow([r["label"], r["city"], r["q"], r["works"], r["intl_works"], r["cn_any_works"],
                    r["cn_only_works"]] + [("" if r[k] is None else f"{r[k]:.6f}") for k in ("A", "B", "B_hk")])
with open(OUT.with_suffix(".csv.prov.json"), "w", encoding="utf-8") as f:
    json.dump({
        "inputs": ["raw/openalex_intl_cn_by_quarter.csv", "clean/intl_collab_by_quarter.csv（仅作一致性对照）"],
        "manifests": ["openalex_intl_cn_by_quarter.csv.manifest.json"],
        "script": "scripts/m7_cn_sensitivity.py",
        "method": "A=intl/works；B=(intl−cn_only)/works，两城同规则；B_hk=仅香港按 B。γ 与分解方法同 rq1_scale_robustness.py。",
        "verdict": verdict,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }, f, ensure_ascii=False, indent=1)
print(f"\n写入 {OUT.relative_to(ROOT)}（{len(rows)} 行）+ prov.json")
