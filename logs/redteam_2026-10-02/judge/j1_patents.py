# -*- coding: utf-8 -*-
"""裁判抽查 j1：专利族级重建 + 关键主张重算（只读仓库）
输出到屏幕；中间表写本目录。
"""
import csv, collections, pathlib, re, sys
import pandas as pd

ROOT = pathlib.Path("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck")
OUT = pathlib.Path(__file__).resolve().parent

rows = list(csv.DictReader(open(ROOT / "raw/patents_families_raw.csv", encoding="utf-8-sig")))
smap = {r["assignee"].strip(): r["sector"].strip()
        for r in csv.DictReader(open(ROOT / "config/patents_assignee_sector.csv", encoding="utf-8-sig"))}
gx = list(csv.DictReader(open(ROOT / "config/patents_assignee_geo_exclude.csv", encoding="utf-8-sig")))
EX = {(g["city"], g["assignee"]) for g in gx if g["exclude_level"] in ("ali_grp", "ant_grp")}

def parts(r):
    return [a.strip() for a in (r["assignees"] or "").split(" | ") if a.strip()]

for r in rows:
    r["year"] = int(r["quarter"][:4])
    r["parts"] = parts(r)
    r["secs"] = {smap.get(a) for a in r["parts"]}
    cps = [a for a in r["parts"] if smap.get(a) == "company"]
    r["cps"] = cps
    hit = [a for a in cps if (r["city"], a) in EX]
    r["is_comp"] = bool(cps) and not (hit and len(hit) == len(cps))
    r["is_univ"] = "university" in r["secs"]

# ---------- 0. 复现：与仓库序列逐格核对 ----------
def official(kind):
    d = collections.defaultdict(float)
    for r in csv.DictReader(open(ROOT / f"raw/patents_families_by_quarter_{kind}.csv", encoding="utf-8-sig")):
        d[(r["industry"], r["city"], int(r["quarter"][:4]))] += float(r["patent_families"])
    return d
offc, offu = official("company_ali_ant_grp"), official("university")
mine_c = collections.Counter((r["industry"], r["city"], r["year"]) for r in rows if r["is_comp"])
mine_u = collections.Counter((r["industry"], r["city"], r["year"]) for r in rows if r["is_univ"])
bad = [k for k in set(offc) | set(mine_c) if abs(offc[k] - mine_c[k]) > 0]
badu = [k for k in set(offu) | set(mine_u) if abs(offu[k] - mine_u[k]) > 0]
print(f"[0] 复现：企业档差异格 {len(bad)}，大学档差异格 {len(badu)}")

def tot(counter, ind, city, ys):
    return sum(counter[(ind, city, y)] for y in ys)
E, L = (2015, 2016, 2017), (2021, 2022, 2023)
print("\n[0b] 企业专利三年合计与比值（项目口径）")
for i in ("ai", "biomed", "fintech"):
    he, se, hl, sl = tot(mine_c, i, "hk", E), tot(mine_c, i, "sg", E), tot(mine_c, i, "hk", L), tot(mine_c, i, "sg", L)
    print(f"  {i:8s} 2015–17 {he}/{se}={he/se:.3f}   2021–23 {hl}/{sl}={hl/sl:.3f}")

# ---------- 1. 商汤（geo-2）----------
st_re = re.compile(r"SENSE ?TIME", re.I)
print("\n[1] 商汤主体：各城各年企业档 AI 族数")
stc = collections.Counter()
for r in rows:
    if r["industry"] == "ai" and r["is_comp"] and any(st_re.search(a) for a in r["cps"]):
        stc[(r["city"], r["year"])] += 1
print("   ", dict(sorted(stc.items())))
names = sorted({a for r in rows for a in r["parts"] if st_re.search(a)})
print("    名称变体：", names)
# 族内是否全部企业申请人都是商汤（只有这种族才「整族」改归）
def all_st(r):
    return r["cps"] and all(st_re.search(a) for a in r["cps"])
mv = collections.Counter((r["city"], r["year"]) for r in rows if r["industry"] == "ai" and r["is_comp"] and all_st(r))
print("    其中企业申请人全为商汤的族：", dict(sorted(mv.items())))
sg_st_L = sum(mv[("sg", y)] for y in L); sg_st_E = sum(mv[("sg", y)] for y in E)
hl, sl = tot(mine_c, "ai", "hk", L), tot(mine_c, "ai", "sg", L)
he, se = tot(mine_c, "ai", "hk", E), tot(mine_c, "ai", "sg", E)
print(f"    V6 商汤改归香港：2015–17 {(he+sg_st_E)}/{(se-sg_st_E)}={(he+sg_st_E)/(se-sg_st_E):.3f}；"
      f"2021–23 {(hl+sg_st_L)}/{(sl-sg_st_L)}={(hl+sg_st_L)/(sl-sg_st_L):.3f}")
print(f"    商汤从新加坡剔除但不加回香港：2021–23 {hl}/{sl-sg_st_L}={hl/(sl-sg_st_L):.3f}")
print(f"    商汤占新加坡 AI 企业族（2021–23）：{sg_st_L}/{sl}={sg_st_L/sl:.3f}；2021 年 {mv[('sg',2021)]}/{mine_c[('ai','sg',2021)]}")

