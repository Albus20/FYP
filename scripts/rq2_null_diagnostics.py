# -*- coding: utf-8 -*-
r"""
rq2_null_diagnostics.py —— RQ2 零结果的成因诊断（描述性，不改主检验结果）

主检验（scripts/rq2_leadlag.py）24 项无一通过 FDR。本脚本回答「为什么测不出来」，五项：

  A 同比重叠后的有效样本量：相邻季度的同比共享 3 个季度，研究者存量又是三年滚动计数，
    真正独立的观测比配对数少。按 Bartlett 近似 n_eff = n / (1 + 2 Σ_{k=1..4} ρx(k)ρy(k)) 粗算，
    给出可侦测最小相关（α=0.05 双侧、检验力 80%）。
  B 专利季度噪声：泊松计数噪声在专利同比方差中的占比（delta 法：Var[log(X+1)] ≈ μ/(μ+1)²）。
  C 人才上涨落在可配对窗口之外的比例（专利止于 2023Q4、滞后 4 季 → 人才只能用到 2022Q4）。
  D 企业专利的申请人集中度：前 3 大申请人的族数占比，及其对同比变化方差的贡献（cov/var）。
  E 2015–17 → 2021–23 企业专利年均变化，与研究者存量 2017Q4 → 2024Q4 的倍数对照。
  附：反方向（专利领先人才 4 季）的相关分布——**不在预注册内，只作探索**。

    python scripts\rq2_null_diagnostics.py  > logs\rq2_null_diagnostics_2026-10-02.txt

自检：从 raw/patents_families_raw.csv 按现行规则重建企业专利季度序列，须与
raw/patents_families_by_quarter_company_ali_ant_grp.csv 逐格一致，否则停止。
R1：只读既有序列，不产生数据值。
"""
import collections
import csv
import importlib.util
import math
import os
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rq2", ROOT / "scripts" / "rq2_leadlag.py")
rq2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rq2)
os.chdir(ROOT)                                     # rq2.load 用相对路径

UNITS, LAG = rq2.UNITS, rq2.PREREG_LAG
Z = 1.959964 + 0.841621


def rmin(n):
    return math.tanh(Z / math.sqrt(n - 3)) if n > 3 else float("nan")


def acf(v, k):
    m = st.mean(v)
    d = sum((a - m) ** 2 for a in v)
    return sum((v[i] - m) * (v[i + k] - m) for i in range(len(v) - k)) / d if d else 0.0


def read(rel):
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


idi_raw = rq2.load(rq2.IDI_PATH, "patent_families")
idi_g = {u: rq2.yoy(idi_raw[u], "count") for u in UNITS}
tai_all = {lab: (rq2.load(p, c, q, keep), kind) for lab, p, c, q, kind, keep in rq2.TAI_SPEC}

# ── 自检：重建企业专利序列 ──
SMAP = {r["assignee"].strip(): r["sector"].strip() for r in read("config/patents_assignee_sector.csv")}
EX = {(g["city"], g["assignee"]) for g in read("config/patents_assignee_geo_exclude.csv")
      if g["exclude_level"] in ("ali_grp", "ant_grp")}
FAM = []
for r in read("raw/patents_families_raw.csv"):
    ps = [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]
    cps = [a for a in ps if SMAP.get(a) == "company"]
    hit = [a for a in cps if (r["city"], a) in EX]
    if cps and not (hit and len(hit) == len(cps)):
        FAM.append((r["industry"], r["city"], r["quarter"], [a for a in cps if (r["city"], a) not in EX]))
rebuilt = collections.Counter((i, c, q) for i, c, q, _ in FAM)
bad = [(u, q) for u in UNITS for q, v in idi_raw[u].items() if rebuilt.get((u[0], u[1], q), 0) != v]
assert not bad, f"自检失败：重建序列与发布序列不一致 {bad[:5]}"

print("=" * 88)
print("RQ2 零结果成因诊断（描述性）")
print("=" * 88)
print(f"自检通过：企业专利季度序列由 raw 重建，与 {rq2.IDI_PATH} 逐格一致（{sum(len(v) for v in idi_raw.values())} 格）\n")

# ── A ──
print("── A 同比重叠后的有效样本量 ──")
print("单元内 n 为主检验配对数；ρ1 为同比序列的一阶自相关；r_min 为可侦测最小相关")
rows = []
for lab, (d, kind) in tai_all.items():
    for u in UNITS:
        x, y, n = rq2.paired(rq2.yoy(d[u], kind), idi_g[u], LAG)
        s = sum(acf(x, k) * acf(y, k) for k in range(1, 5))
        neff = n / (1 + 2 * s)
        rows.append((lab, u, n, acf(x, 1), acf(y, 1), neff))
        print(f"  {lab:16s} {u[0]:8s}{u[1]:3s} n={n:2d}  ρ1人才={acf(x, 1):+.2f}  ρ1专利={acf(y, 1):+.2f}  "
              f"n_eff={neff:5.1f}  r_min(n)={rmin(n):.2f}  r_min(n_eff)={rmin(neff):.2f}")
