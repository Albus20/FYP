# -*- coding: utf-8 -*-
r"""
rq2_overview_figs.py —— RQ2 全部 24 项检验的图（补图 5 只展示 AI·香港 一格的不足）

    python scripts\rq2_overview_figs.py
    → docs/fig/rq2_fig2_all_tests.png        24 项检验一览（4 个人才指标 × 6 个单元，格内 r 与分块置换 p）
    → docs/fig/rq2_fig3_scatter_m1stock.png  研究者存量 → 一年后企业专利：六个单元的散点

r、p 直接调用 scripts/rq2_leadlag.py 的函数，按主脚本的同一种子顺序重算，并与 logs/rq2_output_2026-10-02.txt 逐格核对。
只是作图，不新增检验。R1：只读既有序列，不产生数据值。
"""
import importlib.util
import math
import os
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rq2", ROOT / "scripts" / "rq2_leadlag.py")
rq2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rq2)
os.chdir(ROOT)

IND_ZH = {"ai": "人工智能", "biomed": "生物医药", "fintech": "金融科技"}
CITY_ZH = {"hk": "香港", "sg": "新加坡"}
SHORT = {"m1_stock 研究者存量": "研究者存量", "m1_flow 新增作者": "新增作者",
         "m4 前10%高引占比": "前 10% 高引占比", "m7 国际合著比例": "国际合著比例"}

# ── 重算 24 项（与主脚本同一流程、同一种子顺序） ──
idi_raw = rq2.load(rq2.IDI_PATH, "patent_families")
idi_g = {u: rq2.yoy(idi_raw[u], "count") for u in rq2.UNITS}
RES, PAIRS = {}, {}
for label, path, col, qc, kind, keep in rq2.TAI_SPEC:
    d = rq2.load(path, col, qc, keep)
    for u in rq2.UNITS:
        x, y, n = rq2.paired(rq2.yoy(d[u], kind), idi_g[u], rq2.PREREG_LAG)
        r = rq2.pearson(x, y)
        random.seed(f"{label}|{u[0]}/{u[1]}")
        rq2.perm_p(x, y, r)                       # 简单打乱（保持种子流与主脚本一致）
        pb = rq2.perm_p(x, y, r, block=rq2.BLOCK)
        RES[(label, u)] = (r, n, pb)
        PAIRS[(label, u)] = (x, y)

# ── 与 10/2 日志逐格核对 ──
log = (ROOT / "logs" / "rq2_output_2026-10-02.txt").read_text(encoding="utf-8")
checked = 0
for (label, u), (r, n, pb) in RES.items():
    pat = re.escape(label) + r"\s+" + re.escape(f"{u[0]}/{u[1]}") + r"\s+([+-]\d\.\d{3})\s+(\d+)\s+\S+\s+(\d\.\d{3})"
    m = re.search(pat, log)
    assert m, (label, u)
    assert (f"{r:+.3f}", str(n), f"{pb:.3f}") == m.groups(), ((label, u), (r, n, pb), m.groups())
    checked += 1
passed = rq2.bh_fdr([(f"{l}|{u}", v[2]) for (l, u), v in RES.items()])
print(f"核对通过：{checked} 格与 logs/rq2_output_2026-10-02.txt 一致；通过 FDR：{sum(passed.values())}/{len(passed)}")

# ── 图 ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
IND_COLOR = {"ai": "#2a78d6", "biomed": "#eb6834", "fintech": "#1baf7a"}   # 与图 1 同义
# 发散色：蓝（正）—灰（零）—红（负），中点为中性灰
CMAP = LinearSegmentedColormap.from_list("div", ["#b8302f", "#e88a89", "#f0efec", "#86b6ef", "#1c5cab"])
NORM = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
FIG = ROOT / "docs" / "fig"

# 图 6：24 项一览
labels = [t[0] for t in rq2.TAI_SPEC]
fig, ax = plt.subplots(figsize=(8.6, 4.3))
fig.subplots_adjust(left=0.15, right=0.98, top=0.72, bottom=0.17)
for i, label in enumerate(labels):
    for j, u in enumerate(rq2.UNITS):
        r, n, pb = RES[(label, u)]
        ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=CMAP(NORM(r)), edgecolor="#fcfcfb", lw=2))
        txt_c = "white" if abs(r) > 0.55 else INK
        ax.text(j + 0.5, i + 0.42, f"{r:+.2f}", ha="center", va="center", fontsize=10.5, color=txt_c, fontweight="bold")
        ax.text(j + 0.5, i + 0.74, f"p = {pb:.3f}　n = {n}", ha="center", va="center", fontsize=7, color=txt_c)
