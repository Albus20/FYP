from common import *
exec(open("s7_variants.py").read().split("V={")[0])
D1sg={"foreign_mnc","mainland_grp","lenovo","hk_grp"}; D1hk={"foreign_mnc","mainland_grp","lenovo"}
print("AI 企业专利三年滚动比值：V0 基线 | V6 基线+商汤改归香港 | V1 两城同剔外地集团 | V5 V1+商汤改归香港")
for y in range(2017,2024):
    yrs=(y-2,y-1,y)
    h0=count("ai","hk",yrs); s0=count("ai","sg",yrs); m=moved("ai",yrs,"hk_grp")
    h1=count("ai","hk",yrs,D1hk); s1=count("ai","sg",yrs,D1sg)
    print(f"  {y-2}-{y}: V0 {h0}/{s0}={h0/s0:.3f} | V6 {h0+m}/{s0-m}={(h0+m)/(s0-m):.3f} | V1 {h1}/{s1}={h1/s1:.3f} | V5 {h1+m}/{s1}={(h1+m)/s1:.3f}  (商汤族 {m})")
