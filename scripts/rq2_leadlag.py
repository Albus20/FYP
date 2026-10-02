# -*- coding: utf-8 -*-
r"""
rq2_leadlag.py —— RQ2 探索性先行关联检验

═══ 这是提案的第二个研究问题，此前从未跑过 ═══

RQ2：对季度增长率序列，在预先注册的滞后设定下，
     TAI 的变动是否先行于 IDI 相应维度的变动？六个单元的先行方向是否一致？

⚠️ **这是先行关联，不是因果。** 借用 Granger(1969) 的先行—滞后思想，
   但观测数据不能识别因果效应，报告中不得作因果解读。

═══ 数据现实（2026-09-27 实盘清点）═══

IDI 侧只有 m8（企业专利族）一条六单元序列：
    m8   6 单元 × 36 期（2015Q1–2023Q4）
    m9   临床试验只有 2 单元（无产业维），进不了六单元检验
    m9_lic 牌照只有 1 单元（hk/fintech）

所以 RQ2 实际可做的是：**TAI 三维 → m8（创新维）**，滞后 4 季（提案预注册值）。
商业维与资本维无数据，其 8 季／8–12 季滞后设定无法检验。

═══ 两处必须交代的方法选择 ═══

**① 计数序列与比例序列的变换方式不同**

提案 §4.5 步骤③ 写「取同比增长率以去除趋势与季节性」。但：

- **计数序列**（m1_stock、m1_flow、m8）：用 Δlog(x+1) 的同比差分。
  取 log 是为了把乘性增长转成加性；+1 是因为 m8 的 fintech/hk 有 3 个零值季度，
  直接算 x[t]/x[t-4]−1 会除零。
- **比例序列**（m4 前10%高引占比、m7 国际合著比例）：用同比**差分**，不取比值。
  比例本身已归一化（0–1），对一个比例再取「增长率」会让小基数期剧烈放大，
  且分母含义不清。

**② 置换检验用了两种零分布**

提案预注册的是「打乱时间顺序重算一千次」。但简单打乱会**破坏自相关**，
使零分布过窄、显著性被高估——这是时序数据置换检验的已知缺陷。

本脚本同时给出：
- `p_shuffle`：简单打乱（预注册口径，照实报告）
- `p_block`：分块打乱（块长 4 季，保留块内自相关结构，更保守）

**以 p_block 为准。两者差距大本身就是结论的一部分。**

**③ m1 只用窗口完整的季度（2026-10-02 组长定，与 RQ1 一致）**

研究者存量的三年滚动窗口在前 11 季不完整（window_full=False），新增作者在 2018Q1 前有
左截断偏误（new_authors_usable=False），见 clean/researchers_stock_by_quarter.csv.prov.json。
9/27 首跑没有过滤这两段；10/2 起默认过滤，`--full-window` 可复现旧口径作对照。
同时每个检验按「指标|单元」单独设随机种子，结果不随检验顺序或其他检验的样本量变化。

═══ 用法 ═══

    python scripts\rq2_leadlag.py                 # 主结果（预注册滞后 4 季）
    python scripts\rq2_leadlag.py --appendix      # 附全滞后网格（0–8 季）+ FDR 校正
    python scripts\rq2_leadlag.py --full-window   # m1 用全 40 期（9/27 口径，仅作对照）

R1：只读既有清洁序列，不产生任何数据值。
"""
import argparse
import collections
import csv
import math
import pathlib
import random
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS = ("ai", "biomed", "fintech")
CITIES = ("hk", "sg")
UNITS = [(i, c) for i in INDS for c in CITIES]

PREREG_LAG = 4          # 提案预注册：人才 → 创新 4 个季度
N_PERM = 1000
BLOCK = 4               # 分块置换的块长（一年）
LOW_BASE_MEDIAN = 5     # 中位数低于此值的计数序列标记为低基数

random.seed(20260927)   # 置换检验可复现


