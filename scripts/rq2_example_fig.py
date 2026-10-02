# -*- coding: utf-8 -*-
r"""
rq2_example_fig.py —— RQ2 图解：一项先行检验长什么样（AI · 香港 · 研究者存量 → 一年后的企业专利）

用途：向导师／读者说明 24 项检验中「一项」是怎么做的，并直观呈现「人才同比平稳、专利同比乱跳」。
只是图解，不新增任何检验；r 与 p 直接调用 scripts/rq2_leadlag.py 的函数重算，并与 10/2 输出核对。

    python scripts\rq2_example_fig.py
    → docs/fig/rq2_fig1_example_ai_hk.png
    python scripts\rq2_example_fig.py --label "图 5" --out docs/fig/report_fig5_rq2_example.png   # 报告底稿用（只改图号）

R1：只读既有序列，不产生数据值。
"""
import argparse
import importlib.util
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rq2", ROOT / "scripts" / "rq2_leadlag.py")
rq2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rq2)

ap = argparse.ArgumentParser()
ap.add_argument("--label", default="图 R2-1", help="图号")
ap.add_argument("--out", default="docs/fig/rq2_fig1_example_ai_hk.png", help="输出路径（相对仓库根）")
ARGS = ap.parse_args()

UNIT = ("ai", "hk")
LABEL = "m1_stock 研究者存量"      # 与 rq2_leadlag.TAI_SPEC 的标签一致（种子依赖它）
EXPECT_R, EXPECT_PB, EXPECT_N = 0.291, 0.195, 17   # logs/rq2_output_2026-10-02.txt


def nxt(q, k):
    """季度字符串加 k 季。"""
    y, s = int(q[:4]), int(q[5])
    i = y * 4 + s - 1 + k
    return f"{i // 4}Q{i % 4 + 1}"


# ── 数据与检验（与 rq2_leadlag.main 同一流程） ──
spec_row = next(t for t in rq2.TAI_SPEC if t[0] == LABEL)
_, path, col, qc, kind, keep = spec_row
import os
os.chdir(ROOT)                                            # rq2.load 用相对路径
tai = rq2.load(path, col, qc, keep)[UNIT]
pat = rq2.load(rq2.IDI_PATH, "patent_families")[UNIT]
tai_y = rq2.yoy(tai, kind)
pat_y = rq2.yoy(pat, "count")
x, y, n = rq2.paired(tai_y, pat_y, rq2.PREREG_LAG)
r = rq2.pearson(x, y)
random.seed(f"{LABEL}|{UNIT[0]}/{UNIT[1]}")
_ps = rq2.perm_p(x, y, r)                                 # 先简单打乱（与主脚本顺序一致，保证种子流相同）
pb = rq2.perm_p(x, y, r, block=rq2.BLOCK)

assert n == EXPECT_N and round(r, 3) == EXPECT_R and round(pb, 3) == EXPECT_PB, (n, r, pb)
print(f"核对通过：n={n}  r={r:+.3f}  p_分块={pb:.3f}（与 logs/rq2_output_2026-10-02.txt 一致）")

tq = sorted(tai_y)[:n]                                    # 参与配对的人才季度
pq = [nxt(q, rq2.PREREG_LAG) for q in tq]                 # 对应的专利季度
assert [pat_y[q] for q in pq] == y
tv = [100 * (math.exp(v) - 1) for v in x]                 # 换回百分比（同比增长率）
pv = [100 * (math.exp(v) - 1) for v in y]                 # 专利为 (x+1) 的同比，见注

# ── 图 ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import ConnectionPatch

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
# 与图 3、图 4 同义配色：研究端紫、企业端黄（dataviz 校验通过；黄色对比度 2.1:1 → 关键点直接标注数值）
C_TAI, C_PAT = "#4a3aa7", "#eda100"

fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.2, 6.0), sharey=True)
fig.subplots_adjust(left=0.08, right=0.98, top=0.80, bottom=0.16, hspace=0.58)
idx = list(range(n))

