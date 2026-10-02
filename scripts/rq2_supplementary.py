# -*- coding: utf-8 -*-
r"""
rq2_supplementary.py —— RQ2 事后补充分析 S1、S2（规则见 docs/RQ2补充分析计划_2026-10-02.md，跑之前写定）

S1  六单元合并检验：各单元按主检验配对，R = tanh(Σ(n_u−3)·atanh(r_u) / Σ(n_u−3))；
    零分布为每个单元各自独立分块打乱专利序列（块长 4 季）后重算 R，2,000 次。4 项（4 个人才指标）BH-FDR。
    次要：只合并香港三个单元（4 项、单独 FDR）；剔除 fintech/hk 后的 R（描述）。
S2  生医临床试验作第二产出：S2a 全部试验（raw/clinicaltrials_by_quarter.csv）、S2b 企业申办（raw/clinicaltrials_sponsor_by_quarter.csv，
    sponsor_class=INDUSTRY）。生医 4 个人才指标 × 2 城 × 2 产出 = 16 项，单元内分块置换 2,000 次，16 项一起 BH-FDR。
    次要：每个指标、每种产出合并港星两城（同 S1 法），8 项、单独 FDR。
留一检查：只对通过 FDR 的合并检验做——依次去掉一个单元重算 R，任一次变号或 |R| 降到原值一半以下 → 不稳健。
检验力：可侦测最小相关（α=0.05 双侧、80%），按名义 Σ(n_u−3) 与 Bartlett 有效样本量 Σ(n_eff_u−3) 各算一次。

变换、滞后、配对、窗口全部调用 scripts/rq2_leadlag.py 的函数，与主检验一致。主结果 0/24 不被本脚本覆盖。

    python scripts\rq2_supplementary.py > logs\rq2_supplementary_2026-10-02.txt
    → clean/rq2_supplementary_results.csv（+ .prov.json）

R1：只读既有序列，不产生数据值。
"""
import collections
import csv
import datetime
import importlib.util
import json
import math
import os
import pathlib
import random
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rq2", ROOT / "scripts" / "rq2_leadlag.py")
rq2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rq2)
os.chdir(ROOT)

N_PERM = 2000
BLOCK = rq2.BLOCK
LAG = rq2.PREREG_LAG
Z = 1.959964 + 0.841621
LOW_BASE = {("fintech", "hk")}          # 主检验已标记的低基数单元


# ───────── 工具 ─────────
def block_shuffle(y):
    blocks = [y[i:i + BLOCK] for i in range(0, len(y), BLOCK)]
    random.shuffle(blocks)
    return [v for b in blocks for v in b][:len(y)]


def pooled_R(pairs):
    """pairs: [(x, y)]；返回 (R, Σ(n−3))。"""
    num = den = 0.0
    for x, y in pairs:
        r = rq2.pearson(x, y)
        w = len(x) - 3
        num += w * math.atanh(r)
        den += w
    return math.tanh(num / den), den


def pooled_test(pairs, seed):
    R, den = pooled_R(pairs)
    random.seed(seed)
    hits = 0
    for _ in range(N_PERM):
        Rp, _ = pooled_R([(x, block_shuffle(y)) for x, y in pairs])
        if abs(Rp) >= abs(R):
            hits += 1
    return R, (hits + 1) / (N_PERM + 1)


def unit_test(x, y, seed):
    r = rq2.pearson(x, y)
    random.seed(seed)
    hits = sum(1 for _ in range(N_PERM) if abs(rq2.pearson(x, block_shuffle(y))) >= abs(r))
    return r, (hits + 1) / (N_PERM + 1)


def acf(v, k):
    m = st.mean(v)
    d = sum((a - m) ** 2 for a in v)
    return sum((v[i] - m) * (v[i + k] - m) for i in range(len(v) - k)) / d if d else 0.0


def neff(x, y):
    return len(x) / (1 + 2 * sum(acf(x, k) * acf(y, k) for k in range(1, 5)))


def rmin(df):
    return math.tanh(Z / math.sqrt(df)) if df > 0 else float("nan")


def power_txt(pairs):
    nom = sum(len(x) - 3 for x, _ in pairs)
    eff = sum(max(neff(x, y) - 3, 0.5) for x, y in pairs)
    return f"可侦测最小相关：名义 {rmin(nom):.2f}，按有效样本量 {rmin(eff):.2f}"


