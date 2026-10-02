# 生医企业研发港星比（口径不同：HK=C&SD 表 710-86107「Biotechnology」技术领域；SG=data.gov.sg 私营部门「Biomedical & Related Sciences」研究领域）
# HK: https://www.censtatd.gov.hk/api/get.php?id=710-86107&lang=en&full_series=1
# SG: https://data.gov.sg/api/action/datastore_search?resource_id=d_092342c287b5b20280ab6b47263cb858
# 汇率：用世界银行 GDP(现价美元)/GDP(现价本币) 隐含汇率
hk_bio = {2021: 1515.4, 2022: 1718.0, 2023: 2260.4}
sg_bio = {2021: 861.97, 2022: 822.44, 2023: 707.94}
hk_fx = {2021: 368954169748.818/2867973000000, 2022: 358673532516.529/2808922000000, 2023: 380762296025.216/2981210000000}
sg_fx = {2021: 441110903524.645/592625000000, 2022: 514252535238.749/708983000000, 2023: 511181761243.760/686398000000}
# 软件+信息系统（HK）作为 AI/金融科技相关企业研发的粗略代理——SG 无对应细分，不算比值
tot_h = tot_s = 0
for y in (2021, 2022, 2023):
    h = hk_bio[y]*hk_fx[y]; s = sg_bio[y]*sg_fx[y]
    tot_h += h; tot_s += s
    print(y, 'HK 生物技术企业研发 %.0f 百万美元, SG 私营生医研发 %.0f 百万美元, 比 %.2f' % (h, s, h/s))
print('2021-23 合计比 %.2f' % (tot_h/tot_s))
print('故事线生医企业专利比 0.37 ÷ 上述比 = %.2f' % (0.37/(tot_h/tot_s)))