# ───────── 载入 ─────────

def load(path, valcol, qcol="quarter", keep=None):
    """keep：只保留该列为 True 的行（m1 的窗口完整／可用标记）。"""
    d = collections.defaultdict(dict)
    p = ROOT / path
    if not p.exists():
        return None
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        if keep and str(r.get(keep, "")).strip() != "True":
            continue
        v = r.get(valcol, "")
        if v in ("", None):
            continue
        # 论文类用 fintech_kw，专利类用 fintech，必须归一化
        ind = "fintech" if r["industry"] == "fintech_kw" else r["industry"]
        try:
            d[(ind, r["city"])][r[qcol]] = float(v)
        except ValueError:
            continue
    return d


# ───────── 变换 ─────────

def yoy(series, kind):
    """同比变换。返回 {quarter: 变换值}，前 4 期无值。

    kind="count"  → Δlog(x+1)：乘性增长转加性，且容得下零值
    kind="share"  → 同比差分：比例已归一化，不再取比值
    """
    qs = sorted(series)
    out = {}
    for i, q in enumerate(qs):
        if i < 4:
            continue
        a, b = series[q], series[qs[i - 4]]
        if kind == "count":
            out[q] = math.log(a + 1) - math.log(b + 1)
        else:
            out[q] = a - b
    return out


# ───────── 统计 ─────────

def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def paired(tai_g, idi_g, lag):
    """TAI[t] 与 IDI[t+lag] 配对。返回 (x, y, 期数)。"""
    qs = sorted(set(tai_g) | set(idi_g))
    idx = {q: i for i, q in enumerate(qs)}
    x, y = [], []
    for q in sorted(tai_g):
        j = idx[q] + lag
        if j < len(qs):
            q2 = qs[j]
            if q2 in idi_g:
                x.append(tai_g[q])
                y.append(idi_g[q2])
    return x, y, len(x)


def perm_p(x, y, obs, block=None):
    """置换检验。block=None 为简单打乱；否则按块长分块后打乱块序。"""
    if obs is None:
        return None
    hits = 0
    for _ in range(N_PERM):
        if block:
            blocks = [y[i:i + block] for i in range(0, len(y), block)]
            random.shuffle(blocks)
            yp = [v for b in blocks for v in b][:len(y)]
        else:
            yp = y[:]
            random.shuffle(yp)
        r = pearson(x, yp)
        if r is not None and abs(r) >= abs(obs):
            hits += 1
    return (hits + 1) / (N_PERM + 1)      # 加一校正，避免报 p=0


def bh_fdr(pairs, q=0.05):
    """Benjamini–Hochberg。pairs=[(标签, p)]，返回 {标签: 是否通过}。"""
    valid = [(k, p) for k, p in pairs if p is not None]
    m = len(valid)
    if not m:
        return {}
    ranked = sorted(valid, key=lambda t: t[1])
    passed, cut = {}, 0
    for i, (k, p) in enumerate(ranked, 1):
        if p <= q * i / m:
            cut = i
    for i, (k, p) in enumerate(ranked, 1):
        passed[k] = i <= cut
    return passed


# ───────── 主流程 ─────────

TAI_SPEC = [   # 最后一列：只保留该标记为 True 的季度（None = 不过滤）
    ("m1_stock 研究者存量", "clean/researchers_stock_by_quarter.csv", "unique_authors", "quarter", "count", "window_full"),
    ("m1_flow 新增作者",    "clean/researchers_stock_by_quarter.csv", "new_authors",    "quarter", "count", "new_authors_usable"),
    ("m4 前10%高引占比",    "clean/top10pct_by_quarter.csv",          "top10_share",    "period",  "share", None),
    ("m7 国际合著比例",     "clean/intl_collab_by_quarter.csv",       "intl_share",     "quarter", "share", None),
]
IDI_PATH = "raw/patents_families_by_quarter_company_ali_ant_grp.csv"


