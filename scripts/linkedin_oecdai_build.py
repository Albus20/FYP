# -*- coding: utf-8 -*-
r"""
linkedin_oecdai_build.py —— OECD.AI 上的 LinkedIn 数据（港星）：整理、算比值、作图

输入：raw/oecd_ai/*.zip（OECD.AI 页面「Download → Data (CSV)」原样保存，见 manifests/oecd_ai__*.manifest.json）
      clean/researchers_stock_by_quarter.csv（学术作者口径的研究者存量，只用来在图左栏对照）
输出：clean/linkedin_oecdai_hk_sg.csv（+ .prov.json）
      docs/fig/linkedin_fig1_hk_sg.png
      屏幕输出（另存 logs/linkedin_oecdai_build_2026-10-04.txt）

    python scripts\linkedin_oecdai_build.py > logs\linkedin_oecdai_build_2026-10-04.txt

═══ 定位（组长 10/4 决定，见 docs/LinkedIn数据_OECD.AI_2026-10-04.md）═══
    事后的描述性佐证，用于第七章 7.4「人才持平只对学术作者成立」。不进 RQ1 轨迹表、不进 RQ2 先行检验、不进任何合成指数。
    数据是先看过页面、再决定使用的，正文须写明。
    Campaign Manager 受众估算（docs/LinkedIn截面口径_2026-10-02.md）停用，以本数据代替。

═══ 两处源文件缺陷（不改 raw，只在读取时处理）═══
    ① 科技业文件：行业名「Technology, information and media」含逗号却未加引号，每行多一列 → 按「前 3 列＋末列」读。
    ② 净迁移文件：新加坡每年重复一行，值相同（页面表格亦如此）→ 去重；若同一城同一年出现不同值则报错停下。

R1：只做比值与去重，不产生新的数据值。
"""
import csv
import datetime
import hashlib
import io
import json
import pathlib
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "oecd_ai"
OUT = ROOT / "clean" / "linkedin_oecdai_hk_sg.csv"
FIG = ROOT / "docs" / "fig" / "linkedin_fig1_hk_sg.png"

CONC = {   # 序列名: (文件, 行业中文)
    "conc_all": ("linkedin_ai_talent_conc_country.zip", "全部会员"),
    "conc_edu": ("linkedin_ai_talent_conc_education.zip", "教育业"),
    "conc_fin": ("linkedin_ai_talent_conc_financial.zip", "金融服务业"),
    "conc_tech": ("linkedin_ai_talent_conc_tech.zip", "科技、信息与媒体业"),
}


def read_zip_csv(name):
    with zipfile.ZipFile(RAW / name) as z:
        text = z.read("data.csv").decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], rows[1:]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── 读四个集中度文件 ──
conc = {}          # (序列, 年) -> {"SGP": v, "HKG": v}
for key, (fn, _) in CONC.items():
    head, rows = read_zip_csv(fn)
    assert head[0] == "AI_talent_concentration_eng_pct" and head[1] == "Country" and head[-1] == "Year", (fn, head)
    for r in rows:
        if not r:
            continue
        if len(r) != len(head):                       # 缺陷①：多出的列只可能来自行业名里的逗号
            assert key == "conc_tech" and len(r) == len(head) + 1, (fn, r)
        v, c, y = float(r[0]), r[1], int(r[-1])
        d = conc.setdefault((key, y), {})
        assert c not in d, ("重复", fn, c, y)
        d[c] = v

# ── 净迁移（缺陷②去重） ──
head, rows = read_zip_csv("linkedin_ai_skills_migration.zip")
assert head[0].startswith("AI_skills_migration") and head[-1] == "Year", head
mig, dup = {}, 0
for r in rows:
    if not r:
        continue
    v, c, y = float(r[0]), r[1], int(r[-1])
    if (c, y) in mig:
        assert mig[(c, y)] == v, ("同城同年两个不同值，停下", c, y, mig[(c, y)], v)
        dup += 1
        continue
    mig[(c, y)] = v

# ── 招聘指数（月度） ──
head, rows = read_zip_csv("linkedin_ai_hiring_index.zip")
assert head == ["Country", "Country_label", "Month", "Relative_AI_hiring_index_pct"], head
hire = {}
for r in rows:
    if not r:
        continue
    hire[(r[0], r[2])] = float(r[3])

