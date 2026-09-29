# -*- coding: utf-8 -*-
r"""
bis_payments_fetch.py —— 港星支付数字化数据：BIS 支付统计 ＋ 世界银行人口（J8）

═══ 为什么采这个 ═══

金融科技的专利与论文都太少（专利约为 AI 的四分之一，论文约为生医的 2%），
撑不起港星对比。2026-09-29 组长同意改看「支付是否被用起来」：
国际清算银行（BIS）的 CPMI 支付统计由香港金管局、新加坡金管局按同一口径报送，
是唯一现成、两城对称的官方序列。

⚠️ 已知限制（2026-09-29 预查，采回后由组长确认）：
    · 香港电子货币序列从 2017 年才有（2016 年底才有储值支付牌照制度），新加坡从 2012 年起
    · 香港快速支付（FPS）从 2018 年起，新加坡（FAST）从 2015 年起
    · 电子货币笔数里交通卡（八达通、易通卡）占大头，香港 2021 年起还受消费券影响
  所以这组数据定位为「支付数字化」的背景指标，只做年度港星对比，不进季度分析。

═══ 采什么 ═══

    ① BIS WS_CPMI_CT1（零售支付、现金及相关指标），香港＋新加坡全部年度序列，原样保存
    ② 世界银行人口 SP.POP.TOTL（HKG、SGP，2012–2024），两城同一来源，用来算人均

挑哪几条序列、怎么折算人均，采回来后由组长在本地做（R1：本脚本只存原件）。

═══ 用法 ═══

    # 第一步：冒烟测试（2 次请求，不写盘）
    python scripts\bis_payments_fetch.py

    # 看到 SMOKE TEST PASSED 后
    $env:COLLECTOR_NAME = "你的真名"
    python scripts\bis_payments_fetch.py --full

产物：raw/bis_cpmi_ct1_hk_sg.csv、raw/worldbank_population_hk_sg.csv，
      以及 manifests/ 下各自的 manifest 与 requests.tsv。
"""
import argparse
import collections
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_all as ca   # noqa: E402
import requests            # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CPMI_CT1/1.0/A.HK+SG........"
BIS_PARAMS = {"format": "csv"}
WB_URL = "https://api.worldbank.org/v2/country/HKG;SGP/indicator/SP.POP.TOTL"
WB_PARAMS = {"format": "json", "date": "2012:2024", "per_page": "100"}
BIS_OUT = "bis_cpmi_ct1_hk_sg.csv"
WB_OUT = "worldbank_population_hk_sg.csv"
WATCH = ("e-money", "Fast payments", "Population", "Credit transfers", "All Card and e-money")


def get(url, params, tag):
    ca.log_request(url, params, tag)
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=90)
        if r.status_code in (429, 503):
            ca.log(f"{r.status_code} @{tag} → 等 {20 * (attempt + 1)}s 重试")
            import time; time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"{tag} 重试后仍失败")


