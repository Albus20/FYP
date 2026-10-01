# -*- coding: utf-8 -*-
r"""
oa_intl_cn_probe.py  v2 —— m7 国际合著：扣掉「只和中国内地合作」的论文后还剩多少（J7b）

═══ 为什么要查 ═══

m7 国际合著比例 = 作者机构来自 ≥2 个国家／地区的论文占比。
OpenAlex 按机构 country_code 判国家：香港 = hk，内地 = cn。
所以「港大 + 北大」合写的论文，现在被算作国际合著。
香港生医有 84% 的论文算国际合著（新加坡 63%），这是 RQ1 目前唯一对刻度稳健的发现。
如果其中大部分只是港—内地合作，结论就要改写。

═══ v1 为什么作废（2026-09-30 冒烟失败）═══

v1 用四次 meta.count（countries_distinct_count 过滤）取数。冒烟测试 biomed/hk/2015Q1：
    works 1,440，国际合著 69.8%；9/11 统一采集包同一格是 works 1,692、76.9%
同一个 filter，J3（9/28）数出来是 1,726，J7（9/30）是 1,440——OpenAlex 两天里改了数据。
所以 v1 的冒烟对照同时混着两件事：①OpenAlex 数据版本变了；②countries_distinct_count
与我们「按机构 country_code 自己数」的口径可能不同。拆不开，所以停下是对的。

═══ v2 怎么做 ═══

与 collect_openalex_master.py 完全同一套做法：cursor 逐篇翻页，select 只要 authorships，
每篇论文把 authorships[].institutions[].country_code 去重成一个集合，本地判定：

    works          该单元该季度论文数
    intl_works     集合里 ≥2 个国家／地区                        （＝现行 m7 口径）
    cn_any_works   集合里有 cn
    cn_only_works  集合恰好是 {本城, cn}                          （只和内地合作）
    intl_works_ac  另按 authorships[].countries 数 ≥2（OpenAlex 自带字段，只作对照）

四个数出自同一次翻页、同一个数据版本，比例内部一致；A、B 两个口径都从这里算，
不再和 9/11 的数混用。9/11 版本只在屏幕上对照，作为「OpenAlex 数据漂移」的记录。

产业过滤、国家范围与 collect_openalex_master.pull_unit 逐字相同：
    AI／生医：primary_topic 学科 ID（boundary_rules_v1.yaml）
    金融科技：search 关键词前 6 个（fintech_kw 口径）
    国家范围：authorships.institutions.country_code:{hk|sg}，2015-01-01 至 2024-12-31

═══ 用法 ═══

    在 data_repo 文件夹里（在 scripts 文件夹里就去掉 "scripts\"；用 PyCharm 就在运行配置的
    Parameters 填 --full、Environment variables 填 COLLECTOR_NAME=你的真名）：

    # 第一步：冒烟测试（biomed/hk/2015Q1 一格，约 10 次请求、半分钟）
    python scripts\oa_intl_cn_probe.py

    # 看到 SMOKE TEST PASSED 后跑全量（6 个单元逐篇翻页，约 1,000 次请求，40 分钟上下）
    $env:COLLECTOR_NAME = "你的真名"
    python scripts\oa_intl_cn_probe.py --full
    #   中途断了：原样再跑一遍，已完成的单元会跳过（12 小时内的断点才认，
    #   超过 12 小时 OpenAlex 可能又换了版本，脚本会要求整批重来）

    # 只检查路径与 filter 拼装、不发请求
    python scripts\oa_intl_cn_probe.py --dry

产物：raw/openalex_intl_cn_by_quarter.csv ＋ manifests/ 下的 manifest 与请求日志
      （只存计数，不存逐篇明细，不涉及 gitignore 的研究者级文件）

环境变量：COLLECTOR_NAME、OPENALEX_KEY、OPENALEX_MAILTO 没设时，脚本会从 data_repo\.keys.env 读
（与 run_phase2.ps1 同一个文件；只读变量名对应的值，不打印）。

已知限制：OpenAlex 列表接口对作者极多的论文只返回前 100 位作者，国家集合可能不全；
9/11 统一采集包（现行 m7）也是同样取法，两者一致。

R1：只记 API 返回内容数出来的计数，不产生任何数据值。
R2：全量模式必须设 COLLECTOR_NAME。
"""
import argparse
import csv
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _load_keys_env():
    """环境里没有的变量，从 data_repo/.keys.env 补上（必须在 import collect_all 之前，它在 import 时读环境变量）。"""
    f = Path(__file__).resolve().parents[1] / ".keys.env"
    got = []
    if not f.exists():
        return got
    for line in f.read_text(encoding="utf-8-sig").splitlines():
        t = line.strip()
        if not t or t.startswith("#") or "=" not in t:
            continue
        k, v = t.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ("COLLECTOR_NAME", "OPENALEX_KEY", "OPENALEX_MAILTO") and v and not os.environ.get(k):
            os.environ[k] = v
            got.append(k)
    return got