ax.set_xlim(0, 6); ax.set_ylim(4, 0)
ax.set_yticks([i + 0.5 for i in range(4)]); ax.set_yticklabels([SHORT[l] for l in labels], fontsize=9, color=INK2)
ax.set_xticks([j + 0.5 for j in range(6)])
ax.set_xticklabels([f"{CITY_ZH[u[1]]}{'†' if u == ('fintech', 'hk') else ''}" for u in rq2.UNITS], fontsize=9)
for k, ind in enumerate(("ai", "biomed", "fintech")):
    ax.text(2 * k + 1, -0.12, IND_ZH[ind], ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold")
    if k:
        ax.axvline(2 * k, color="#fcfcfb", lw=5)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
fig.suptitle("图 6　24 项先行检验一览：方向不一致，无一通过多重检验校正", x=0.01, y=0.975, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.905, "格内为人才同比与一年后企业专利同比的相关系数 r（蓝为正、红为负，颜色越深越强），下方为分块置换 p 值与配对数。\n"
         f"24 项经错误发现率校正（q = 0.05）后通过 {sum(passed.values())} 项；六个单元的方向在每个指标上都不一致。",
         fontsize=8.5, color=INK2, va="top")
fig.text(0.01, 0.02, "† 香港金融科技企业专利每季中位 2.5 件，低基数，增长率不稳定。研究者存量、新增作者只用窗口完整的季度（n = 17、16）。\n"
         "数据与检验：scripts/rq2_leadlag.py；本图：scripts/rq2_overview_figs.py。", fontsize=6.8, color=MUTED, va="bottom")
out1 = FIG / "rq2_fig2_all_tests.png"
fig.savefig(out1, dpi=200)
plt.close(fig)

# 附图：研究者存量 → 一年后企业专利，六个单元散点
label = "m1_stock 研究者存量"
fig, axes = plt.subplots(3, 2, figsize=(8.2, 9.6))
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.08, hspace=0.5, wspace=0.28)
for a, ind in enumerate(("ai", "biomed", "fintech")):
    for b, city in enumerate(("hk", "sg")):
        ax = axes[a][b]
        u = (ind, city)
        x, y = PAIRS[(label, u)]
        r, n, pb = RES[(label, u)]
        xs = [100 * (math.exp(v) - 1) for v in x]
        ys = [100 * (math.exp(v) - 1) for v in y]
        ax.axhline(0, color=INK2, lw=0.8, zorder=1)
        ax.grid(color=GRID, lw=0.6, zorder=0)
        ax.scatter(xs, ys, s=34, color=IND_COLOR[ind], edgecolor="#fcfcfb", linewidth=1.2, zorder=3)
        ax.set_title(f"{IND_ZH[ind]} · {CITY_ZH[city]}　r = {r:+.2f}，p = {pb:.3f}，n = {n}", fontsize=9, color=INK, loc="left")
        ax.set_xlabel("人才：研究者存量同比（%）", fontsize=8)
        if b == 0:
            ax.set_ylabel("一年后：企业专利同比（%）", fontsize=8)
fig.suptitle("附图 1　研究者存量 → 一年后企业专利：六个单元", x=0.01, y=0.985, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.945, "每个点是一对季度（横轴为人才同比，纵轴为一年后的专利同比）。各格坐标独立。若人才先行，点应沿左下到右上分布；六格都看不出这种形状。",
         fontsize=8, color=INK2, va="top")
fig.text(0.01, 0.01, "专利同比按 log(件数+1) 计、换算回百分比。香港金融科技为低基数单元。本图：scripts/rq2_overview_figs.py。", fontsize=6.8, color=MUTED)
out2 = FIG / "rq2_fig3_scatter_m1stock.png"
fig.savefig(out2, dpi=200)
print(f"已写出 {out1.relative_to(ROOT)}、{out2.relative_to(ROOT)}")