def parse_bis(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    need = {"REP_CTY", "TITLE_TS", "TIME_PERIOD", "OBS_VALUE"}
    if not rows or not need <= set(rows[0]):
        raise RuntimeError(f"BIS 返回的表头不对：{list(rows[0]) if rows else '空'}")
    return rows


def coverage(rows):
    """{(城市, 标题): [有值的年份]}"""
    cov = collections.defaultdict(list)
    for r in rows:
        v = (r.get("OBS_VALUE") or "").strip()
        if v and v.lower() != "nan":
            cov[(r["REP_CTY"], r["TITLE_TS"])].append(r["TIME_PERIOD"])
    return cov


def parse_wb(j):
    if not isinstance(j, list) or len(j) < 2 or not isinstance(j[1], list):
        raise RuntimeError(f"世界银行返回的结构不对：{str(j)[:200]}")
    out = []
    for d in j[1]:
        iso = (d.get("countryiso3code") or "").upper()
        city = {"HKG": "hk", "SGP": "sg"}.get(iso)
        if city and d.get("value") is not None:
            out.append([city, d["date"], int(d["value"])])
    return sorted(out, key=lambda x: (x[0], x[1]))


def show(rows, pop):
    cov = coverage(rows)
    print(f"BIS：{len(rows):,} 行，{len(cov)} 条有值的序列")
    print("\n与支付数字化相关的序列（城市 · 标题 · 有值年份）：")
    for (cty, title), yrs in sorted(cov.items()):
        if any(w.lower() in title.lower() for w in WATCH):
            print(f"   {cty}  {title[:70]:<70} {min(yrs)}–{max(yrs)}（{len(yrs)} 年）")
    print(f"\n世界银行人口：{len(pop)} 行 " +
          "；".join(f"{c} {min(y for cc, y, _ in pop if cc == c)}–{max(y for cc, y, _ in pop if cc == c)}"
                   for c in ("hk", "sg") if any(cc == c for cc, _, _ in pop)))
    ok_emoney = {c for (c, t) in cov if "e-money" in t.lower()}
    ok_pop = {c for c, _, _ in pop}
    return {"HK", "SG"} <= {c.upper() for c in ok_emoney} and {"hk", "sg"} <= ok_pop


def smoke():
    print("=" * 72)
    print("冒烟测试：各发 1 次请求，只看能不能拿到、有哪些序列，不写盘")
    print("=" * 72)
    rows = parse_bis(get(BIS_URL, BIS_PARAMS, "bis/ct1/hk+sg").text)
    pop = parse_wb(get(WB_URL, WB_PARAMS, "worldbank/pop").json())
    ok = show(rows, pop)
    print()
    if ok:
        print("SMOKE TEST PASSED —— 可以跑全量了：")
        print('    $env:COLLECTOR_NAME = "你的真名"')
        print("    python scripts\\bis_payments_fetch.py --full")
    else:
        print("SMOKE TEST FAILED —— 港星两边的电子货币序列或人口没拿全。把上面整段发回给组长。")
    return ok


def full():
    ca.require_collector()
    ca.RAW.mkdir(parents=True, exist_ok=True)

    # ① BIS：原样落盘（字节级，不改一个字）
    r = get(BIS_URL, BIS_PARAMS, "bis/ct1/hk+sg")
    rows = parse_bis(r.text)
    p = ca.RAW / BIS_OUT
    p.write_bytes(r.content)
    reqs = ca.write_request_log(BIS_OUT)
    ca.write_manifest(p, "https://data.bis.org/topics/CPMI_CT",
                      "BIS SDMX API：WS_CPMI_CT1 1.0，key A.HK+SG........（两城全部年度序列），format=csv；响应原样保存",
                      "J8·金融科技产出的替代口径（支付数字化，背景指标）。已知：香港电子货币 2017 年起、FPS 2018 年起；"
                      "新加坡电子货币 2012 年起、FAST 2015 年起。电子货币笔数含交通卡；香港 2021 年起受消费券影响。"
                      "序列选择与人均折算在 clean 层完成。", reqs)
    ca.log(f"raw/{BIS_OUT} 写入 {len(rows):,} 行")

    # ② 世界银行人口
    j = get(WB_URL, WB_PARAMS, "worldbank/pop").json()
    pop = parse_wb(j)
    ca.save_rows(WB_OUT, ["city", "year", "population"], pop,
                 "https://data.worldbank.org/indicator/SP.POP.TOTL",
                 "World Bank API v2：country HKG;SGP，indicator SP.POP.TOTL，date 2012:2024",
                 "J8·人均折算用分母，两城同一来源")

    print()
    show(rows, pop)
    print(f"\n完成。把 raw/{BIS_OUT}、raw/{WB_OUT}、manifests/ 下对应的 manifest 与 requests.tsv、"
          "以及这段运行输出一起发给组长。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="落盘。不加只做冒烟测试。")
    a = ap.parse_args()
    if a.full:
        full()
    else:
        sys.exit(0 if smoke() else 1)