_KEYS_LOADED = _load_keys_env()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_all as ca   # noqa: E402

API = "https://api.openalex.org/works"
CITIES = ("hk", "sg")
OUT_NAME = "openalex_intl_cn_by_quarter.csv"
HEADER = ["industry", "city", "quarter", "works", "intl_works", "cn_any_works", "cn_only_works",
          "intl_works_ac"]
COUNT_KEYS = HEADER[3:]
CKPT = ca.RAW / "_ckpt_j7b"
CKPT_MAX_AGE_H = 12


def base_filter(ind, spec, cc, d0, d1):
    """返回 (产业标签, filter, 额外参数)，与 collect_openalex_master.pull_unit 一致。"""
    ifilter = ca.industry_filter(spec)
    if ifilter:
        extra, label = {}, ind
    else:
        extra, label = {"search": " OR ".join(f'"{k}"' for k in spec["keywords"][:6])}, ind + "_kw"
    flt = ",".join(p for p in (ifilter,
                               f"authorships.institutions.country_code:{cc}",
                               f"from_publication_date:{d0}",
                               f"to_publication_date:{d1}") if p)
    return label, flt, extra


def quarter_of(d):
    if not d or len(d) < 7:
        return None
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def classify(w, cc):
    """一篇论文 → (inst 国家集合, authorships.countries 集合)。与 master 同一数法。"""
    inst, ac = set(), set()
    for a in w.get("authorships") or []:
        for it in a.get("institutions") or []:
            c = (it.get("country_code") or "").lower()
            if c:
                inst.add(c)
        for c in a.get("countries") or []:
            if c:
                ac.add(c.lower())
    return inst, ac


def get_page(params, tag):
    """collect_all.http_get 只重试 429；这里再兜住 5xx 与网络中断（翻页中途断一次不至于整个单元白跑）。"""
    import requests
    for attempt in range(4):
        try:
            return ca.http_get(API, params, tag=tag)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError, ValueError) as e:
            err = e.__class__.__name__      # ValueError：返回内容不是完整 JSON（传到一半断了）
        except requests.exceptions.HTTPError as e:
            code = getattr(e.response, "status_code", None)
            if code is None or code < 500:
                raise
            err = f"HTTP {code}"
        if attempt < 3:
            ca.log(f"  {tag}：{err}，等 {30 * (attempt + 1)} 秒重试")
            time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"{tag} 重试 3 次仍失败（{err}）。原样再跑一次即可，已完成的单元会跳过。")


def enumerate_unit(label, flt, extra, cc, tag):
    """cursor 逐页翻完一个 filter，返回 ({季度: {计数}}, 翻到的篇数, meta.count, 页数, 首页诊断)。"""
    counts, n, page, cursor, meta_count, diag = {}, 0, 0, "*", None, None
    while cursor:
        params = {"filter": flt, "select": "id,publication_date,authorships",
                  "per_page": 200, "cursor": cursor, "mailto": ca.MAILTO, **extra,
                  **({"api_key": ca.KEY} if ca.KEY else {})}
        j = get_page(params, f"{tag}/p{page}")
        if j is None:                                   # --dry
            return None, 0, None, 0, None
        if page == 0:
            meta_count = (j.get("meta") or {}).get("count")
            diag = first_page_diag(j)
        for w in j.get("results", []):
            q = quarter_of(w.get("publication_date"))
            if not q:
                continue
            n += 1
            inst, ac = classify(w, cc)
            c = counts.setdefault(q, dict.fromkeys(COUNT_KEYS, 0))
            c["works"] += 1
            c["intl_works"] += len(inst) >= 2
            c["cn_any_works"] += "cn" in inst
            c["cn_only_works"] += inst == {cc, "cn"}
            c["intl_works_ac"] += len(ac) >= 2
        cursor = (j.get("meta") or {}).get("next_cursor")
        page += 1
        if page % 25 == 0:
            ca.log(f"  {tag}  第 {page} 页  已数 {n:,} 篇")
    return counts, n, meta_count, page, diag