print("  按指标取中位：")
for lab in tai_all:
    sub = [r for r in rows if r[0] == lab]
    print(f"    {lab:16s} n={st.median(r[2] for r in sub):.0f}  n_eff={st.median(r[5] for r in sub):5.1f}  "
          f"r_min(n)={rmin(st.median(r[2] for r in sub)):.2f}  r_min(n_eff)={st.median(rmin(r[5]) for r in sub):.2f}  "
          f"ρ1人才={st.median(r[3] for r in sub):+.2f}")
print("  注：Bartlett 近似在小样本下本身不稳（个别单元 n_eff > n），只作量级参考；显著性检验用的分块置换已处理自相关。\n")

# ── B ──
print("── B 专利同比里的泊松计数噪声占比 ──")
for u in UNITS:
    s = idi_raw[u]
    qs = sorted(s)
    obs = list(idi_g[u].values())
    noise = st.mean(s[qs[i]] / (s[qs[i]] + 1) ** 2 + s[qs[i - 4]] / (s[qs[i - 4]] + 1) ** 2 for i in range(4, len(qs)))
    share = noise / st.pvariance(obs)
    tail = (f"→ 即使完全对应，可观测相关上限 ≈ {math.sqrt(1 - share):.2f}" if share < 1 else
            "→ 近似值超过 100%（delta 法偏大），说明这一格的同比起伏基本都能由计数噪声解释")
    print(f"  {u[0]:8s}{u[1]:3s} 季均 {st.mean(s.values()):5.1f} 族  同比方差 {st.pvariance(obs):.3f}  "
          f"泊松噪声 ≈ {noise:.3f}  占比 ≈ {share:4.0%}  {tail}")
print()

# ── C ──
print("── C 研究者存量的增量有多少落在可配对窗口之外 ──")
d, kind = tai_all["m1_stock 研究者存量"]
for u in UNITS:
    s = d[u]
    qs = sorted(s)
    x, y, n = rq2.paired(rq2.yoy(s, kind), idi_g[u], LAG)
    last = sorted(rq2.yoy(s, kind))[n - 1]
    print(f"  {u[0]:8s}{u[1]:3s} {qs[0]}→{qs[-1]} 存量 {s[qs[0]]:.0f}→{s[qs[-1]]:.0f}（×{s[qs[-1]] / s[qs[0]]:.1f}）；"
          f"可配对人才季度止于 {last}；其后增量占 {(s[qs[-1]] - s[last]) / (s[qs[-1]] - s[qs[0]]):.0%}")
print()

# ── D、E ──
print("── D 企业专利申请人集中度  ／  E 企业专利年均变化 ──")
allq = sorted({q for _, _, q, _ in FAM})
for u in UNITS:
    F = [f for f in FAM if f[0] == u[0] and f[1] == u[1]]
    cnt = collections.Counter(a for f in F for a in set(f[3]))
    top = [a for a, _ in cnt.most_common(3)]
    in_top = lambda f: bool(set(f[3]) & set(top))
    T = collections.Counter(f[2] for f in F)
    K = collections.Counter(f[2] for f in F if in_top(f))
    dT = [T[allq[i]] - T[allq[i - 4]] for i in range(4, len(allq))]
    dK = [K[allq[i]] - K[allq[i - 4]] for i in range(4, len(allq))]
    cov = sum((a - st.mean(dT)) * (b - st.mean(dK)) for a, b in zip(dT, dK)) / len(dT)
    yr = collections.Counter(int(f[2][:4]) for f in F)
    a0 = st.mean(yr[k] for k in (2015, 2016, 2017))
    a1 = st.mean(yr[k] for k in (2021, 2022, 2023))
    print(f"  {u[0]:8s}{u[1]:3s} 族 {len(F):5d}  最大申请人 {top[0][:30]:30s} {cnt[top[0]] / len(F):4.0%}  "
          f"前3合计 {sum(1 for f in F if in_top(f)) / len(F):4.0%}  前3对同比变化方差的贡献 ≈ {cov / st.pvariance(dT):4.0%}  "
          f"| 年均 2015–17 {a0:6.1f} → 2021–23 {a1:6.1f}（{a1 / a0 - 1:+.0%}）")
print()

# ── 附：反方向 ──
print("── 附 反方向：专利领先人才 4 季（不在预注册内，只作探索）──")
rs = []
for lab, (d, kind) in tai_all.items():
    for u in UNITS:
        p, t, n = rq2.paired(idi_g[u], rq2.yoy(d[u], kind), LAG)
        rs.append(rq2.pearson(p, t))
print(f"  24 个相关：正 {sum(r > 0 for r in rs)}、负 {sum(r < 0 for r in rs)}，中位 {st.median(rs):+.2f}，最大 |r| {max(abs(r) for r in rs):.2f}")
