# -*- coding: utf-8 -*-
r"""
ct_phase_fetch.py —— 临床试验按期别全量采集（J4-2）

═══ 为什么不能用 AREA[Phase] 逐期别 count ═══

賈贇 2026-09-23 实测 hk/2024Q1（totalCount = 109）：

    NA                73
    <没有 phases 字段> 14      ← 关键
    PHASE3            12
    PHASE2             7
    EARLY_PHASE1       1
    PHASE1             1
    PHASE4             1
    ───────────────────────
    单值 95 · 多值组合 0 · 无字段 14 · 合计 109

那 14 条**根本没有 phases 字段**，用任何 AREA[Phase]xxx 都筛不到，
逐期别 count 会系统性少计约 13%。（组长此前推断「是多值组合」，实测多值为 0，推断错误。）

所以改为：**拉全量记录回来，本地归类**。调用量反而更少（80 次 vs 480 次）。

═══ 两道自检 ═══

① 冒烟测试（默认行为）：先只跑 hk/2024Q1，跟上面那组已知值逐项比对。
   对不上就停下，不进入全量——避免拿一个坏脚本烧 80 次请求。

② 逐格自检（全量时）：每个 城市×季度 都必须满足

       Σ(各档 count) == totalCount

   对不上立即抛错停下。J4 这次漏数，就是因为原方案没有这道检查。

═══ 用法 ═══

    # 第一步：冒烟测试（1 次请求，十几秒）
    python scripts\ct_phase_fetch.py

    # 看到 SMOKE TEST PASSED 之后，再跑全量
    set COLLECTOR_NAME=你的真名
    python scripts\ct_phase_fetch.py --full

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

try:
    import requests
except ImportError:
    sys.exit("缺 requests：pip install requests")

API = "https://clinicaltrials.gov/api/v2/studies"
TERMS = {"hk": "Hong Kong", "sg": "Singapore"}
PAGE = 200

# 只要这两个字段，避免把整份试验记录拉回来（全量约 8000 条，不裁剪会是几百 MB）
FIELDS = "protocolSection.identificationModule.nctId,protocolSection.designModule.phases"

NO_PHASE = "NO_PHASE_FIELD"     # 没有 phases 字段，与 "NA" 是两回事

# 賈贇 2026-09-23 探针实测值，用作回归基准
SMOKE = {
    "cc": "hk", "q": "2024Q1", "total": 109,
    "buckets": {"NA": 73, NO_PHASE: 14, "PHASE3": 12,
                "PHASE2": 7, "EARLY_PHASE1": 1, "PHASE1": 1, "PHASE4": 1},
}

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ_LOG = []            # (url, city, quarter) —— 供 R4 逐条复核


def quarters(y0=2015, y1=2024):
    """与 collect_all.py 的 Q_START/Q_END 严格对齐，否则两条序列错位。"""
    ends = ["-03-31", "-06-30", "-09-30", "-12-31"]
    for y in range(y0, y1 + 1):
        for qn in range(1, 5):
            yield f"{y}Q{qn}", f"{y}-{3 * (qn - 1) + 1:02d}-01", f"{y}{ends[qn - 1]}"


def fetch_cell(cc, qlabel, d0, d1, use_fields=True):
    """拉回一个 城市×季度 的全部记录，返回 (totalCount, [phases元组...])。"""
    flt = f"AREA[StudyFirstPostDate]RANGE[{d0},{d1}]"
    studies, token, pages, total = [], None, 0, None

    while True:
        p = {"query.locn": TERMS[cc], "filter.advanced": flt,
             "pageSize": PAGE, "countTotal": "true"}
        if use_fields:
            p["fields"] = FIELDS
        if token:
            p["pageToken"] = token

        r = requests.get(API, params=p, timeout=90)
        r.raise_for_status()
        j = r.json()
        REQ_LOG.append((r.url, cc, qlabel))

        batch = j.get("studies", [])

        # fields 参数万一被 API 拒绝或改了形状，返回的记录会缺 protocolSection。
        # 一旦发现就整格退回不带 fields 重拉，不要硬撑。
        if use_fields and batch and "protocolSection" not in batch[0]:
            print(f"    ! fields 参数返回的结构不对，改为不带 fields 重拉 {cc}/{qlabel}")
            return fetch_cell(cc, qlabel, d0, d1, use_fields=False)

        if pages == 0:
            total = j.get("totalCount")
        studies += batch
        pages += 1
        token = j.get("nextPageToken")
        if not token:
            break
        if pages > 50:
            raise RuntimeError(f"{cc}/{qlabel} 翻页超过 50 页，异常，停下")
        time.sleep(0.2)

    out = []
    for s in studies:
        dm = (s.get("protocolSection") or {}).get("designModule") or {}
        ph = dm.get("phases")
        out.append(tuple(ph) if ph else None)      # None = 没有 phases 字段
    return total, out


def classify(phase_tuples):
    """归类成 {档位: 条数}。多值组合照实记成 'PHASE1|PHASE2'，不合并、不丢弃。"""
    c = collections.Counter()
    for ph in phase_tuples:
        c[NO_PHASE if ph is None else "|".join(ph)] += 1
    return c


def smoke_test():
    print("=" * 70)
    print("冒烟测试：跑一格，跟賈贇 2026-09-23 探针实测值比对")
    print("=" * 70)
    qmap = {q: (d0, d1) for q, d0, d1 in quarters()}
    d0, d1 = qmap[SMOKE["q"]]
    total, phs = fetch_cell(SMOKE["cc"], SMOKE["q"], d0, d1)
    got = classify(phs)

    print(f"\n{SMOKE['cc']}/{SMOKE['q']}　totalCount = {total}　取回 {len(phs)} 条\n")
    print(f"{'档位':<20}{'本次':>8}{'基准':>8}  结果")
    ok = True
    for k in sorted(set(got) | set(SMOKE["buckets"])):
        a, b = got.get(k, 0), SMOKE["buckets"].get(k, 0)
        mark = "OK" if a == b else "<<< 不一致"
        if a != b:
            ok = False
        print(f"{k:<20}{a:>8}{b:>8}  {mark}")

    if total != SMOKE["total"]:
        print(f"\n! totalCount {total} ≠ 基准 {SMOKE['total']}")
        ok = False
    if sum(got.values()) != total:
        print(f"\n! 各档合计 {sum(got.values())} ≠ totalCount {total}")
        ok = False

    print()
    if ok:
        print("SMOKE TEST PASSED —— 可以跑全量了：")
        print("    set COLLECTOR_NAME=你的真名")
        print("    python scripts\\ct_phase_fetch.py --full")
    else:
        print("SMOKE TEST FAILED —— 不要跑全量。把上面整段发回给组长。")
        print("（少量漂移可能是 ClinicalTrials.gov 库更新所致，由组长判断，你不用自己决定。）")
    return ok


def full_run():
    by = os.environ.get("COLLECTOR_NAME", "").strip()
    if not by or by.startswith("UNSET"):
        sys.exit("⛔ 未设 COLLECTOR_NAME（R2：manifest 必须记真实采集人）。\n"
                 "   set COLLECTOR_NAME=你的真名")

    rows, cells = [], list(quarters())
    n = len(TERMS) * len(cells)
    i = 0
    for cc in TERMS:
        for qlabel, d0, d1 in cells:
            i += 1
            total, phs = fetch_cell(cc, qlabel, d0, d1)
            got = classify(phs)

            # 逐格自检：加不满就停，不静默跳过
            s = sum(got.values())
            if total is None:
                raise RuntimeError(f"{cc}/{qlabel} 没拿到 totalCount，停下")
            if s != total:
                raise RuntimeError(
                    f"⛔ {cc}/{qlabel} 各档合计 {s} ≠ totalCount {total}，差 {total - s}。\n"
                    f"   已拿到的分布：{dict(got)}\n"
                    f"   拒绝写盘。把这段发回给组长。")

            for k in sorted(got):
                rows.append([cc, qlabel, k, got[k]])
            print(f"[{i:>3}/{n}] {cc}/{qlabel}  total={total:<5} 档位={len(got)}")

    out = ROOT / "raw" / "clinicaltrials_phase_by_quarter.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["city", "quarter", "phase", "count"])
        w.writerows(rows)

    log = out.with_suffix(".csv.requests.tsv")
    with open(log, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["url", "city", "quarter"])
        w.writerows(REQ_LOG)

    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    man = ROOT / "manifests" / (out.name + ".manifest.json")
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps({
        "file": f"raw/{out.name}",
        "sha256": sha,
        "source_url": API,
        "query_or_method":
            "query.locn×StudyFirstPostDate 逐季度拉回全量记录，"
            "本地读 protocolSection.designModule.phases 归类。"
            "不使用 AREA[Phase] 过滤——相当比例的试验没有 phases 字段"
            "（賈贇 2026-09-23 探针单格 14/109≈13%；2026-09-28 全量 1,022/5,501=18.6%），"
            "任何 AREA[Phase]xxx 都筛不到。",
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "collected_by": by,
        "notes":
            f"附录A指标9·IDI创新·按期别拆分。档位 {NO_PHASE} = 没有 phases 字段，"
            "与取值 NA 是两回事，不可合并。多值组合照实记为 'PHASE1|PHASE2' 形式。"
            "逐格自检：每个城市×季度均满足 Σ(各档)==totalCount，否则脚本已停止。",
        "manifest_version": 2,
        "request_log": log.name,
        "request_count": len(REQ_LOG),
        "example_request_url": REQ_LOG[0][0] if REQ_LOG else "",
        "request_log_note":
            "采集时逐条记录的真实请求 URL。复核方法：点开 URL，"
            "核对 totalCount 是否等于该城市×季度各档 count 之和。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n写入 {out}　{len(rows)} 行")
    print(f"请求日志 {log}　{len(REQ_LOG)} 条")
    print(f"manifest {man}")
    print(f"sha256 {sha}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="跑全部 2 城 × 40 季。不加这个参数只做冒烟测试。")
    a = ap.parse_args()
    if a.full:
        full_run()
    else:
        sys.exit(0 if smoke_test() else 1)
