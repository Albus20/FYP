# -*- coding: utf-8 -*-
r"""
rq3_scenarios.py —— RQ3 情景展望：前提检验与可答范围

═══ 为什么要先做前提检验 ═══

提案 RQ3：「基于 RQ1 的剖面与 RQ2 的先行证据，在基线／下行／上行三种人才情景下，
          2028 年前各产业 IDI 的可能路径为何？」

§4.5 步骤④写明做法：「以三种人才情景结合**步骤③的先行系数区间**，外推各产业 IDI 至 2028」。

**但步骤③（RQ2）的结论是：24 个预注册检验无一通过 FDR，先行系数与零无法区分。**

所以 RQ3 的输入不存在——没有可用的先行系数区间去乘。
本脚本不假装能外推，而是**把「情景无法分辨」这件事量化**：

    情景差异（上行 vs 下行对 2028 年 IDI 的影响）
    ────────────────────────────────────────  ≪ 1  ⟹ 情景不可分辨
    预测区间宽度（同一时点的不确定性）

═══ 做法 ═══

① 基线路径：对 log(m8+1) 拟合线性趋势，外推至 2028Q4（末期后 20 季）
② 预测区间：残差 SD × 外推放大因子 × t 值（含参数不确定性）
③ 情景效应：由 RQ2 的回归斜率 β 推算
       IDI 增长率[t+4] = α + β × TAI 增长率[t]
   人才增长率差异 Δg 持续 5 年 ⟹ 对 2028 年 log(IDI) 的累积影响 = 5 × β × Δg
④ 情景定义（由数据本身定，不凭空设）：
       下行 = TAI 同比增长率的历史 10 分位
       基线 = 中位数
       上行 = 90 分位

R1：只读既有清洁序列，不产生任何数据值。
"""
import collections
import csv
import math
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDS = ("ai", "biomed", "fintech")
CITIES = ("hk", "sg")
UNITS = [(i, c) for i in INDS for c in CITIES]

H = 20                  # 2023Q4 → 2028Q4，20 个季度
T95 = 2.03              # t(0.975, df≈34)
YEARS = 5               # 2024–2028


def load(path, valcol, qcol="quarter"):
    d = collections.defaultdict(dict)
    p = ROOT / path
    if not p.exists():
        return None
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        v = r.get(valcol, "")
        if v in ("", None):
            continue
        ind = "fintech" if r["industry"] == "fintech_kw" else r["industry"]
        try:
            d[(ind, r["city"])][r[qcol]] = float(v)
        except ValueError:
            continue
    return d


def yoy_log(series):
    qs = sorted(series)
    return {qs[i]: math.log(series[qs[i]] + 1) - math.log(series[qs[i - 4]] + 1)
            for i in range(4, len(qs))}


def ols(y):
    """对 y 拟合 a + b*i。返回 (a, b, 残差SD, Sxx, n)。"""
    n = len(y)
    xm, ym = (n - 1) / 2, st.mean(y)
    sxx = sum((i - xm) ** 2 for i in range(n))
    b = sum((i - xm) * (v - ym) for i, v in enumerate(y)) / sxx
    a = ym - b * xm
    resid = [v - (a + b * i) for i, v in enumerate(y)]
    sd = math.sqrt(sum(r * r for r in resid) / (n - 2))
    return a, b, sd, sxx, n


def slope_ci(x, y):
    """回归斜率 β 及其 95% 置信区间。返回 (β, lo, hi)。

    关键：RQ2 已证 β 与零无法区分。把 CI 传导到情景效应，
    才能看出「情景差异」这个点估计有多不可靠。
    """
    n = len(x)
    if n < 4:
        return None
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    resid = [c - (a0 + b * a) for a, c in zip(x, y)]
    se_res = math.sqrt(sum(r * r for r in resid) / (n - 2))
    se_b = se_res / math.sqrt(sxx)
    t = 2.056  # t(0.975, df=26)
    return b, b - t * se_b, b + t * se_b


def paired(tg, ig, lag=4):
    qs = sorted(set(tg) | set(ig))
    idx = {q: i for i, q in enumerate(qs)}
    x, y = [], []
    for q in sorted(tg):
        j = idx[q] + lag
        if j < len(qs) and qs[j] in ig:
            x.append(tg[q])
            y.append(ig[qs[j]])
    return x, y