# ---------- 2. 宁德时代香港（geo-3/C4）----------
catl = re.compile(r"CONTEMPORARY AMPEREX", re.I)
cc = collections.Counter((r["city"], r["year"]) for r in rows if r["industry"] == "ai" and r["is_comp"] and r["cps"] and all(catl.search(a) for a in r["cps"]))
print("\n[2] 宁德时代香港：AI 企业族（企业申请人全为该集团）", dict(sorted(cc.items())))
hk_catl_L = sum(cc[("hk", y)] for y in L)
print(f"    香港 AI 企业 2021–23 {hl}，其中 CATL {hk_catl_L}（{hk_catl_L/hl:.3f}）；"
      f"香港 AI 企业 2015–17→2021–23 增量 {hl-he}")
print(f"    对称「总部归属」：商汤→香港 且 CATL 移出香港：2021–23 {(hl+sg_st_L-hk_catl_L)}/{(sl-sg_st_L)}={(hl+sg_st_L-hk_catl_L)/(sl-sg_st_L):.3f}")

# ---------- 3. 对称剔除前 k 大企业申请人（C3） ----------
# 按申请人名称分数归属（族内企业申请人均分），取每城每产业 2015–23 全窗前 k 大（按族次），两城各剔；
# 剔除规则：族内企业申请人全部属于被剔集合才剔（与项目规则同）。
def topk_variant(ind, k, window=None):
    out = {}
    for city in ("hk", "sg"):
        frac = collections.Counter()
        for r in rows:
            if r["industry"] == ind and r["city"] == city and r["is_comp"]:
                if window and r["year"] not in window:
                    continue
                for a in r["cps"]:
                    frac[a] += 1 / len(r["cps"])
        out[city] = {a for a, _ in frac.most_common(k)}
    res = {}
    for ys, tag in ((E, "E"), (L, "L")):
        n = {}
        for city in ("hk", "sg"):
            n[city] = sum(1 for r in rows if r["industry"] == ind and r["city"] == city and r["is_comp"]
                          and r["year"] in ys and not all(a in out[city] for a in r["cps"]))
        res[tag] = n["hk"] / n["sg"] if n["sg"] else float("nan")
    return res, out
print("\n[3] 两城对称剔除各自前 k 大企业申请人（按名称，非集团归并；全窗 2015–23 排名）")
for ind in ("ai", "biomed", "fintech"):
    for k in (1, 3, 5, 10):
        res, out = topk_variant(ind, k)
        print(f"   {ind:8s} k={k:2d}: 2015–17 {res['E']:.3f} → 2021–23 {res['L']:.3f}")
_, out10 = topk_variant("biomed", 10)
print("    生医前10（新加坡）：", sorted(out10["sg"]))
print("    生医前10（香港）：", sorted(out10["hk"]))

# 生医：新加坡增量的申请人分解（分数归属）
print("\n[3b] 新加坡生医企业 2015–17→2021–23 增量前 8 名（分数归属）")
d = collections.Counter()
for r in rows:
    if r["industry"] == "biomed" and r["city"] == "sg" and r["is_comp"] and (r["year"] in E or r["year"] in L):
        s = 1 if r["year"] in L else -1
        for a in r["cps"]:
            d[a] += s / len(r["cps"])
tot_inc = tot(mine_c, "biomed", "sg", L) - tot(mine_c, "biomed", "sg", E)
for a, v in d.most_common(8):
    print(f"     {a:50s} {v:+7.1f}  ({v/tot_inc:.3f} of {tot_inc})")
sn = re.compile(r"SMITH ?(&|AND) ?NEPHEW", re.I)
snc = collections.Counter((r["year"]) for r in rows if r["industry"] == "biomed" and r["city"] == "sg" and r["is_comp"] and r["cps"] and all(sn.search(a) for a in r["cps"]))
print("    Smith & Nephew（企业申请人全为该集团）新加坡生医各年：", dict(sorted(snc.items())))
snL, snE = sum(snc[y] for y in L), sum(snc[y] for y in E)
hb_E, sb_E = tot(mine_c, "biomed", "hk", E), tot(mine_c, "biomed", "sg", E)
hb_L, sb_L = tot(mine_c, "biomed", "sg", L) and tot(mine_c, "biomed", "hk", L), tot(mine_c, "biomed", "sg", L)
print(f"    只剔 S&N：2015–17 {hb_E}/{sb_E-snE}={hb_E/(sb_E-snE):.3f} → 2021–23 {hb_L}/{sb_L-snL}={hb_L/(sb_L-snL):.3f}")

# ---------- 4. 浸会大学（C4）与对称剔最大一家（geo-4）----------
hkbu = re.compile(r"BAPTIST", re.I)
cityu = re.compile(r"UNIV CITY|CITY UNIV|CITY INIVERSITY|CITY UNIVERSITY", re.I)
print("\n[4] 大学档：浸会、城大各年族数（生医）")
for nm, rx in (("浸会", hkbu), ("城大", cityu)):
    c = collections.Counter(r["year"] for r in rows if r["industry"] == "biomed" and r["city"] == "hk" and r["is_univ"]
                            and any(rx.search(a) and smap.get(a) == "university" for a in r["parts"]))
    print(f"   {nm}: ", dict(sorted(c.items())))