# ── 写 clean（长表） ──
out_rows = []
for (key, y) in sorted(conc):
    d = conc[(key, y)]
    sg, hk = d.get("SGP"), d.get("HKG")
    out_rows.append({"series": key, "industry": CONC[key][1], "period": str(y), "unit": "%",
                     "sg": sg, "hk": hk, "hk_over_sg": round(hk / sg, 4) if (hk is not None and sg) else ""})
for y in sorted({y for _, y in mig}):
    out_rows.append({"series": "net_migration", "industry": "全部会员", "period": str(y), "unit": "每万名会员",
                     "sg": mig.get(("SGP", y)), "hk": mig.get(("HKG", y)), "hk_over_sg": ""})
for m in sorted({m for _, m in hire}):
    out_rows.append({"series": "hiring_index", "industry": "全部会员", "period": f"{m[:4]}-{m[4:]}", "unit": "%（同比，3 个月移动平均）",
                     "sg": hire.get(("SGP", m)), "hk": hire.get(("HKG", m)), "hk_over_sg": ""})
OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["series", "industry", "period", "unit", "sg", "hk", "hk_over_sg"])
    w.writeheader()
    for r in out_rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
prov = {
    "inputs": {str(p.relative_to(ROOT).as_posix()): sha(p) for p in sorted(RAW.glob("*.zip"))},
    "script": "scripts/linkedin_oecdai_build.py",
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "notes": "比值＝香港 ÷ 新加坡（同一年、同一行业的集中度）。净迁移去重 %d 行。" % dup,
}
OUT.with_suffix(".csv.prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8")

# ── 屏幕输出 ──
print("OECD.AI · LinkedIn Economic Graph（港星），页面 last updated 2026-03-06")
print(f"读入：集中度 {sum(len(v) for v in conc.values())} 个值，净迁移 {len(mig)} 个（去重 {dup} 行），招聘指数 {len(hire)} 个\n")
print("一、AI 人才集中度（%）与港/星比值")
for key, (_, zh) in CONC.items():
    ys = sorted(y for k, y in conc if k == key)
    print(f"  {zh}")
    for y in ys:
        d = conc[(key, y)]
        sg, hk = d.get("SGP"), d.get("HKG")
        rat = f"{hk / sg:.2f}" if hk is not None else "—（香港样本不足）"
        print(f"    {y}  新加坡 {sg:5.2f}  香港 {'%5.2f' % hk if hk is not None else '   — '}  港/星 {rat}")
    both = [y for y in ys if conc[(key, y)].get("HKG") is not None]
    y0, y1 = both[0], both[-1]
    g = lambda c: conc[(key, y1)][c] / conc[(key, y0)][c]
    print(f"    {y0}→{y1} 增长倍数：新加坡 ×{g('SGP'):.2f}，香港 ×{g('HKG'):.2f}；比值 {conc[(key, y0)]['HKG'] / conc[(key, y0)]['SGP']:.2f} → {conc[(key, y1)]['HKG'] / conc[(key, y1)]['SGP']:.2f}")
print("\n二、AI 技能人才净迁移（每万名会员）")
for y in sorted({y for _, y in mig}):
    print(f"    {y}  新加坡 {mig[('SGP', y)]:+.2f}  香港 {mig[('HKG', y)]:+.2f}")
print("\n三、相对 AI 招聘指数（%，同比，3 个月移动平均）：按年取 12 个月均值，仅作概览")
for yr in range(2018, 2026):
    for c, zh in (("SGP", "新加坡"), ("HKG", "香港")):
        vals = [hire[(c, f"{yr}{m:02d}")] for m in range(1, 13) if (c, f"{yr}{m:02d}") in hire]
        assert len(vals) == 12, (c, yr, len(vals))
    s = sum(hire[("SGP", f"{yr}{m:02d}")] for m in range(1, 13)) / 12
    h = sum(hire[("HKG", f"{yr}{m:02d}")] for m in range(1, 13)) / 12
    print(f"    {yr}  新加坡 {s:+6.2f}  香港 {h:+6.2f}")