def loo(pairs_by_unit):
    """留一检查。返回 (是否稳健, 说明)。"""
    R, _ = pooled_R(list(pairs_by_unit.values()))
    notes, ok = [], True
    for u in pairs_by_unit:
        rest = [p for k, p in pairs_by_unit.items() if k != u]
        Rd, _ = pooled_R(rest)
        bad = (Rd * R < 0) or (abs(Rd) < abs(R) / 2)
        ok &= not bad
        notes.append(f"去掉 {'/'.join(u)}: R={Rd:+.3f}{' ✗' if bad else ''}")
    return ok, "；".join(notes)


ROWS = []


def record(analysis, scope, label, output, n, stat, p, fdr_pass, extra=""):
    ROWS.append(dict(analysis=analysis, scope=scope, tai_indicator=label, output=output, n_pairs=n,
                     statistic=round(stat, 4), p_block=round(p, 4), bh_fdr_pass=fdr_pass, note=extra))


# ───────── 载入 ─────────
idi_raw = rq2.load(rq2.IDI_PATH, "patent_families")
idi_g = {u: rq2.yoy(idi_raw[u], "count") for u in rq2.UNITS}
TAI = [(lab, rq2.load(p, c, q, keep), kind) for lab, p, c, q, kind, keep in rq2.TAI_SPEC]

print("=" * 92)
print("RQ2 事后补充分析 S1、S2（探索性；规则见 docs/RQ2补充分析计划_2026-10-02.md）")
print("=" * 92)
print(f"置换 {N_PERM} 次，分块长 {BLOCK} 季，滞后 {LAG} 季。预注册主结果（0/24）不被本分析覆盖。\n")

# ═════════ S1 ═════════
print("─" * 92)
print("S1 六单元合并检验（产出：企业专利族）")
print("─" * 92)
for scope, units, tag in (("六单元", rq2.UNITS, "S1"), ("香港三单元（次要）", [u for u in rq2.UNITS if u[1] == "hk"], "S1HK")):
    res = []
    for lab, d, kind in TAI:
        pu = {}
        for u in units:
            x, y, n = rq2.paired(rq2.yoy(d[u], kind), idi_g[u], LAG)
            pu[u] = (x, y)
        R, p = pooled_test(list(pu.values()), f"{tag}|{lab}")
        res.append((lab, pu, R, p))
    passed = rq2.bh_fdr([(lab, p) for lab, _, _, p in res])
    print(f"【{scope}】")
    print(f"  {'人才指标':18s}{'R':>8}{'Σn':>6}{'p_分块':>9}  FDR   各单元 r（同主检验）")
    for lab, pu, R, p in res:
        rs = " ".join(f"{'/'.join(u)}{rq2.pearson(*v):+.2f}" for u, v in pu.items())
        n = sum(len(v[0]) for v in pu.values())
        print(f"  {lab:18s}{R:>+8.3f}{n:>6}{p:>9.3f}  {'通过' if passed[lab] else '—':4s}  {rs}")
        note = power_txt(list(pu.values()))
        if passed[lab]:
            ok, txt = loo(pu)
            note += f"；留一检查{'稳健' if ok else '不稳健'}：{txt}"
            print(f"      留一检查：{'稳健' if ok else '不稳健'} —— {txt}")
        if tag == "S1":
            keep = {u: v for u, v in pu.items() if u not in LOW_BASE}
            Rx, _ = pooled_R(list(keep.values()))
            note += f"；剔除 fintech/hk 后 R={Rx:+.3f}（描述）"
            print(f"      剔除低基数 fintech/hk 后 R = {Rx:+.3f}（描述）")
        print(f"      {power_txt(list(pu.values()))}")
        record(tag, scope, lab, "企业专利族", n, R, p, passed[lab], note)
    print(f"  通过 FDR：{sum(passed.values())}/{len(passed)}\n")

# ═════════ S2 ═════════
ct_all = collections.defaultdict(dict)
for r in csv.DictReader(open("raw/clinicaltrials_by_quarter.csv", encoding="utf-8-sig")):
    ct_all[r["city"]][r["quarter"]] = float(r["count"])
ct_ind = collections.defaultdict(lambda: collections.defaultdict(float))
for r in csv.DictReader(open("raw/clinicaltrials_sponsor_by_quarter.csv", encoding="utf-8-sig")):
    if r["sponsor_class"] == "INDUSTRY":
        ct_ind[r["city"]][r["quarter"]] += float(r["count"])
OUT = {"S2a 全部临床试验": {c: dict(ct_all[c]) for c in ("hk", "sg")},
       "S2b 企业申办临床试验": {c: dict(ct_ind[c]) for c in ("hk", "sg")}}