def main():
    print("=" * 84)
    print("RQ3 情景展望 · 前提检验")
    print("=" * 84)

    idi = load("raw/patents_families_by_quarter_company_ali_ant_grp.csv", "patent_families")
    tai = load("clean/researchers_stock_by_quarter.csv", "unique_authors")
    if idi is None or tai is None:
        print("⛔ 缺数据文件")
        return

    print("\n提案 §4.5 步骤④：「以三种人才情景结合**步骤③的先行系数区间**外推 IDI」。")
    print("步骤③（RQ2）实测：24 个预注册检验无一通过 FDR 校正，先行系数与零无法区分。")
    print("\n→ RQ3 的输入不存在。以下不外推，而是量化「情景能否被分辨」。\n")

    print("─" * 84)
    print("情景效应 vs 预测不确定性")
    print("─" * 84)
    print("情景差异 = 上行与下行人才情景对 2028 年 log(IDI) 的累积影响之差")
    print("预测区间 = 同一时点基线路径的 95% 预测区间半宽\n")
    print(f"{'单元':13s}{'β':>9}{'情景差异':>11}{'预测区间±':>11}{'比值':>9}   判读")

    rows = []
    for u in UNITS:
        if u not in idi or u not in tai:
            continue
        qs = sorted(idi[u])
        y = [math.log(idi[u][q] + 1) for q in qs]
        a, b, sd, sxx, n = ols(y)

        # 外推至 h=H 的预测区间半宽（含参数不确定性）
        xm = (n - 1) / 2
        i_fut = (n - 1) + H
        se_pred = sd * math.sqrt(1 + 1 / n + (i_fut - xm) ** 2 / sxx)
        pi = T95 * se_pred

        # 情景效应
        tg, ig = yoy_log(tai[u]), yoy_log(idi[u])
        x, yy = paired(tg, ig)
        res = slope_ci(x, yy)
        if res is None:
            print(f"{u[0]+'/'+u[1]:13s}{'—':>9}  无法估计")
            continue
        beta, blo, bhi = res
        g = sorted(tg.values())
        spread = g[int(0.90 * len(g))] - g[int(0.10 * len(g))]
        eff = YEARS * beta * spread
        eff_lo, eff_hi = YEARS * blo * spread, YEARS * bhi * spread
        ratio = abs(eff) / pi
        signed = (blo > 0) or (bhi < 0)      # β 的 CI 是否排除零
        rows.append((u, beta, blo, bhi, eff, eff_lo, eff_hi, pi, ratio, signed))
        mark = "β的CI含零 → 方向都定不了" if not signed else "β的CI排除零"
        print(f"{u[0]+'/'+u[1]:13s}{beta:>+9.3f}{eff:>+11.3f}{pi:>11.3f}"
              f"{ratio:>9.2f}   {mark}")

    print()
    print("─" * 84)
    print("判读")
    print("─" * 84)
    if rows:
        mr = st.median([r[8] for r in rows])
        n_signed = sum(1 for r in rows if r[9])
        print(f"  比值中位数 = {mr:.2f}（情景差异约为预测区间半宽的 {mr*100:.0f}%）")
        print(f"  β 的 95% CI 排除零的单元数：**{n_signed} / {len(rows)}**")
        print()
        print("  把 β 的不确定性传导到情景效应：")
        print(f"\n{'单元':13s}{'β 的 95% CI':>22}{'情景效应的 95% CI':>26}")
        for u, b, blo, bhi, eff, elo, ehi, pi, ratio, sg in rows:
            print(f"{u[0]+'/'+u[1]:13s}"
                  f"{'['+format(blo,'+.3f')+', '+format(bhi,'+.3f')+']':>22}"
                  f"{'['+format(elo,'+.3f')+', '+format(ehi,'+.3f')+']':>26}")
        print()
        if n_signed == 0:
            print("  → **六个单元的 β 置信区间全部包含零。**")
            print("     这意味着：人才情景对 2028 年 IDI 的影响，连**正负方向都无法确定**。")
            print("     上表「情景差异」那一列的点估计看着有数，但它的区间横跨零，")
            print("     用它画三条情景路径，是把噪声画成了结论。")
            print()
            print("  **因此 RQ3 不能按原设计交付「三条情景路径」。**")
            print("  硬画出来会给读者一个不存在的精确感——那是在用图形掩盖不确定性。")

    print()
    print("─" * 84)
    print("RQ3 改为可答的形式")
    print("─" * 84)
    print("""
  原问法：「三种人才情景下 2028 年各产业 IDI 的可能路径为何？」
      → 不可答。缺先行系数，且情景效应远小于预测区间。

  可答的替代问法：

  **① 本设计能不能支持情景外推？** —— 可答，答案是否定的，且可量化（上表）。
      这本身是方法论发现：在 40 季窗口、单指标 IDI 的条件下，
      人才情景外推不具可行性。

  **② 基线路径本身是什么？** —— 可答，但须同时给出预测区间。
      六个单元的对数趋势斜率：
""")
    for u in UNITS:
        if u not in idi:
            continue
        qs = sorted(idi[u])
        y = [math.log(idi[u][q] + 1) for q in qs]
        a, b, sd, sxx, n = ols(y)
        ann = (math.exp(b * 4) - 1) * 100
        print(f"        {u[0]+'/'+u[1]:13s} 年化 {ann:>+7.1f}%   "
              f"（残差 SD {sd:.3f}，外推 20 季后区间半宽 ±{T95*sd*math.sqrt(1+1/n+((n-1+H)-(n-1)/2)**2/sxx):.2f} 对数单位）")

    print("""
  **③ 需要多长窗口才能支持情景外推？** —— 可答，是对后续研究的具体建议。

  ⚠️ 以上不作因果解读。趋势外推只是把历史斜率延长，不含任何机制假设。
""")


if __name__ == "__main__":
    main()