for ax, vals, c, qs, title in (
        (a1, tv, C_TAI, tq, "人才：AI 研究者存量，比去年同季度增长（%）"),
        (a2, pv, C_PAT, pq, "一年后：AI 企业国际专利族，比去年同季度增长（%）")):
    for i in idx:
        ax.axvline(i, color=GRID, lw=0.6, zorder=0)
    ax.axhline(0, color=INK2, lw=0.8, zorder=1)
    ax.plot(idx, vals, color=c, lw=2, marker="o", markersize=5, zorder=3, solid_capstyle="round")
    ax.set_xticks(idx)
    ax.set_xticklabels([q if q.endswith("Q4") else "" for q in qs], fontsize=8)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_title(title, fontsize=9.5, color=INK, loc="left")
a1.set_ylim(-115, 175)
a1.set_yticks([-50, 0, 50, 100, 150])

# 直接标注
lo, hi = min(tv), max(tv)
a1.annotate(f"一直在 {lo:+.0f}% 到 {hi:+.0f}% 之间，很平稳", xy=(2, tv[2]), xytext=(2, 110),
            fontsize=8, color=INK, ha="left", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
imin, imax = pv.index(min(pv)), pv.index(max(pv))
for i, off in ((imin, (8, -15)), (imax, (6, 10))):
    q1, q0 = pq[i], nxt(pq[i], -4)
    a2.annotate(f"{pv[i]:+.0f}%（{q0} {pat[q0]:.0f} 件 → {q1} {pat[q1]:.0f} 件）",
                xy=(i, pv[i]), xytext=off, textcoords="offset points",
                fontsize=7.5, color=INK, ha="left" if i < n - 5 else "right", va="center")

# 一对配对的示意连线（最后一对）
k = n - 1
con = ConnectionPatch(xyA=(k, tv[k]), coordsA=a1.transData, xyB=(k, pv[k]), coordsB=a2.transData,
                      color=MUTED, lw=0.9, ls=(0, (3, 2)), zorder=-1)   # 画在两图之间（轴内由竖网格线延续）
fig.add_artist(con)
for lab in a1.get_xticklabels():
    lab.set_bbox(dict(facecolor="#fcfcfb", edgecolor="none", pad=1.5))
a1.annotate(f"一对：{tq[k]} 人才 {tv[k]:+.1f}%\n配 {pq[k]} 专利 {pv[k]:+.0f}%", xy=(k, tv[k]), xytext=(-8, 26),
            textcoords="offset points", fontsize=7.5, color=INK2, ha="right")

fig.suptitle(f"{ARGS.label}　一项先行检验长什么样：AI · 香港 · 研究者存量 → 一年后的企业专利",
             x=0.01, y=0.975, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.925,
         f"上下两图同一竖线是一对（人才季度配一年后的专利季度），共 {n} 对。两图纵轴刻度相同。\n"
         f"相关系数 r = {r:+.2f}，分块置换 p = {pb:.3f}：不能排除是巧合。24 项检验里的每一项都是这样做的。",
         fontsize=8.5, color=INK2, va="top")
fig.text(0.01, 0.02,
         "注：同比 = 本季度比去年同季度。专利按 log(件数+1) 计同比以容纳零值，图中换算回百分比；相关系数按对数同比计算。\n"
         "研究者存量 = 过去 3 年发表 AI 论文、署名挂香港机构的不同作者数（2017Q4 前窗口不完整，未用）。企业专利按最早申请日计季度，剔除阿里、蚂蚁系；数据止于 2023Q4。\n"
         "数据：clean/researchers_stock_by_quarter.csv、raw/patents_families_by_quarter_company_ali_ant_grp.csv；检验：scripts/rq2_leadlag.py；本图：scripts/rq2_example_fig.py。",
         fontsize=6.8, color=MUTED, va="bottom")

out = ROOT / ARGS.out
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=200)
print(f"已写出 {out.relative_to(ROOT)}")