print("─" * 92)
print("S2 生物医药：临床试验作第二产出（16 项一起 FDR）")
print("─" * 92)
for name, ser in OUT.items():
    for c in ("hk", "sg"):
        v = list(ser[c].values())
        print(f"  {name} {c}：{min(ser[c])}–{max(ser[c])}，季中位 {st.median(v):.0f}，最小 {min(v):.0f}")
print()
unit_res = []
for name, ser in OUT.items():
    for lab, d, kind in TAI:
        for c in ("hk", "sg"):
            u = ("biomed", c)
            x, y, n = rq2.paired(rq2.yoy(d[u], kind), rq2.yoy(ser[c], "count"), LAG)
            r, p = unit_test(x, y, f"S2|{name}|{lab}|biomed/{c}")
            unit_res.append((name, lab, c, x, y, n, r, p))
passed = rq2.bh_fdr([(f"{a}|{b}|{c}", p) for a, b, c, *_, p in unit_res])
print(f"  {'产出':14s}{'人才指标':18s}{'城市':>4}{'n':>5}{'r':>8}{'p_分块':>9}  FDR")
for name, lab, c, x, y, n, r, p in unit_res:
    k = f"{name}|{lab}|{c}"
    print(f"  {name:14s}{lab:18s}{c:>4}{n:>5}{r:>+8.3f}{p:>9.3f}  {'通过' if passed[k] else '—'}")
    record("S2", f"biomed/{c}", lab, name, n, r, p, passed[k], f"可侦测最小相关：名义 {rmin(n - 3):.2f}，按有效样本量 {rmin(max(neff(x, y) - 3, 0.5)):.2f}")
print(f"  通过 FDR：{sum(passed.values())}/{len(passed)}")
for name in OUT:
    rs = [r for a, *_, r, p in unit_res if a == name]
    print(f"  {name}：8 个相关 正 {sum(r > 0 for r in rs)}、负 {sum(r < 0 for r in rs)}，中位 {st.median(rs):+.3f}")
print()

print("【S2 次要：每个指标、每种产出合并港星两城（8 项、单独 FDR）】")
pres = []
for name, ser in OUT.items():
    for lab, d, kind in TAI:
        pu = {}
        for c in ("hk", "sg"):
            u = ("biomed", c)
            x, y, n = rq2.paired(rq2.yoy(d[u], kind), rq2.yoy(ser[c], "count"), LAG)
            pu[u] = (x, y)
        R, p = pooled_test(list(pu.values()), f"S2P|{name}|{lab}")
        pres.append((name, lab, pu, R, p))
passed = rq2.bh_fdr([(f"{a}|{b}", p) for a, b, _, _, p in pres])
for name, lab, pu, R, p in pres:
    k = f"{name}|{lab}"
    n = sum(len(v[0]) for v in pu.values())
    note = power_txt(list(pu.values()))
    line = f"  {name:14s}{lab:18s} R={R:+.3f}  Σn={n}  p_分块={p:.3f}  {'通过' if passed[k] else '—'}"
    if passed[k]:
        ok, txt = loo(pu)
        note += f"；留一检查{'稳健' if ok else '不稳健'}：{txt}"
        line += f"  留一：{'稳健' if ok else '不稳健'}（{txt}）"
    print(line)
    record("S2-合并", "biomed 港星", lab, name, n, R, p, passed[k], note)
print(f"  通过 FDR：{sum(passed.values())}/{len(passed)}\n")

# ───────── 输出 ─────────
out = ROOT / "clean" / "rq2_supplementary_results.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
    w.writeheader()
    w.writerows(ROWS)
prov = {
    "inputs": ["clean/researchers_stock_by_quarter.csv", "clean/top10pct_by_quarter.csv", "clean/intl_collab_by_quarter.csv",
               "raw/patents_families_by_quarter_company_ali_ant_grp.csv", "raw/clinicaltrials_by_quarter.csv",
               "raw/clinicaltrials_sponsor_by_quarter.csv"],
    "script": "scripts/rq2_supplementary.py",
    "plan": "docs/RQ2补充分析计划_2026-10-02.md（跑之前写定，组长 10/2 确认）",
    "method": "变换、滞后 4 季、配对、窗口同 scripts/rq2_leadlag.py；合并统计量为 Fisher z 按 (n−3) 加权平均；零分布为单元内分块打乱（块长 4 季）2,000 次；各项内部 BH-FDR q=0.05；通过者做留一检查。",
    "note": "事后、探索性补充分析，不覆盖预注册主结果（0/24）。statistic 列：S1 与 S2-合并为合并相关 R，S2 为单元相关 r。",
    "created_utc": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
}
json.dump(prov, open(str(out) + ".prov.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"已写出 {out.relative_to(ROOT)}（{len(ROWS)} 行）与 .prov.json")
