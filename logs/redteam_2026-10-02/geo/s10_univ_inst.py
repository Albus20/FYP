from common import *
import re
MAP=[("hk","CityU",r"CITY"),("hk","CUHK",r"CHINES"),("hk","PolyU",r"POLYTECHNIC"),("hk","HKUST",r"SCI"),
     ("hk","HKBU",r"BAPTIST"),("hk","EdUHK",r"EDUCATION"),("hk","HKU",r"UNIV HONG KONG$|UNIV OF HONG KONG|VERSITECH"),
     ("sg","NUH/NUHS(医院)",r"HOSPITAL|HEALTH SYSTEM"),("sg","理工学院",r"POLYTECHNIC"),("sg","NTU",r"NANY ?ANG|NANYANG"),
     ("sg","SUTD",r"DESIGN"),("sg","SMU",r"MAN"),("sg","NUS",r"SINGAP|SINGPORE")]
def inst(c,a):
    for cc,n,p in MAP:
        if cc==c and re.search(p,a): return n
    return "其他:"+a
def univ_fams(i,c,yrs):
    out=[]
    for r in rows:
        if r["industry"]==i and r["city"]==c and year(r) in yrs and "university" in secs(r):
            out.append((r["family_id"],{inst(c,a) for a in parts(r) if smap.get(a)=="university"}))
    return out
res={}
for y0 in (2015,2021):
    yrs=(y0,y0+1,y0+2)
    print(f"\n######## {y0}-{y0+2}")
    for i in ("ai","biomed","fintech"):
        F={c:univ_fams(i,c,yrs) for c in ("hk","sg")}
        line={}
        for c in ("hk","sg"):
            cc=collections.Counter(x for _,s in F[c] for x in s)
            n=len(F[c])
            line[c]=cc
            print(f"  {i}/{c} 大学族 {n}: " + "；".join(f"{k} {v}（{v/n:.0%}）" for k,v in cc.most_common(10)))
        h=len(F["hk"]); s=len(F["sg"])
        if s==0: continue
        top_h=line["hk"].most_common(1)[0][0]; top_s=line["sg"].most_common(1)[0][0]
        h_d=sum(1 for _,x in F["hk"] if x-{top_h}); s_d=sum(1 for _,x in F["sg"] if x-{top_s})
        # 重分类：新加坡医院→public_rd，理工学院剔除
        s_r=sum(1 for _,x in F["sg"] if x-{"NUH/NUHS(医院)","理工学院"})
        nusntu=sum(1 for _,x in F["sg"] if x&{"NUS","NTU"})
        print(f"   比值 基线 {h}/{s}={h/s:.3f} | 两城各剔最大一家（港 {top_h}，星 {top_s}）{h_d}/{s_d}={h_d/s_d if s_d else float('nan'):.3f}"
              f" | 只剔港最大 {h_d}/{s}={h_d/s:.3f} | 只剔星最大 {h}/{s_d}={h/s_d if s_d else float('nan'):.3f}"
              f" | 星医院/理工学院改出大学档 {h}/{s_r}={h/s_r:.3f} | NUS+NTU 占星 {nusntu/s:.0%}")
        # 头部对头部
        a=line["hk"].most_common(1)[0][1]; b=line["sg"].most_common(1)[0][1]
        print(f"   头部对头部：{top_h} {a} ÷ {top_s} {b} = {a/b:.2f}；港第 2–n 名合计 vs 星第 2–n 名合计见上")