def first_page_diag(j):
    n_au = n_inst = n_cc = 0
    for w in j.get("results", []):
        for a in w.get("authorships") or []:
            n_au += 1
            insts = a.get("institutions") or []
            if insts:
                n_inst += 1
            if any(it.get("country_code") for it in insts):
                n_cc += 1
    if n_au and n_inst == 0:
        sys.exit("⛔ 首页所有署名的 institutions 都是空的——select 把嵌套字段裁掉了，数出来全是 0。"
                 "停下，把这段发回给组长。")
    return f"首页署名位次 {n_au}，带机构 {n_inst}（{n_inst / max(n_au, 1):.0%}），机构带国家码 {n_cc}"


def hard_check(tag, c):
    bad = []
    if not c["intl_works"] <= c["works"]:
        bad.append("intl > works")
    if not c["cn_only_works"] <= c["cn_any_works"] <= c["works"]:
        bad.append("cn_only ≤ cn_any ≤ works 不成立")
    if not c["cn_only_works"] <= c["intl_works"]:
        bad.append("cn_only > intl")
    if bad:
        raise RuntimeError(f"⛔ {tag} 自检失败：{'；'.join(bad)}。拒绝写盘，把这段发回给组长。")


def meta_count(flt, extra, tag):
    params = {"filter": flt, "per_page": 1, "mailto": ca.MAILTO, **extra,
              **({"api_key": ca.KEY} if ca.KEY else {})}
    j = get_page(params, tag)
    n = None if j is None else (j.get("meta") or {}).get("count")
    return None if n is None else int(n)


