# -*- coding: utf-8 -*-
r"""
company_authors_build.py —— 企业作者：在本地「企业」类机构署名的作者数（规则见 docs/企业作者口径_2026-10-04.md，跑之前写定）

为什么：人才指标只数到大学里的作者（报告 7.4、9.3 局限第 2 条）。OpenAlex 给每个机构标了类型
（education／healthcare／company／government／nonprofit／facility／archive／other），
把作者按署名机构的类型拆开，就能看到企业里发表论文的研发人员。

两步：
  ① --fetch   向 OpenAlex 取港、星两地全部机构及其类型（约 20–40 次调用；需要联网和 COLLECTOR_NAME）
              → raw/openalex_institutions_hk_sg.csv ＋ manifest ＋ requests.tsv
  ② --build   不联网。读 9/11 统一采集包的 raw/openalex_author_inst_years.csv（研究者级底稿，不入库）
              和 ①，按年计算各类机构的作者数
              → clean/company_authors_by_year.csv（+ .prov.json）
              → clean/company_authors_top_institutions.csv（只有机构名和人数，不含任何作者 ID）
              → 屏幕输出（另存 logs/company_authors_build_<日期>.txt）

    $env:COLLECTOR_NAME="賈贇"
    python scripts\company_authors_build.py --fetch
    python scripts\company_authors_build.py --build > logs\company_authors_build_2026-10-XX.txt

自检（--build 会自动做，不过就停下）：
  · 底稿的 SHA-256 必须等于 manifests/openalex_author_inst_years.csv.manifest.json（换行符不同也认），
    确认用的是 9/11 那一版——全文论文类指标都以这一版为准；
  · 用底稿算出的「全部本地作者」三年窗口数，必须与 clean/researchers_stock_by_quarter.csv 的第四季度
    unique_authors 基本一致（相对差 ≤ 1%）。两者出自同一次采集、同一批论文，对不上说明读错了文件或口径。

隐私（提案 §7）：作者 ID 只在本机内存中使用，任何输出都只有按产业×城市×年的人数，以及机构层面的人数。

R1：只做计数与比值，不产生新的数据值。
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, CLEAN, MAN = ROOT / "raw", ROOT / "clean", ROOT / "manifests"
INST_YEARS = RAW / "openalex_author_inst_years.csv"
INST_TYPES = RAW / "openalex_institutions_hk_sg.csv"
OUT = CLEAN / "company_authors_by_year.csv"
OUT_TOP = CLEAN / "company_authors_top_institutions.csv"
STOCK = CLEAN / "researchers_stock_by_quarter.csv"

YEARS = list(range(2015, 2025))
WINDOW = 3                                   # 三个日历年 = 12 个季度，与研究者存量同长
TYPES = ["education", "healthcare", "company", "government", "nonprofit", "facility", "archive", "other"]
CATS = ["all_local", "company", "company_only"] + [f"type_{t}" for t in TYPES if t != "company"] + ["type_unknown"]
ACAD_RATIO_CHECK = {"ai": "1.05", "biomed": "1.13", "fintech": "1.47"}   # 报告表 D-1 / D-3 的 2024Q4 学术比值
LOW_BASE = 30
norm = lambda ind: ind.replace("_kw", "")


def sha(p, crlf=False):
    b = p.read_bytes()
    if crlf:
        b = b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return hashlib.sha256(b).hexdigest()


# ════════════════════════ ① 取机构类型 ════════════════════════
def fetch():
    sys.path.insert(0, str(ROOT / "scripts"))
    import collect_all as ca
    ca.require_collector()
    rows = []
    counts = {}
    for cc in ("hk", "sg"):
        cursor, page = "*", 0
        while cursor:
            params = {"filter": f"country_code:{cc}", "select": "id,display_name,ror,type,country_code,works_count",
                      "per_page": 200, "cursor": cursor, "mailto": ca.MAILTO, **({"api_key": ca.KEY} if ca.KEY else {})}
            j = ca.http_get("https://api.openalex.org/institutions", params, tag=f"{cc}/p{page}")
            if page == 0:
                counts[cc] = j["meta"]["count"]
                ca.log(f"{cc}：meta.count = {counts[cc]}")
            for it in j.get("results", []):
                rows.append([cc, (it.get("id") or "").rstrip("/").rsplit("/", 1)[-1], it.get("display_name") or "",
                             it.get("ror") or "", it.get("type") or "", (it.get("country_code") or "").lower(),
                             it.get("works_count") or 0])
            cursor = (j.get("meta") or {}).get("next_cursor")
            page += 1
        n = sum(1 for r in rows if r[0] == cc)
        if n != counts[cc]:
            sys.exit(f"⛔ {cc} 翻页取回 {n} 家，meta.count 为 {counts[cc]}，对不上，停下（不写文件）")
        ca.log(f"{cc}：取回 {n} 家，与 meta.count 一致")
    types = collections.Counter((r[0], r[4]) for r in rows)
    ca.log("类型分布：" + "；".join(f"{c}/{t or '空'} {n}" for (c, t), n in sorted(types.items())))
    ca.save_rows(INST_TYPES.name, ["city", "inst_id", "display_name", "ror", "type", "country_code", "works_count"], rows,
                 "https://api.openalex.org/institutions",
                 "filter=country_code:hk / country_code:sg，全部类型，cursor 翻页；select=id,display_name,ror,type,country_code,works_count",
                 "企业作者指标（docs/企业作者口径_2026-10-04.md）的机构类型表。类型是取数当天的 OpenAlex 标注，"
                 "作者底稿是 9/11 采集的，两者时间不同，--build 会报告对不上类型的机构占比。")


# ════════════════════════ ② 计算 ════════════════════════
def build(allow_other_version=False):
    for p in (INST_YEARS, INST_TYPES, STOCK):
        if not p.exists():
            sys.exit(f"⛔ 找不到 {p.relative_to(ROOT)}" + ("（先跑 --fetch）" if p == INST_TYPES else ""))

    # 自检一：底稿版本
    man = json.loads((MAN / "openalex_author_inst_years.csv.manifest.json").read_text(encoding="utf-8"))
    h, hc = sha(INST_YEARS), sha(INST_YEARS, crlf=True)
    if man["sha256"] in (h, hc):
        print(f"自检一通过：底稿 SHA-256 与 manifest 一致（{man['collected_utc'][:10]} 采集{'，换行符不同' if man['sha256'] != h else ''}）")
    elif allow_other_version:
        print("⚠️ 底稿 SHA-256 与 manifest 不一致，因 --allow-other-version 继续（只用于测试，结果不得入库）")
    else:
        sys.exit("⛔ 底稿与 9/11 版本的 manifest 不一致。全文论文类指标以 9/11 版为准，换了版本不能比。停下。")

    # 机构类型
    itype, iname = {}, {}
    for r in csv.DictReader(open(INST_TYPES, encoding="utf-8-sig")):
        itype[(r["city"], r["inst_id"])] = r["type"] or "other"
        iname[(r["city"], r["inst_id"])] = r["display_name"]

    # 读底稿：(产业, 城市, 年) -> {作者: 本地机构集合}
    data = collections.defaultdict(lambda: collections.defaultdict(set))
    n_rows = n_local = n_unknown = 0
    for r in csv.DictReader(open(INST_YEARS, encoding="utf-8-sig")):
        n_rows += 1
        city = r["city"]
        if r["inst_cc"] != city:
            continue
        n_local += 1
        if (city, r["inst_id"]) not in itype:
            n_unknown += 1
        data[(norm(r["industry"]), city, int(r["year"]))][r["author_id"]].add(r["inst_id"])
    print(f"读入底稿 {n_rows:,} 行；其中本地机构 {n_local:,} 行；机构类型表里找不到的本地机构行 {n_unknown:,}"
          f"（{n_unknown / max(n_local, 1):.1%}{'，超过 5%，须在文档中交代' if n_unknown > 0.05 * n_local else ''}）")

    def cats_of(city, insts):
        ts = {itype.get((city, i), "unknown") for i in insts}
        out = {"all_local"}
        if "company" in ts:
            out.add("company")
            if "education" not in ts:
                out.add("company_only")
        for t in ts:
            if t == "unknown":
                out.add("type_unknown")          # 机构类型表里找不到（9/11 之后被合并或删除）
            elif t != "company":
                out.add(f"type_{t}" if t in TYPES else "type_other")
        return out

    # 每年每类的作者集合
    sets = collections.defaultdict(set)          # (ind, city, year, cat) -> {author}
    comp_inst = collections.defaultdict(lambda: collections.defaultdict(set))   # (ind, city) -> inst -> {author}（2022–2024）
    for (ind, city, year), authors in data.items():
        for a, insts in authors.items():
            for c in cats_of(city, insts):
                sets[(ind, city, year, c)].add(a)
            if 2022 <= year <= 2024:
                for i in insts:
                    if itype.get((city, i)) == "company":
                        comp_inst[(ind, city)][i].add(a)

    units = sorted({(k[0], k[1]) for k in data})
    rows = []
    for ind, city in units:
        for k, y in enumerate(YEARS):
            win = YEARS[max(0, k - WINDOW + 1):k + 1]
            for c in CATS:
                s1 = sets.get((ind, city, y, c), set())
                s3 = set().union(*[sets.get((ind, city, wy, c), set()) for wy in win])
                rows.append({"industry": ind, "city": city, "year": y, "category": c,
                             "authors_1y": len(s1), "authors_3y": len(s3), "window_full": len(win) == WINDOW})
    R = {(r["industry"], r["city"], r["year"], r["category"]): r for r in rows}

    # 自检二：与研究者存量对账
    stock = {}
    for r in csv.DictReader(open(STOCK, encoding="utf-8-sig")):
        if r["quarter"].endswith("Q4"):
            stock[(norm(r["industry"]), r["city"], int(r["quarter"][:4]))] = int(r["unique_authors"])
    worst = 0.0
    for ind, city in units:
        for y in range(2017, 2025):
            a, b = R[(ind, city, y, "all_local")]["authors_3y"], stock[(ind, city, y)]
            worst = max(worst, abs(a - b) / b)
    print(f"自检二：全部本地作者（三年窗口）与 researchers_stock 第四季度的最大相对差 {worst:.2%}")
    if worst > 0.03:
        sys.exit("⛔ 相对差超过 3%，口径或文件对不上，停下，把这段输出发给组长。")
    if worst > 0.01:
        print("⚠️ 相对差在 1%–3% 之间：继续，但须在回传说明里写明（可能是少数机构没有 ID）")
    for ind in ("ai", "biomed", "fintech"):
        r = stock[(ind, "hk", 2024)] / stock[(ind, "sg", 2024)]
        if f"{r:.2f}" != ACAD_RATIO_CHECK[ind]:
            sys.exit(f"⛔ researchers_stock 的 2024Q4 比值 {ind} = {r:.2f}，与报告 {ACAD_RATIO_CHECK[ind]} 不符，clean 文件不是定稿版，停下")
    print("自检二通过：研究者存量文件是定稿版（2024Q4 比值 AI 1.05、生医 1.13、金融科技 1.47）\n")

    # 写 clean
    CLEAN.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    top_rows = []
    for (ind, city), d in sorted(comp_inst.items()):
        tot = len(set().union(*d.values())) if d else 0
        for i, au in sorted(d.items(), key=lambda kv: -len(kv[1]))[:10]:
            top_rows.append({"industry": ind, "city": city, "period": "2022-2024", "inst_id": i,
                             "display_name": iname.get((city, i), ""), "authors": len(au),
                             "share_of_company_authors": round(len(au) / tot, 4) if tot else ""})
    with open(OUT_TOP, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["industry", "city", "period", "inst_id", "display_name", "authors", "share_of_company_authors"])
        w.writeheader(); w.writerows(top_rows)
    prov = {"inputs": {INST_YEARS.relative_to(ROOT).as_posix(): man["sha256"], INST_TYPES.relative_to(ROOT).as_posix(): sha(INST_TYPES),
                       STOCK.relative_to(ROOT).as_posix(): sha(STOCK)},
            "script": "scripts/company_authors_build.py",
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "notes": "rules: docs/企业作者口径_2026-10-04.md"}
    OUT.with_suffix(".csv.prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_TOP.with_suffix(".csv.prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8")

    # 屏幕输出与判读（规则见文档 §四）
    print("一、企业作者（三年窗口，2017 年起窗口完整）与占本地作者的比例")
    for ind in ("ai", "biomed", "fintech"):
        print(f"  {ind}")
        for y in (2017, 2020, 2024):
            line = []
            for city in ("hk", "sg"):
                c, a = R[(ind, city, y, "company")]["authors_3y"], R[(ind, city, y, "all_local")]["authors_3y"]
                co = R[(ind, city, y, "company_only")]["authors_3y"]
                line.append(f"{city} 企业 {c:,}（占 {c / a:.1%}；不兼大学 {co:,}）")
            print(f"    {y}  " + "   ".join(line))
    print("\n二、判读：企业作者港/星比值（Rc）对学术比值（Ra），2024 年三年窗口")
    for ind in ("ai", "biomed", "fintech"):
        hk, sg = R[(ind, "hk", 2024, "company")]["authors_3y"], R[(ind, "sg", 2024, "company")]["authors_3y"]
        ra = R[(ind, "hk", 2024, "all_local")]["authors_3y"] / R[(ind, "sg", 2024, "all_local")]["authors_3y"]
        hk17, sg17 = R[(ind, "hk", 2017, "company")]["authors_3y"], R[(ind, "sg", 2017, "company")]["authors_3y"]
        ra17 = R[(ind, "hk", 2017, "all_local")]["authors_3y"] / R[(ind, "sg", 2017, "all_local")]["authors_3y"]
        if min(hk, sg) < LOW_BASE:
            verdict = f"低基数（少于 {LOW_BASE} 人），只报不判"
            rc = hk / sg if sg else float("nan")
        else:
            rc = hk / sg
            verdict = ("Rc ≤ 0.8×Ra：企业作者口径下香港相对更少，支持 7.4" if rc <= 0.8 * ra else
                       "Rc ≥ 1.2×Ra：企业作者的港星比并不低于学术口径，不支持 7.4，正文照实修改" if rc >= 1.2 * ra else
                       "两种口径大致一致，无法区分")
        rc17 = f"{hk17 / sg17:.2f}" if sg17 else "—"
        print(f"  {ind:8s} Rc {rc:.2f}（2017：{rc17}）  Ra {ra:.2f}（2017：{ra17:.2f}）  → {verdict}")
    print("\n三、企业作者最多的机构（2022–2024，前 5）")
    for (ind, city) in sorted(comp_inst):
        lst = [r for r in top_rows if r["industry"] == ind and r["city"] == city][:5]
        print(f"  {ind}/{city}：" + "；".join(f"{r['display_name']} {r['authors']}（{r['share_of_company_authors']:.0%}）" for r in lst))
    print(f"\n已写出 {OUT.relative_to(ROOT).as_posix()}（{len(rows)} 行）、{OUT_TOP.relative_to(ROOT).as_posix()}（{len(top_rows)} 行）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--allow-other-version", action="store_true", help="仅测试用：底稿版本不符也继续")
    a = ap.parse_args()
    if not (a.fetch or a.build):
        ap.error("要 --fetch 或 --build")
    if a.fetch:
        fetch()
    if a.build:
        build(a.allow_other_version)