# ── 学术作者口径（左栏对照）：AI 研究者存量 Q4，窗口完整的年份 ──
stock = {}
with open(ROOT / "clean" / "researchers_stock_by_quarter.csv", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        if r["industry"] == "ai" and r["quarter"].endswith("Q4") and r["window_full"] == "True":
            stock[(r["city"], int(r["quarter"][:4]))] = int(r["unique_authors"])
acad = {y: stock[("hk", y)] / stock[("sg", y)] for y in sorted({y for _, y in stock}) if ("hk", y) in stock and ("sg", y) in stock}
print("\n四、对照：学术作者口径 AI 研究者存量 港/星（Q4，人数比）")
print("    " + "  ".join(f"{y}:{v:.2f}" for y, v in acad.items()))
assert f"{acad[2017]:.2f}" == "0.68" and f"{acad[2024]:.2f}" == "1.05", "与报告表 D-1 对不上，停下"

# ── 图 ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for fam in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC", "SimHei"):
    if any(fam == fe.name for fe in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#7d7b75",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7d7b75", "#e4e3dc"
AI_BLUE = "#2a78d6"

fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.9), gridspec_kw={"width_ratios": [1, 1.35]})
fig.subplots_adjust(left=0.06, right=0.84, top=0.80, bottom=0.20, wspace=0.28)
for ax in (a1, a2):
    ax.axhline(1, color=GRID, lw=1, zorder=0)
    ax.set_xlim(2015.6, 2025.4)
    ax.set_ylim(0.3, 1.15)
    ax.set_xticks(range(2016, 2026, 2))
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.text(2015.75, 1.005, "两城持平", fontsize=7, color=MUTED, va="bottom")

ys = list(acad)
a1.plot(ys, [acad[y] for y in ys], color=AI_BLUE, lw=2.2, marker="o", ms=3.5)
for y in (ys[0], ys[-1]):
    a1.annotate(f"{acad[y]:.2f}", (y, acad[y]), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, color=AI_BLUE, fontweight="bold")
a1.set_title("学术作者（OpenAlex）\n研究者存量之比", fontsize=9.5, color=INK, loc="left")
a1.set_ylabel("香港 ÷ 新加坡")

STYLE = {"conc_all": ("#0b0b0b", 2.2, "-"), "conc_edu": (AI_BLUE, 2.2, "-"),
         "conc_fin": ("#1baf7a", 1.6, "--"), "conc_tech": ("#7d7b75", 1.6, ":")}
for key, (col, lw, ls) in STYLE.items():
    pts = sorted((y, conc[(k, y)]["HKG"] / conc[(k, y)]["SGP"]) for k, y in conc if k == key and "HKG" in conc[(k, y)])
    xs, vs = zip(*pts)
    a2.plot(xs, vs, color=col, lw=lw, ls=ls, marker="o", ms=2.8)
    a2.text(xs[-1] + 0.25, vs[-1], f"{CONC[key][1]} {vs[-1]:.2f}", fontsize=8, color=col, va="center",
            fontweight="bold" if key in ("conc_all", "conc_edu") else None, clip_on=False)
a2.set_title("LinkedIn 会员（OECD.AI）\nAI 人才集中度之比，按会员所在行业", fontsize=9.5, color=INK, loc="left")

fig.suptitle("图 7　香港相对新加坡的 AI 人才：学术作者在追，业界没有", x=0.01, y=0.985, ha="left", fontsize=11, color=INK)
fig.text(0.01, 0.025,
         "左：三年滚动窗口内的不同作者数之比，2017–2024 年第四季度（人数比）。\n"
         "右：至少有两项 AI 工程技能或从事 AI 职位的会员占该行业会员的比例，两城之比（比例之比，受两城 LinkedIn 覆盖率影响）；教育业香港 2019 年起才有数据。\n"
         "两栏量的东西不同，只比较走势。数据：OECD.AI (2026), data from LinkedIn Economic Graph, last updated 2026-03-06。本图：scripts/linkedin_oecdai_build.py。",
         fontsize=6.6, color=MUTED, va="bottom")
FIG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIG, dpi=200)
print(f"\n已写出 {OUT.relative_to(ROOT).as_posix()}（{len(out_rows)} 行）、{FIG.relative_to(ROOT).as_posix()}")
