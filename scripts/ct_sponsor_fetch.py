# -*- coding: utf-8 -*-
r"""
ct_sponsor_fetch.py —— 临床试验按申办方类型全量采集（J10）

═══ 为什么采 ═══

生医产出篮子（docs/分产业产出篮子口径_2026-09-30.md）用「全部临床试验」作主口径。
香港的临床试验很多由大学和医院发起，不一定代表产业。稳健性检查 e 要看：
只数「企业申办」（leadSponsor.class = INDUSTRY）的试验，港/星比较的方向变不变。

═══ 做法：与 ct_phase_fetch.py（J4-2）完全同一套 ═══

逐个 城市×季度 把全部试验记录拉回来（只要 nctId 和申办方模块），
本地读 protocolSection.sponsorCollaboratorsModule.leadSponsor.class 归类：

    INDUSTRY 企业 · NIH · FED 美国联邦 · OTHER_GOV 其他政府 · INDIV 个人
    NETWORK 协作网络 · OTHER 其他（大学、医院多在这里）· UNKNOWN · AMBIG
    NO_SPONSOR_CLASS  记录里没有这个字段（与 UNKNOWN 是两回事，不合并）

城市、季度、日期字段与 J4-2 一致：query.locn ＋ StudyFirstPostDate，2015Q1–2024Q4。

═══ 两道自检 ═══

① 冒烟测试（默认）：只跑 hk/2024Q1（1 次请求），检查
   · totalCount 与 9/25 采集的季度总数 109 相差不超过 5（库会缓慢更新，见 docs/ClinicalTrials计数漂移_2026-09-27.md）
   · 各档合计 == totalCount
   · 没有申办方类型字段的记录 ≤ 5%（否则说明 fields 参数的返回结构变了）
② 逐格自检（全量）：每个 城市×季度 都必须 Σ(各档) == totalCount，否则停下、不写盘。

═══ 用法（PowerShell，在 data_repo 文件夹里；在 scripts 文件夹里就去掉 "scripts\"；
     用 PyCharm 就在运行配置的 Parameters 填 --full、Environment variables 填 COLLECTOR_NAME=你的真名）═══

    # 第一步：冒烟测试（1 次请求，几秒钟）
    python scripts\ct_sponsor_fetch.py

    # 看到 SMOKE TEST PASSED 之后
    $env:COLLECTOR_NAME = "你的真名"
    python scripts\ct_sponsor_fetch.py --full        # 约 90 次请求，3–5 分钟

产物：raw/clinicaltrials_sponsor_by_quarter.csv
      manifests/clinicaltrials_sponsor_by_quarter.csv.manifest.json
      manifests/clinicaltrials_sponsor_by_quarter.csv.requests.tsv

R1：不产生任何数据值，全部来自 API 返回。
R2：全量模式必须设 COLLECTOR_NAME，否则拒跑。
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
except ImportError:
    sys.exit("缺 requests：pip install requests")

API = "https://clinicaltrials.gov/api/v2/studies"
TERMS = {"hk": "Hong Kong", "sg": "Singapore"}
PAGE = 200
# 取整个 sponsorCollaboratorsModule（很小：申办方、合作方、责任方），比只写到 leadSponsor 更稳妥
FIELDS = "protocolSection.identificationModule.nctId,protocolSection.sponsorCollaboratorsModule"
NO_CLASS = "NO_SPONSOR_CLASS"
KNOWN = {"INDUSTRY", "NIH", "FED", "OTHER_GOV", "INDIV", "NETWORK", "OTHER", "UNKNOWN", "AMBIG"}

# 冒烟基准：賈贇 9/23 探针与 9/25 季度总数都是 109
SMOKE = {"cc": "hk", "q": "2024Q1", "total": 109, "tol": 5, "max_missing": 0.05}

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _collector_from_keys_env():
    """环境里没设 COLLECTOR_NAME 时，从 data_repo/.keys.env 读（与 run_phase2.ps1 同一个文件）。"""
    f = ROOT / ".keys.env"
    if os.environ.get("COLLECTOR_NAME") or not f.exists():
        return
    for line in f.read_text(encoding="utf-8-sig").splitlines():
        t = line.strip()
        if "=" in t and t.split("=", 1)[0].strip() == "COLLECTOR_NAME":
            v = t.split("=", 1)[1].strip().strip('"').strip("'")
            if v:
                os.environ["COLLECTOR_NAME"] = v
                print("（从 .keys.env 载入 COLLECTOR_NAME）")
            return


OUT = ROOT / "raw" / "clinicaltrials_sponsor_by_quarter.csv"
MAN_DIR = ROOT / "manifests"
REF = ROOT / "raw" / "clinicaltrials_by_quarter.csv"
REQ_LOG = []            # (url, city, quarter) —— 供 R4 逐条复核
FALLBACK = []           # 带 fields 被拒、改为整条记录重拉的格


def quarters(y0=2015, y1=2024):
    """与 collect_all.py 的 Q_START/Q_END、ct_phase_fetch.py 严格对齐。"""
    ends = ["-03-31", "-06-30", "-09-30", "-12-31"]
    for y in range(y0, y1 + 1):
        for qn in range(1, 5):
            yield f"{y}Q{qn}", f"{y}-{3 * (qn - 1) + 1:02d}-01", f"{y}{ends[qn - 1]}"


def get(params, tag):
    """带退避重试：429、5xx、网络中断、返回内容不完整各重试 4 次（10/20/40/80 秒）。返回 (response, json)。"""
    last = None
    for attempt in range(5):
        try:
            r = requests.get(API, params=params, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
            else:
                r.raise_for_status()
                return r, r.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            last = f"网络中断：{e.__class__.__name__}"
        except requests.exceptions.Timeout:
            last = "超时"
        except ValueError:
            last = "返回内容不是完整 JSON"
        if attempt < 4:
            wait = 10 * 2 ** attempt
            print(f"    {tag}：{last}，等 {wait} 秒重试")
            time.sleep(wait)
    raise RuntimeError(f"{tag} 重试 4 次仍失败（{last}）。过一会儿原样再跑一次即可。")


def fetch_cell(cc, qlabel, d0, d1, use_fields=True):
    """拉回一个 城市×季度 的全部记录，返回 (totalCount, [申办方类型或 None ...])。"""
    flt = f"AREA[StudyFirstPostDate]RANGE[{d0},{d1}]"
    studies, token, pages, total = [], None, 0, None
    while True:
        p = {"query.locn": TERMS[cc], "filter.advanced": flt,
             "pageSize": PAGE, "countTotal": "true"}
        if use_fields:
            p["fields"] = FIELDS
        if token:
            p["pageToken"] = token
        try:
            r, j = get(p, f"{cc}/{qlabel}")
        except requests.exceptions.HTTPError as e:
            if use_fields:          # fields 写法被 API 拒绝（400 等）：整格改为不带 fields 重拉
                print(f"    ! 带 fields 的请求被拒（{e}），改为不带 fields 重拉 {cc}/{qlabel}")
                FALLBACK.append(f"{cc}/{qlabel}")
                return fetch_cell(cc, qlabel, d0, d1, use_fields=False)
            raise
        batch = j.get("studies", [])
        # fields 参数万一被 API 拒绝或改了形状，返回的记录会缺 protocolSection：整格改为不带 fields 重拉
        if use_fields and batch and "protocolSection" not in batch[0]:
            print(f"    ! fields 参数返回的结构不对，改为不带 fields 重拉 {cc}/{qlabel}")
            FALLBACK.append(f"{cc}/{qlabel}")
            return fetch_cell(cc, qlabel, d0, d1, use_fields=False)
        REQ_LOG.append((r.url, cc, qlabel))
        if pages == 0:
            total = j.get("totalCount")
        studies += batch
        pages += 1
        token = j.get("nextPageToken")
        if not token:
            break
        if pages > 50:
            raise RuntimeError(f"{cc}/{qlabel} 翻页超过 50 页，异常，停下")
        time.sleep(0.3)
    out = []
    for s in studies:
        ls = ((s.get("protocolSection") or {}).get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
        c = ls.get("class")
        out.append(str(c).strip().upper() if c else None)
    return total, out


def classify(classes):
    c = collections.Counter()
    for k in classes:
        c[k if k else NO_CLASS] += 1
    return c


def smoke_test():
    print("=" * 70)
    print("冒烟测试：hk/2024Q1 一格，检查总数、合计与字段是否取到")
    print("=" * 70)
    d0, d1 = {q: (a, b) for q, a, b in quarters()}[SMOKE["q"]]
    total, cls = fetch_cell(SMOKE["cc"], SMOKE["q"], d0, d1)
    got = classify(cls)
    ok = True
    print(f"\n{SMOKE['cc']}/{SMOKE['q']}　totalCount = {total}　取回 {len(cls)} 条\n")
    print(f"{'申办方类型':<20}{'条数':>6}")
    for k, v in got.most_common():
        flag = "" if k in KNOWN or k == NO_CLASS else "   ← 新出现的取值，照实记录"
        print(f"{k:<20}{v:>6}{flag}")
    if total is None:
        print("\n! 没拿到 totalCount")
        ok = False
    else:
        if abs(total - SMOKE["total"]) > SMOKE["tol"]:
            print(f"\n! totalCount {total} 与 9/25 采集的 {SMOKE['total']} 相差超过 {SMOKE['tol']}")
            ok = False
        else:
            print(f"\ntotalCount {total}，9/25 采集为 {SMOKE['total']}（相差 {total - SMOKE['total']:+d}，在容许范围内）")
        if sum(got.values()) != total:
            print(f"! 各档合计 {sum(got.values())} ≠ totalCount {total}")
            ok = False
    miss = got.get(NO_CLASS, 0) / max(len(cls), 1)
    print(f"没有申办方类型字段的记录：{got.get(NO_CLASS, 0)} 条（{miss:.0%}）")
    if miss > SMOKE["max_missing"]:
        print("! 超过 5%：fields 参数的返回结构可能变了")
        ok = False
    print()
    if ok:
        print("SMOKE TEST PASSED —— 可以跑全量了：")
        print('    $env:COLLECTOR_NAME = "你的真名"')
        print("    python scripts\\ct_sponsor_fetch.py --full")
    else:
        print("SMOKE TEST FAILED —— 不要跑全量。把上面整段发回给组长。")
    return ok


def load_ref():
    ref = {}
    try:
        with open(REF, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                ref[(r["city"], r["quarter"])] = int(r["count"])
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return ref


def full_run():
    _collector_from_keys_env()
    by = os.environ.get("COLLECTOR_NAME", "").strip()
    if not by or by.startswith("UNSET"):
        sys.exit('⛔ 未设 COLLECTOR_NAME（R2：manifest 必须记真实采集人）。\n'
                 '   PowerShell：$env:COLLECTOR_NAME = "你的真名"')
    ref = load_ref()
    rows, drift, cells = [], [], list(quarters())
    n, i = len(TERMS) * len(cells), 0
    for cc in TERMS:
        for qlabel, d0, d1 in cells:
            i += 1
            total, cls = fetch_cell(cc, qlabel, d0, d1)
            got = classify(cls)
            if total is None:
                raise RuntimeError(f"{cc}/{qlabel} 没拿到 totalCount，停下")
            if sum(got.values()) != total:
                raise RuntimeError(
                    f"⛔ {cc}/{qlabel} 各档合计 {sum(got.values())} ≠ totalCount {total}。\n"
                    f"   已拿到的分布：{dict(got)}\n   拒绝写盘。把这段发回给组长。")
            if (cc, qlabel) in ref and ref[(cc, qlabel)] != total:
                drift.append(f"{cc}/{qlabel} {ref[(cc, qlabel)]}→{total}")
            for k in sorted(got):
                rows.append([cc, qlabel, k, got[k]])
            print(f"[{i:>2}/{n}] {cc}/{qlabel}  total={total:<4} INDUSTRY={got.get('INDUSTRY', 0):<4} "
                  f"缺字段={got.get(NO_CLASS, 0)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["city", "quarter", "sponsor_class", "count"])
        w.writerows(rows)
    MAN_DIR.mkdir(parents=True, exist_ok=True)
    log = MAN_DIR / (OUT.name + ".requests.tsv")
    with open(log, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["url", "city", "quarter"])
        w.writerows(REQ_LOG)
    total_all = sum(r[3] for r in rows)
    miss_all = sum(r[3] for r in rows if r[2] == NO_CLASS)
    drift_note = (f"与 9/25 季度总数（raw/clinicaltrials_by_quarter.csv）比对：{len(ref)} 格中 {len(drift)} 格不同"
                  + (f"：{'；'.join(drift[:30])}" if drift else "") + "。差异来自库更新，非采集错误。") if ref else \
                 "未找到 raw/clinicaltrials_by_quarter.csv，未做总数比对。"
    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    man = MAN_DIR / (OUT.name + ".manifest.json")
    man.write_text(json.dumps({
        "file": f"raw/{OUT.name}",
        "sha256": sha,
        "source_url": API,
        "query_or_method":
            "query.locn×StudyFirstPostDate 逐季度拉回全量记录（fields=nctId,sponsorCollaboratorsModule），"
            "本地读 protocolSection.sponsorCollaboratorsModule.leadSponsor.class 归类。与 ct_phase_fetch.py 同法。",
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "collected_by": by,
        "notes":
            f"J10·生医产出篮子稳健性检查 e（仅企业申办）。档位 {NO_CLASS} = 记录里没有申办方类型字段，"
            f"与取值 UNKNOWN 不同，不可合并；全量 {miss_all}/{total_all}。"
            f"逐格自检：每个城市×季度均满足 Σ(各档)==totalCount，否则脚本已停止。{drift_note}"
            + (f"｜带 fields 被拒、改为整条记录重拉的格：{'、'.join(FALLBACK)}" if FALLBACK else ""),
        "manifest_version": 2,
        "request_log": log.name,
        "request_count": len(REQ_LOG),
        "example_request_url": REQ_LOG[0][0] if REQ_LOG else "",
        "request_log_note":
            "采集时逐条记录的真实请求 URL。复核方法：点开 URL，核对 totalCount 是否等于该城市×季度各档 count 之和。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写入 raw/{OUT.name}　{len(rows)} 行（{total_all} 项试验，其中缺字段 {miss_all}）")
    print(f"请求日志 manifests/{log.name}　{len(REQ_LOG)} 条")
    print(f"manifest manifests/{man.name}")
    print(f"与 9/25 季度总数不同的格：{len(drift)}（库会缓慢更新，个位数差异属正常）")
    print("\n完成。把 raw 下的 csv、manifests 下的两个文件、以及这段运行输出一起发给组长。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="跑全部 2 城 × 40 季。不加只做冒烟测试。")
    a = ap.parse_args()
    if a.full:
        full_run()
    else:
        sys.exit(0 if smoke_test() else 1)