def ref_m7(ind, cc, q):
    try:
        with open(ca.ROOT / "clean" / "intl_collab_by_quarter.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["industry"] == ind and r["city"] == cc and r["quarter"] == q:
                    return int(r["works"]), float(r["intl_share"])
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return None


def env_status():
    if _KEYS_LOADED:
        print(f"从 .keys.env 载入：{', '.join(_KEYS_LOADED)}")
    print(f"OpenAlex API key：{'已设置' if ca.KEY else '未设置'}　｜　采集人：{os.environ.get('COLLECTOR_NAME') or '未设置'}")
    if not ca.KEY:
        print("  （没有 key 也能跑，但全量约 1,000 次请求，可能被限流；脚本遇到限流会自动等待重试。）")


# ── 冒烟 ─────────────────────────────────────────────────
def smoke(ready):
    print("=" * 72)
    print("冒烟测试 v2：biomed/hk/2015Q1 逐篇翻页，按机构国家码本地数")
    print("=" * 72)
    env_status()
    q, d0, d1 = "2015Q1", "2015-01-01", "2015-03-31"
    label, flt, extra = base_filter("biomed", ready["biomed"], "hk", d0, d1)
    print(f"filter = {flt}")
    t0 = time.time()
    counts, n, mc, pages, diag = enumerate_unit(label, flt, extra, "hk", f"{label}/hk/{q}")
    if counts is None:
        print("\n✅ 空跑通过：路径、import、口径规则、filter 拼装都正常。去掉 --dry 才会真的发请求。")
        return True
    cdc = meta_count(flt + ",countries_distinct_count:>1", extra, f"{label}/hk/{q}/cdc")
    c = counts.get(q, dict.fromkeys(COUNT_KEYS, 0))
    ok = True
    print(f"\n{diag}")
    print(f"逐篇翻页 {n:,} 篇（{pages} 页，{time.time() - t0:.0f} 秒）；同一时刻 meta.count = {mc if mc is None else format(mc, ',')}")
    if mc is None or abs(n - mc) > max(2, 0.005 * mc):
        print("! 翻到的篇数与 meta.count 对不上（>0.5%）：cursor 翻页有丢失")
        ok = False
    w = max(c["works"], 1)
    print(f"\nworks          = {c['works']:,}")
    print(f"intl_works     = {c['intl_works']:,}   （{c['intl_works'] / w:.1%}）  ← 按机构国家码，现行 m7 口径")
    print(f"cn_any_works   = {c['cn_any_works']:,}   （占国际合著 {c['cn_any_works'] / max(c['intl_works'], 1):.1%}）")
    print(f"cn_only_works  = {c['cn_only_works']:,}   （占国际合著 {c['cn_only_works'] / max(c['intl_works'], 1):.1%}）")
    print(f"intl_works_ac  = {c['intl_works_ac']:,}   （{c['intl_works_ac'] / w:.1%}）  ← 按 authorships.countries，只作对照")
    if cdc is not None and mc:
        print(f"countries_distinct_count:>1 的 meta.count = {cdc:,}（{cdc / mc:.1%}）  ← v1 用的口径，只作对照")
    try:
        hard_check("biomed/hk/2015Q1", c)
    except RuntimeError as e:
        print(f"! {e}")
        ok = False
    gap = (c["intl_works"] - (cdc or 0)) / w * 100
    if cdc is not None:
        print(f"\n同一版本内，机构国家码口径 − countries_distinct_count 口径 = {gap:+.1f} 个百分点"
              "（这就是 v1 与 m7 的口径差；v2 不再依赖它）")
    ref = ref_m7("biomed", "hk", q)
    if ref:
        rw, rs = ref
        print(f"9/11 统一采集包同一格：works {rw:,}、m7 {rs:.1%}；本次 works {c['works']:,}、m7 {c['intl_works'] / w:.1%}"
              f"（works 差 {(c['works'] - rw) / rw:+.1%}——这是 OpenAlex 数据版本漂移，只记录，不判失败）")
    print()
    if ok:
        print("SMOKE TEST PASSED —— 可以跑全量了（约 40 分钟，可以挂着不管）：")
        print('    $env:COLLECTOR_NAME = "你的真名"')
        print("    python scripts\\oa_intl_cn_probe.py --full")
    else:
        print("SMOKE TEST FAILED —— 不要跑全量。把上面整段发回给组长。")
    return ok


# ── 全量 ─────────────────────────────────────────────────
def ckpt_path(label, cc):
    return CKPT / f"{label}_{cc}.json"


def load_ckpt(label, cc):
    p = ckpt_path(label, cc)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(d["done_utc"])).total_seconds() / 3600
    if age_h > CKPT_MAX_AGE_H:
        sys.exit(f"⛔ 断点 {p.name} 是 {age_h:.0f} 小时前的，OpenAlex 可能已换版本，不能与新数据混用。\n"
                 f"   删掉文件夹 raw\\_ckpt_j7b 后整批重跑。")
    return d