def univ_ratio(ind, drop_hk=None, drop_sg=None):
    res = {}
    for ys, tag in ((E, "E"), (L, "L")):
        n = {}
        for city, rx in (("hk", drop_hk), ("sg", drop_sg)):
            cnt = 0
            for r in rows:
                if r["industry"] == ind and r["city"] == city and r["is_univ"] and r["year"] in ys:
                    us = [a for a in r["parts"] if smap.get(a) == "university"]
                    if rx and all(rx.search(a) for a in us):
                        continue
                    cnt += 1
            n[city] = cnt
        res[tag] = (n["hk"], n["sg"], n["hk"] / n["sg"])
    return res
for ind in ("ai", "biomed"):
    b = univ_ratio(ind)
    print(f"   {ind} 基线：2015–17 {b['E'][0]}/{b['E'][1]}={b['E'][2]:.3f} → 2021–23 {b['L'][0]}/{b['L'][1]}={b['L'][2]:.3f}")
b = univ_ratio("biomed", drop_hk=hkbu)
print(f"   biomed 只剔浸会：{b['E'][0]}/{b['E'][1]}={b['E'][2]:.3f} → {b['L'][0]}/{b['L'][1]}={b['L'][2]:.3f}")
nus = re.compile(r"NAT(IONAL)? UNIV(ERSITY)? (OF )?SINGAPORE|UNIV SINGAPORE", re.I)
ntu = re.compile(r"NANYANG", re.I)
b = univ_ratio("biomed", drop_hk=cityu, drop_sg=nus)
print(f"   biomed 两城各剔城大/NUS：{b['E'][0]}/{b['E'][1]}={b['E'][2]:.3f} → {b['L'][0]}/{b['L'][1]}={b['L'][2]:.3f}")
b = univ_ratio("biomed", drop_hk=hkbu, drop_sg=nus)
print(f"   biomed 2015–17 各城最大一家（浸会/NUS）：{b['E'][0]}/{b['E'][1]}={b['E'][2]:.3f}")
b = univ_ratio("ai", drop_hk=cityu, drop_sg=ntu)
print(f"   ai 两城各剔城大/NTU：{b['E'][0]}/{b['E'][1]}={b['E'][2]:.3f} → {b['L'][0]}/{b['L'][1]}={b['L'][2]:.3f}")
b = univ_ratio("ai", drop_hk=cityu)
print(f"   ai 只剔城大：→ 2021–23 {b['L'][0]}/{b['L'][1]}={b['L'][2]:.3f}")
cu_share = {}
for ind in ("ai", "biomed"):
    n = sum(1 for r in rows if r["industry"] == ind and r["city"] == "hk" and r["is_univ"] and r["year"] in L)
    c = sum(1 for r in rows if r["industry"] == ind and r["city"] == "hk" and r["is_univ"] and r["year"] in L
            and any(cityu.search(a) and smap.get(a) == "university" for a in r["parts"]))
    print(f"   {ind} 2021–23 香港大学族中含城大 {c}/{n}={c/n:.3f}")

# ---------- 5. 万事达亚太（C4，金融科技）----------
mc = re.compile(r"MASTERCARD", re.I)
m = collections.Counter((r["city"], r["year"]) for r in rows if r["industry"] == "fintech" and r["is_comp"] and r["cps"] and all(mc.search(a) for a in r["cps"]))
print("\n[5] 万事达（企业申请人全为万事达）金融科技各城各年：", dict(sorted(m.items())))
print("    名称：", sorted({a for r in rows for a in r["parts"] if mc.search(a)}))
def fin3(y, drop):
    ys = (y-2, y-1, y)
    h = tot(mine_c, "fintech", "hk", ys)
    s = tot(mine_c, "fintech", "sg", ys) - (sum(m[("sg", t)] for t in ys) if drop else 0)
    return h / s
print("    金融科技企业三年滚动比值 基线：", " ".join(f"{y}:{fin3(y,False):.3f}" for y in range(2017, 2024)))
print("    剔万事达（新加坡）后：      ", " ".join(f"{y}:{fin3(y,True):.3f}" for y in range(2017, 2024)))
sg_fin_E, sg_fin_L = tot(mine_c, "fintech", "sg", E), tot(mine_c, "fintech", "sg", L)
print(f"    新加坡金融科技企业 2015–17 {sg_fin_E} → 2021–23 {sg_fin_L}（净 {sg_fin_L-sg_fin_E}）；万事达 {sum(m[('sg',y)] for y in E)} → {sum(m[('sg',y)] for y in L)}")

# ---------- 6. 跨城双计 ----------
fam = collections.defaultdict(set)
for r in rows:
    fam[(r["industry"], r["family_id"])].add(r["city"])
both = [k for k, v in fam.items() if len(v) == 2]
print(f"\n[6] 产业×家族 {len(fam)} 个，两城同时出现 {len(both)} 个")
