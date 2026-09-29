# -*- coding: utf-8 -*-
r"""
oa_intl_cn_probe.py —— m7 国际合著：扣掉「只和中国内地合作」的论文后还剩多少（J7）

═══ 为什么要查 ═══

m7 国际合著比例 = 作者机构来自 ≥2 个国家／地区的论文占比。
OpenAlex 按机构 country_code 判国家：香港 = hk，内地 = cn。
所以「港大 + 北大」合写的论文，现在被算作国际合著。

香港生医有 84% 的论文算国际合著（新加坡 63%），这是 RQ1 目前唯一对刻度稳健的发现。
如果其中大部分只是港—内地合作，结论就要改写。本脚本逐季取四个数：

    works          该单元论文总数
    intl_works     国际合著数            countries_distinct_count:>1
    cn_any_works   有中国内地机构参与的   ＋ authorships.institutions.country_code:cn
    cn_only_works  只有「本城 + 内地」两方  ＋ cn ＋ countries_distinct_count:2

之后由 scripts/m7_cn_sensitivity.py 按「两城同一规则」重算 m7：
    口径 A（现行）  intl_works / works
    口径 B          (intl_works − cn_only_works) / works    —— 只和内地合作的不算国际

新加坡也按同一规则算（B 口径下新加坡—内地两方合著同样扣掉），保证两城可比。

═══ 口径与统一采集包一致 ═══

产业过滤、国家范围、季度切分与 collect_openalex_master.py 逐字相同：
    AI／生医：primary_topic 学科 ID（boundary_rules_v1.yaml）
    金融科技：search 关键词前 6 个（fintech_kw 口径）
    国家范围：authorships.institutions.country_code:{hk|sg}
同一字段重复写两次（hk 与 cn）在 OpenAlex 里是「同时满足」。

═══ 用法 ═══

    # 第一步：冒烟测试（1 格 4 次请求，十几秒）
    python scripts\oa_intl_cn_probe.py

    # 看到 SMOKE TEST PASSED 后跑全量（240 格 × 4 = 960 次请求，约 20–25 分钟）
    $env:COLLECTOR_NAME = "你的真名"
    python scripts\oa_intl_cn_probe.py --full

    # 只检查路径与 filter 拼装、不发请求
    python scripts\oa_intl_cn_probe.py --dry

产物：raw/openalex_intl_cn_by_quarter.csv ＋ manifests/ 下的 manifest 与请求日志。

R1：只记 API 返回的计数，不产生任何数据值。
R2：全量模式必须设 COLLECTOR_NAME。
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_all as ca   # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "https://api.openalex.org/works"
CITIES = ("hk", "sg")
OUT_NAME = "openalex_intl_cn_by_quarter.csv"
HEADER = ["industry", "city", "quarter", "works", "intl_works", "cn_any_works", "cn_only_works"]


def unit_params(ind, spec, cc, d0, d1):
    """返回 (产业标签, 基础 filter, 额外参数)，与 collect_openalex_master.pull_unit 一致。"""
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


def count(flt, extra, tag):
    params = {"filter": flt, "per_page": 1, "mailto": ca.MAILTO, **extra,
              **({"api_key": ca.KEY} if ca.KEY else {})}
    j = ca.http_get(API, params, tag=tag)
    if j is None:                       # --dry
        return None
    n = (j.get("meta") or {}).get("count")
    if n is None:
        raise RuntimeError(f"{tag} 没有 meta.count，停下")
    return int(n)


def fetch_cell(ind, spec, cc, q, d0, d1):
    label, flt, extra = unit_params(ind, spec, cc, d0, d1)
    tag = f"{label}/{cc}/{q}"
    works = count(flt, extra, tag + "/works")
    intl = count(flt + ",countries_distinct_count:>1", extra, tag + "/intl")
    cn_any = count(flt + ",authorships.institutions.country_code:cn", extra, tag + "/cn_any")
    cn_only = count(flt + ",authorships.institutions.country_code:cn,countries_distinct_count:2",
                    extra, tag + "/cn_only")
    return label, flt, extra, (works, intl, cn_any, cn_only)


def check(tag, vals, hard=True):
    """逐格自检。硬约束违反即停；软约束只提示。"""
    works, intl, cn_any, cn_only = vals
    problems = []
    if not (0 <= intl <= works):
        problems.append(f"intl {intl} 不在 [0, works={works}] 内")
    if not (0 <= cn_only <= cn_any):
        problems.append(f"cn_only {cn_only} > cn_any {cn_any}")
    if hard and problems:
        raise RuntimeError(f"⛔ {tag} 自检失败：{'；'.join(problems)}。拒绝写盘，把这段发回给组长。")
    soft = []
    if cn_any > intl:
        soft.append(f"cn_any {cn_any} > intl {intl}（OpenAlex 两个字段口径略有出入，记录在案即可）")
    if cn_only > intl:
        soft.append(f"cn_only {cn_only} > intl {intl}")
    return problems, soft


def smoke(ready):
    print("=" * 72)
    print("冒烟测试：biomed/hk/2015Q1 取四个数，检查大小关系与现有 m7 是否对得上")
    print("=" * 72)
    q, d0, d1 = "2015Q1", "2015-01-01", "2015-03-31"
    label, flt, extra, vals = fetch_cell("biomed", ready["biomed"], "hk", q, d0, d1)
    print(f"filter = {flt}")
    if vals[0] is None:
        print("\n✅ 空跑通过：路径、import、口径规则、filter 拼装都正常。去掉 --dry 才会真的发请求。")
        return True
    works, intl, cn_any, cn_only = vals
    print(f"\nworks          = {works:,}")
    print(f"intl_works     = {intl:,}   （{intl / works:.1%}）")
    print(f"cn_any_works   = {cn_any:,}   （占国际合著 {cn_any / max(intl, 1):.1%}）")
    print(f"cn_only_works  = {cn_only:,}   （占国际合著 {cn_only / max(intl, 1):.1%}）")
    ok = True
    problems, soft = check("biomed/hk/2015Q1", vals, hard=False)
    for p in problems:
        print(f"! {p}")
        ok = False
    for s in soft:
        print(f"· {s}")
    # 与 9/11 统一采集包的 m7 对照（J3 已证实 OpenAlex 会回溯改数，差几个百分点属正常）
    ref = None
    try:
        with open(ca.ROOT / "clean" / "intl_collab_by_quarter.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["industry"] == "biomed" and r["city"] == "hk" and r["quarter"] == q:
                    ref = float(r["intl_share"])
    except FileNotFoundError:
        pass
    if ref is not None:
        diff = intl / works - ref
        print(f"\n现有 m7（9/11 采集）= {ref:.1%}　本次 = {intl / works:.1%}　差 {diff * 100:+.1f} 个百分点")
        if abs(diff) > 0.05:
            print("! 差超过 5 个百分点：OpenAlex 的 countries_distinct_count 与我们按机构国家计的口径可能不一致")
            ok = False
    print()
    if ok:
        print("SMOKE TEST PASSED —— 可以跑全量了：")
        print('    $env:COLLECTOR_NAME = "你的真名"')
        print("    python scripts\\oa_intl_cn_probe.py --full")
    else:
        print("SMOKE TEST FAILED —— 不要跑全量。把上面整段发回给组长。")
    return ok


def full(ready):
    ca.require_collector()
    rows, soft_all = [], []
    cells = list(ca.quarters())
    inds = [i for i in ("ai", "biomed", "fintech") if i in ready]
    if len(inds) < 3:
        sys.exit(f"⛔ 规则文件里就绪的产业只有 {inds}，与统一采集包不一致，停下")
    n, i = len(inds) * len(CITIES) * len(cells), 0
    for ind in inds:
        for cc in CITIES:
            for q, d0, d1 in cells:
                i += 1
                label, _, _, vals = fetch_cell(ind, ready[ind], cc, q, d0, d1)
                tag = f"{label}/{cc}/{q}"
                _, soft = check(tag, vals, hard=True)
                soft_all += [f"{tag}: {s}" for s in soft]
                rows.append([label, cc, q, *vals])
                works, intl, cn_any, cn_only = vals
                print(f"[{i:>3}/{n}] {tag:<24} works={works:<6} intl={intl:<6} "
                      f"cn_any={cn_any:<6} cn_only={cn_only}")
    note = ("m7 国际合著的港—内地拆分（J7）。cn_only_works = 只有本城与中国内地两方机构的论文。"
            "产业过滤、国家范围、季度切分与 collect_openalex_master.py 一致；"
            "国际合著用 OpenAlex 的 countries_distinct_count，与统一采集包按机构 country_code 自数的口径"
            "可能有少量出入，works 与 intl_works 同批采集，比例内部一致。")
    if soft_all:
        note += f"｜软约束提示 {len(soft_all)} 条：" + "；".join(soft_all[:20])
    ca.save_rows(OUT_NAME, HEADER, rows, API,
                 "每个 产业×城市×季度 四次 meta.count：基础 filter；＋countries_distinct_count:>1；"
                 "＋authorships.institutions.country_code:cn；＋cn 且 countries_distinct_count:2",
                 note)
    print(f"\n完成 {len(rows)} 格。把 raw/{OUT_NAME}、manifests/ 下同名的 manifest 与 requests.tsv、"
          "以及这段运行输出一起发给组长。")
    if soft_all:
        print(f"（有 {len(soft_all)} 条软约束提示，已写进 manifest 的 notes，不影响使用）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="跑全部 3 产业 × 2 城 × 40 季。不加只做冒烟测试。")
    ap.add_argument("--dry", action="store_true", help="空跑：不发请求，只检查路径与 filter 拼装。")
    a = ap.parse_args()
    if a.dry:
        ca.DRY = True      # 必须改模块属性（2026-09-11 在 collect_authors.py 上踩过坑）
    ready, blocked = ca.load_rules()
    if a.full and not a.dry:
        full(ready)
    else:
        sys.exit(0 if smoke(ready) else 1)