def full(ready):
    ca.require_collector()
    env_status()
    inds = [i for i in ("ai", "biomed", "fintech") if i in ready]
    if len(inds) < 3:
        sys.exit(f"⛔ 规则文件里就绪的产业只有 {inds}，与统一采集包不一致，停下")
    qs = [q for q, _, _ in ca.quarters()]
    CKPT.mkdir(parents=True, exist_ok=True)
    first_urls, summary, soft = [], [], []
    for ind in inds:
        for cc in CITIES:
            label, flt, extra = base_filter(ind, ready[ind], cc, "2015-01-01", "2024-12-31")
            tag = f"{label}/{cc}"
            done = load_ckpt(label, cc)
            if done:
                ca.log(f"{tag}：用 {done['done_utc']} 的断点，跳过")
                first_urls.append((f"{tag}/p0", done["first_url"]))
                summary.append((tag, done["n"], done["meta_count"], done["pages"], "断点"))
                continue
            ca.log(f"{tag}：开始逐篇翻页")
            t0 = time.time()
            before = len(ca.REQUEST_LOG)
            counts, n, mc, pages, diag = enumerate_unit(label, flt, extra, cc, tag)
            ca.log(f"  {diag}")
            if mc is None or abs(n - mc) > max(2, 0.005 * mc):
                sys.exit(f"⛔ {tag} 翻到 {n:,} 篇，meta.count {mc}，差超过 0.5%：cursor 翻页有丢失。停下发回组长。")
            for q in qs:
                c = counts.get(q, dict.fromkeys(COUNT_KEYS, 0))
                hard_check(f"{tag}/{q}", c)
                if c["works"] == 0:
                    soft.append(f"{tag}/{q} works=0")
            first_url = ca.REQUEST_LOG[before][1]
            ckpt_path(label, cc).write_text(json.dumps({
                "label": label, "city": cc, "n": n, "meta_count": mc, "pages": pages,
                "first_url": first_url, "done_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "counts": counts}, ensure_ascii=False), encoding="utf-8")
            first_urls.append((f"{tag}/p0", first_url))
            summary.append((tag, n, mc, pages, f"{time.time() - t0:.0f}s"))
            ca.log(f"  {tag} 完成：{n:,} 篇 / meta.count {mc:,} / {pages} 页")

    rows = []
    for ind in inds:
        for cc in CITIES:
            label, _, _ = base_filter(ind, ready[ind], cc, "2015-01-01", "2024-12-31")
            d = json.loads(ckpt_path(label, cc).read_text(encoding="utf-8"))
            for q in qs:
                c = d["counts"].get(q, dict.fromkeys(COUNT_KEYS, 0))
                rows.append([label, cc, q, *(c[k] for k in COUNT_KEYS)])

    # 请求日志只留每个单元的首页（cursor=*）——后续页的 cursor 令牌会过期，点开也复现不了；
    # 与 openalex_works_master.csv.requests.tsv 的做法一致
    ca.REQUEST_LOG = first_urls
    ca.REQUEST_LOG_NOTE = ("每个单元 cursor 翻页的首页请求（cursor=*）；后续页的 cursor 令牌会过期，不记。"
                           "已剔除 api_key 与 mailto。复核方法：点开 URL，meta.count 应≈本表该单元 40 个季度 works 之和"
                           "（OpenAlex 数据会变，差几个百分点属正常，记录差值即可）。")
    note = ("m7 国际合著的港—内地拆分（J7b，v2）。与 collect_openalex_master.py 同一数法："
            "cursor 逐篇翻页，authorships[].institutions[].country_code 去重成集合；"
            "intl_works = 集合 ≥2；cn_any_works = 集合含 cn；cn_only_works = 集合恰为 {本城, cn}；"
            "intl_works_ac = 按 authorships[].countries 数 ≥2（OpenAlex 自带字段，仅作对照）。"
            "五列出自同一次翻页、同一 OpenAlex 数据版本。v1（meta.count + countries_distinct_count）"
            "2026-09-30 冒烟失败作废：同一 filter 的 works 在 9/28 与 9/30 相差 17%，OpenAlex 数据版本漂移。"
            "逐单元 翻页篇数/meta.count：" + "；".join(f"{t} {n}/{m}" for t, n, m, _, _ in summary))
    if soft:
        note += f"｜提示 {len(soft)} 条：" + "；".join(soft[:20])
    ca.save_rows(OUT_NAME, HEADER, rows, API,
                 "6 单元 × 2015-01-01..2024-12-31 cursor 翻页（per_page=200，select=id,publication_date,authorships），"
                 "按 publication_date 归季，本地数五个计数",
                 note)
    shutil.rmtree(CKPT, ignore_errors=True)
    print("\n单元　　　　　　　翻页篇数　meta.count　页数　耗时")
    for t, n, m, p, s in summary:
        print(f"  {t:<16} {n:>8,} {m:>10,} {p:>5}  {s}")
    print(f"\n完成 {len(rows)} 格。把 raw/{OUT_NAME}、manifests/ 下同名的 manifest 与 requests.tsv、"
          "以及这段运行输出一起发给组长。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="跑全部 3 产业 × 2 城（逐篇翻页）。不加只做冒烟测试。")
    ap.add_argument("--dry", action="store_true", help="空跑：不发请求，只检查路径与 filter 拼装。")
    a = ap.parse_args()
    if a.dry:
        ca.DRY = True      # 必须改模块属性（2026-09-11 在 collect_authors.py 上踩过坑）
    ready, blocked = ca.load_rules()
    if a.full and not a.dry:
        full(ready)
    else:
        sys.exit(0 if smoke(ready) else 1)
