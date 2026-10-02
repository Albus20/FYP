from common import *
exec(open("s7_variants.py").read().split("V={")[0])
D1sg={"foreign_mnc","mainland_grp","lenovo","hk_grp"}; D1hk={"foreign_mnc","mainland_grp","lenovo"}
for i in ("ai","biomed"):
    print(f"\n{i}: 年度企业族数 与 三年滚动比值")
    for y in range(2015,2024):
        h0=count(i,"hk",(y,)); s0=count(i,"sg",(y,)); h1=count(i,"hk",(y,),D1hk); s1=count(i,"sg",(y,),D1sg)
        st=sum(1 for r in rows if r["industry"]==i and r["city"]=="sg" and year(r)==y and is_company_kept(r) and any(cat("sg",a)=="hk_grp" for a in fam_company_assignees(r)))
        lm=sum(1 for r in rows if r["industry"]==i and r["city"]=="sg" and year(r)==y and is_company_kept(r) and any(a=="LEMON INC" for a in fam_company_assignees(r)))
        line=f"  {y}: HK {h0:4d} SG {s0:4d} (商汤 {st:3d}, Lemon {lm:3d}) | V1: HK {h1:4d} SG {s1:4d}"
        if y>=2017:
            yrs=(y-2,y-1,y)
            line+=f" | 滚动 V0 {count(i,'hk',yrs)/count(i,'sg',yrs):.3f}  V1 {count(i,'hk',yrs,D1hk)/count(i,'sg',yrs,D1sg):.3f}"
        print(line)