def main(appendix=False, full_window=False):
    print("=" * 84)
    print("RQ2 探索性先行关联检验 —— TAI → IDI 创新维（企业专利族）")
    print("=" * 84)
    print("⚠️ 先行关联，非因果。以下一律不作因果解读。")
    print("m1 窗口：" + ("全 40 期（9/27 口径，仅作对照）" if full_window else "只用窗口完整的季度（10/2 定）") + "\n")

    idi_raw = load(IDI_PATH, "patent_families")
    if idi_raw is None:
        print(f"⛔ 找不到 {IDI_PATH}")
        return
    idi_g = {u: yoy(idi_raw[u], "count") for u in UNITS if u in idi_raw}

    # 低基数标记
    low = {u for u in UNITS if u in idi_raw
           and st.median(list(idi_raw[u].values())) < LOW_BASE_MEDIAN}
    if low:
        print("⚠️ 低基数单元（IDI 中位数 < %d，增长率不稳定，结果仅供参考）：" % LOW_BASE_MEDIAN)
        for u in sorted(low):
            v = list(idi_raw[u].values())
            print(f"     {u[0]}/{u[1]}  中位 {st.median(v):.1f}  最小 {min(v):.0f}  "
                  f"零值 {sum(1 for x in v if x == 0)} 期")
        print()

    tais = []
    for label, path, col, qc, kind, keep in TAI_SPEC:
        d = load(path, col, qc, None if full_window else keep)
        if d is None:
            print(f"  ! 缺 {path}，跳过 {label}")
            continue
        tais.append((label, {u: yoy(d[u], kind) for u in UNITS if u in d}, kind))

    # ── 主结果：预注册滞后 ──
    print("─" * 84)
    print(f"主结果 · 预注册滞后 {PREREG_LAG} 季（人才 → 创新）")
    print("─" * 84)
    print(f"{'TAI 指标':22s}{'单元':13s}{'r':>8}{'n':>5}{'p_打乱':>9}{'p_分块':>9}   标记")

    prereg = []
    for label, tg, kind in tais:
        for u in UNITS:
            if u not in tg or u not in idi_g:
                continue
            x, y, n = paired(tg[u], idi_g[u], PREREG_LAG)
            r = pearson(x, y)
            random.seed(f"{label}|{u[0]}/{u[1]}")      # 每个检验独立设种子
            if r is None:
                print(f"{label:22s}{u[0]+'/'+u[1]:13s}{'—':>8}{n:>5}  方差为零，无法计算")
                continue
            ps = perm_p(x, y, r)
            pb = perm_p(x, y, r, block=BLOCK)
            prereg.append((f"{label}|{u[0]}/{u[1]}", r, n, ps, pb, u in low))
            mark = "低基数" if u in low else ("*" if pb is not None and pb < 0.05 else "")
            print(f"{label:22s}{u[0]+'/'+u[1]:13s}{r:>+8.3f}{n:>5}{ps:>9.3f}{pb:>9.3f}   {mark}")
        print()

    # ── 方向一致性 ──
    print("─" * 84)
    print("方向一致性 · 小样本下的复制证据")
    print("─" * 84)
    print("六个单元若先行方向一致，构成复制证据；方向散乱则无。\n")
    print(f"{'TAI 指标':22s}{'正向':>6}{'负向':>6}{'一致?':>8}   中位 r")
    for label, tg, kind in tais:
        rs = [r for k, r, n, ps, pb, lo in prereg if k.startswith(label + "|")]
        if not rs:
            continue
        pos, neg = sum(1 for r in rs if r > 0), sum(1 for r in rs if r < 0)
        agree = "是" if pos == len(rs) or neg == len(rs) else ("偏向" if max(pos, neg) >= 5 else "否")
        print(f"{label:22s}{pos:>6}{neg:>6}{agree:>8}   {st.median(rs):+.3f}")

    # ── 多重检验 ──
    print()
    print("─" * 84)
    print(f"多重检验校正 · BH-FDR（q=0.05，共 {len(prereg)} 个预注册检验）")
    print("─" * 84)
    passed = bh_fdr([(k, pb) for k, r, n, ps, pb, lo in prereg])
    survivors = [k for k, v in passed.items() if v]
    if survivors:
        print("通过 FDR 校正的：")
        for k in survivors:
            row = next(t for t in prereg if t[0] == k)
            tag = "（低基数，谨慎）" if row[5] else ""
            print(f"    {k}   r={row[1]:+.3f}  p_分块={row[4]:.3f} {tag}")
    else:
        print("**无一通过。**")
        print("在预注册的滞后 4 季设定下，未发现 TAI 先行于 IDI 创新维的证据。")
        print("按提案 §4.5 步骤③：零结果照实报告——可靠的「无先行证据」同样是交付物。")

    # ── 附录 ──
    if appendix:
        print()
        print("=" * 84)
        print("附录 · 全滞后网格（0–8 季）")
        print("=" * 84)
        print("提案要求其余滞后一并汇报，且不以拟合优度择优。\n")
        for label, tg, kind in tais:
            print(f"【{label}】")
            print(f"{'单元':13s}" + "".join(f"{('L'+str(L)):>8}" for L in range(9)))
            for u in UNITS:
                if u not in tg or u not in idi_g:
                    continue
                cells = []
                for L in range(9):
                    x, y, n = paired(tg[u], idi_g[u], L)
                    r = pearson(x, y)
                    cells.append(f"{r:>+8.2f}" if r is not None else f"{'—':>8}")
                print(f"{u[0]+'/'+u[1]:13s}" + "".join(cells))
            print()

    # ── 检验力：零结果必须配这个才能解释 ──
    print()
    print("=" * 84)
    print("检验力 · 这个零结果能说明什么")
    print("=" * 84)
    n = min(t[2] for t in prereg) if prereg else 0      # 取最短的一组（m1 过滤后对数最少）
    if n > 3:
        # Fisher z：双侧 α=.05、power=.80 下可侦测的最小 |r|
        se = 1 / math.sqrt(n - 3)
        z_need = (1.959964 + 0.841621) * se
        r_min = math.tanh(z_need)
        obs_max = max(abs(r) for _, r, *_ in prereg)
        print(f"  样本量 n = {n} 对观测（每单元）")
        print(f"  在 α=0.05、检验力 80% 下，可侦测的最小相关 |r| = {r_min:.2f}")
        print(f"  预注册滞后下实际观测到的最大 |r| = {obs_max:.2f}")
        print()
        if obs_max < r_min:
            print(f"  → 本设计只能侦测到 |r| ≥ {r_min:.2f} 的强关联。")
            print("     **因此这个零结果的正确表述是「未发现强先行关联」，")
            print("     不是「不存在先行关联」。** 中等强度的关联本设计看不见。")
            print("     这是样本量的限制，不是数据质量问题——窗口只有 40 季，")
            print("     同比变换与滞后各消耗 4 季，剩下 28 对是结构性上限。")

    print()
    print("=" * 84)
    print("边界条件")
    print("=" * 84)
    print(f"  · 样本量：每单元约 {prereg[0][2] if prereg else '?'} 对观测。小样本，"
          "相关系数的置信区间很宽。")
    print("  · IDI 侧只有创新维一条序列（m8）。商业维、资本维无数据，"
          "其预注册滞后（8 季／8–12 季）无法检验。")
    print("  · 简单打乱的 p 值系统性偏小（破坏自相关）。以分块打乱为准。")
    print("  · 本检验为探索性，不支持因果推断。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--appendix", action="store_true", help="附全滞后网格 0–8 季")
    ap.add_argument("--full-window", action="store_true", help="m1 用全 40 期（9/27 口径，仅作对照）")
    a = ap.parse_args()
    main(a.appendix, a.full_window)
