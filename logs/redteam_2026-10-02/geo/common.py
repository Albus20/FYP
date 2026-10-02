import csv, collections, pathlib
ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")
OUT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/redteam/geo")
rows = list(csv.DictReader(open(ROOT/"raw/patents_families_raw.csv", encoding="utf-8-sig")))
smap = {r["assignee"].strip(): r["sector"].strip() for r in csv.DictReader(open(ROOT/"config/patents_assignee_sector.csv", encoding="utf-8-sig"))}
gx = list(csv.DictReader(open(ROOT/"config/patents_assignee_geo_exclude.csv", encoding="utf-8-sig")))
EX = {(g["city"], g["assignee"]) for g in gx}
def parts(r): return [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]
def year(r): return int(r["quarter"][:4])
def secs(r): return {smap.get(a) for a in parts(r)}
def is_company_kept(r, extra_ex=frozenset()):
    """company 口径 + ali_ant_grp 剔除（全部 company 申请人都在剔除名单才剔），extra_ex 为额外剔除 (city, assignee)"""
    cps = [a for a in parts(r) if smap.get(a) == "company"]
    if not cps: return False
    ex = EX | set(extra_ex)
    hit = [a for a in cps if (r["city"], a) in ex]
    return not (hit and len(hit) == len(cps))
