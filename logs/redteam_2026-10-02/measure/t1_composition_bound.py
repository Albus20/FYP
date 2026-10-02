# T1：构成差异要多大，才能单独解释「论文多、专利少」？（反推边界，不需新数据）
# 设专利 = 论文 × [s·p_b + (1−s)·p_c]，s = 专利倾向高的（基础/工程/药学）论文份额，p_c = k·p_b（临床论文的专利倾向是基础论文的 k 倍）
# 构成单独解释落差 ⇔ [s_h(1−k)+k]/[s_s(1−k)+k] = G，G = 专利比 / 论文比
import pandas as pd
G={"生医·大学(9/11)":0.473/1.125,"生医·大学(10/2,2021–23论文0.940)":0.473/0.940,
   "生医·企业(9/11)":0.369/1.125,"生医·企业(10/2)":0.369/0.940,
   "AI·大学(9/11)":0.315/1.029,"AI·企业(9/11)":0.163/1.029}
rows=[]
for name,g in G.items():
    for s_s in (0.3,0.5,0.7):
        for k in (0.0,0.1,0.2):
            s_h=(g*(s_s*(1-k)+k)-k)/(1-k)
            rows.append(dict(case=name,G=round(g,3),s_sg=s_s,k=k,required_s_hk=round(s_h,3),required_ratio=round(s_h/s_s,3)))
d=pd.DataFrame(rows); print(d.to_string(index=False))
# 临床强度代理：非企业申办临床试验 / 生医论文
ct=pd.read_csv("/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/raw/clinicaltrials_sponsor_by_quarter.csv"); ct=ct[ct.quarter.str[:4].astype(int).between(2022,2024)&(ct.sponsor_class!="INDUSTRY")].groupby("city")["count"].sum()/3; ct_hk,ct_sg=ct.hk,ct.sg; print("非企业申办试验 2022–24 年均",round(ct_hk,1),round(ct_sg,1))
for v,r in (("9/11",1.125),("10/2",0.975),("8/26",0.912)):
    print(f"非企业临床试验每篇生医论文 港/星（论文 {v} 版本）：{(ct_hk/ct_sg)/r:.2f}")
