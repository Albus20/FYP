# 外部官方统计的港星研发投入比较（只用下列 URL 中取得的数字，未改仓库任何文件）
# 来源：
#  WB GERD%GDP  https://api.worldbank.org/v2/country/HKG;SGP/indicator/GB.XPD.RSDV.GD.ZS?format=json&date=2013:2024 (lastupdated 2026-07-13)
#  WB GDP US$   https://api.worldbank.org/v2/country/HKG;SGP/indicator/NY.GDP.MKTP.CD?format=json&date=2015:2024
#  WB GDP LCU   https://api.worldbank.org/v2/country/SGP;HKG/indicator/NY.GDP.MKTP.CN?format=json&date=2015:2024
#  WB 研究人员/百万人 https://api.worldbank.org/v2/country/HKG;SGP/indicator/SP.POP.SCIE.RD.P6?format=json&date=2013:2024
#  WB 人口      https://api.worldbank.org/v2/country/HKG;SGP/indicator/SP.POP.TOTL?format=json&date=2015:2024
#  HK 分部门 GERD 2014-16: https://www.censtatd.gov.hk/en/data/stat_report/product/B1110010/att/B11100102016AN16B0100.pdf
#  HK 分部门 GERD 2019-24: https://www.censtatd.gov.hk/api/get.php?id=710-86004&lang=en&full_series=1
#  SG 分部门 R&D 支出: https://data.gov.sg/api/action/datastore_search?resource_id=d_092342c287b5b20280ab6b47263cb858
#  SG R&D 人力 2015: https://data.gov.sg/api/action/datastore_search?resource_id=d_9bad05d1afb13f6a11c243fd65f1d0f1
#  HK R&D 人力 2015/2023: 上述 HK 2016 年刊 PDF 与 B11100102023AN23.pdf

gerd_pct = {  # WB
    'HK': {2015: 0.76183, 2022: 1.07293, 2023: 1.10625, 2024: 1.12597},
    'SG': {2015: 2.17445, 2022: 1.80821},
}
gdp_usd = {
    'HK': {2015: 309385622601.348, 2022: 358673532516.529, 2023: 380762296025.216, 2024: 408368682415.423},
    'SG': {2015: 307998545269.398, 2022: 514252535238.749, 2023: 511181761243.760, 2024: 572877260178.427},
}
gdp_lcu_sg = {2023: 686398000000, 2015: 423444100000, 2022: 708983000000}
# 分部门（本币百万）
hk = {  # business, higher_ed, government, total  (HK$ m)
    2015: (7994, 9551, 726, 18271),
    2022: (12370.7, 16355.5, 1412.2, 30138.4),
    2023: (12975.7, 18327.9, 1702.4, 33006.0),
    2024: (13906.1, 20054.2, 1811.6, 35771.9),
}
sg = {  # private, IHL, government(incl. PRIs), total (S$ m)
    2015: (5469.39, 1583.42, 2154.76, 9207.58),
    2022: (8130.09, 1716.71, 2829.40, 12676.21),
    2023: (8955.99, 1872.64, 2918.28, 13746.91),
}

# SG 2023 GERD/GDP 由本币算
gerd_pct['SG'][2023] = sg[2023][3] * 1e6 / gdp_lcu_sg[2023] * 100

def usd(city, yr):
    return gerd_pct[city][yr] / 100 * gdp_usd[city][yr] / 1e9

print('== GERD/GDP (%) ==')
for yr in (2015, 2022, 2023):
    print(yr, 'HK %.2f' % gerd_pct['HK'][yr], 'SG %.2f' % gerd_pct['SG'][yr])

print('\n== 部门结构（占 GERD %） ==')
for yr in (2015, 2022, 2023):
    b, h, g, t = hk[yr]
    pb, ph, pg, pt = sg[yr]
    print(yr, 'HK 企业 %.1f 高校 %.1f 政府 %.1f' % (b/t*100, h/t*100, g/t*100),
          '| SG 私营 %.1f 高校 %.1f 政府+PRI %.1f' % (pb/pt*100, ph/pt*100, pg/pt*100))

print('\n== 以美元计的 GERD 及分部门（十亿美元；= GERD%×GDP美元×部门份额） ==')
rows = []
for yr in (2015, 2022, 2023):
    hk_usd, sg_usd = usd('HK', yr), usd('SG', yr)
    b, h, g, t = hk[yr]
    pb, ph, pg, pt = sg[yr]
    hkB, hkH, hkG = hk_usd*b/t, hk_usd*h/t, hk_usd*g/t
    sgB, sgH, sgG = sg_usd*pb/pt, sg_usd*ph/pt, sg_usd*pg/pt
    print(yr, 'GERD HK %.2f SG %.2f 比 %.2f' % (hk_usd, sg_usd, hk_usd/sg_usd))
    print('     企业 HK %.2f SG %.2f 比 %.2f' % (hkB, sgB, hkB/sgB))
    print('     高校 HK %.2f SG %.2f 比 %.2f' % (hkH, sgH, hkH/sgH))
    print('     政府(含SG PRI) HK %.2f SG %.2f 比 %.2f' % (hkG, sgG, hkG/sgG))
    print('     高校+政府 HK %.2f SG %.2f 比 %.2f' % (hkH+hkG, sgH+sgG, (hkH+hkG)/(sgH+sgG)))
    print('     企业研发/GDP HK %.2f%% SG %.2f%%' % (gerd_pct['HK'][yr]*b/t, gerd_pct['SG'][yr]*pb/pt))

print('\n== 研究人员（FTE，WB/UIS 每百万人 × 人口） ==')
rpm = {'HK': {2015: 3487.90, 2022: 4815.20}, 'SG': {2015: 7134.93, 2022: 8781.74}}
pop = {'HK': {2015: 7291300, 2022: 7346100}, 'SG': {2015: 5535002, 2022: 5637022}}
for yr in (2015, 2022):
    h = rpm['HK'][yr]*pop['HK'][yr]/1e6
    s = rpm['SG'][yr]*pop['SG'][yr]/1e6
    print(yr, 'HK %.0f SG %.0f 比 %.2f（每百万人比 %.2f）' % (h, s, h/s, rpm['HK'][yr]/rpm['SG'][yr]))

print('\n== 分部门 R&D 人力（FTE，含研究人员、技术与辅助人员） 2015 ==')
hk15 = {'business': 12217, 'higher_ed': 15247, 'government': 701}
sg15 = {'private': 1713.9+4969.1+11185.7+1892.4+1472.5+1810.1,
        'ihl': 4197.6+1398.0+1988.1+71.1+5862.0+170.6+396.9,
        'gov': 460.8+611.3+1003.4+70.5+448.7+1284.0,
        'pri': 2270.3+553.5+867.9+66.6+424.5+264.5}
print('SG 2015 分部门合计', {k: round(v, 1) for k, v in sg15.items()})
print('企业/私营 HK/SG %.2f' % (hk15['business']/sg15['private']))
print('高校 HK/SG %.2f' % (hk15['higher_ed']/sg15['ihl']))
print('高校+政府 vs 高校+政府+PRI HK/SG %.2f' % ((hk15['higher_ed']+hk15['government'])/(sg15['ihl']+sg15['gov']+sg15['pri'])))

print('\n== HKUST 衍生公司地点（HKUST_Socioeconomic_Impact.pdf p.39-41） ==')
hkc, sz, gz = 415, 120, 53
print('香港 %.1f%%  深圳+广州 %.1f%%（分母=三地合计 %d）' % (hkc/(hkc+sz+gz)*100, (sz+gz)/(hkc+sz+gz)*100, hkc+sz+gz))

print('\n== 与故事线比值对照（故事线比值取自 docs/故事线与证据链_2026-10-02.md 表一、表二） ==')
# 高校研发支出比（美元）：2015 1.07，2022 1.66；企业研发支出比：2015 0.26，2022 0.26
he = {2015: usd('HK',2015)*hk[2015][1]/hk[2015][3] / (usd('SG',2015)*sg[2015][1]/sg[2015][3]),
      2022: usd('HK',2022)*hk[2022][1]/hk[2022][3] / (usd('SG',2022)*sg[2022][1]/sg[2022][3])}
be = {2015: usd('HK',2015)*hk[2015][0]/hk[2015][3] / (usd('SG',2015)*sg[2015][0]/sg[2015][3]),
      2022: usd('HK',2022)*hk[2022][0]/hk[2022][3] / (usd('SG',2022)*sg[2022][0]/sg[2022][3])}
uni_pat = {'AI': (0.33, 0.32), 'BIO': (0.52, 0.47)}           # 2015-17 -> 2021-23
co_pat = {'AI': (0.26, 0.16), 'BIO': (0.64, 0.37), 'FIN': (0.18, 0.22)}
for k, (a, b) in uni_pat.items():
    print('大学专利/高校研发支出 %s: 2015 %.2f -> 2022 %.2f' % (k, a/he[2015], b/he[2022]))
for k, (a, b) in co_pat.items():
    print('企业专利/企业研发支出 %s: 2015 %.2f -> 2022 %.2f' % (k, a/be[2015], b/be[2022]))

print('\n== 规模：人口与 GDP（WB） ==')
popall = {'HK': {2015: 7291300, 2022: 7346100, 2023: 7536100, 2024: 7524100},
          'SG': {2015: 5535002, 2022: 5637022, 2023: 5917648, 2024: 6036860}}
for yr in (2015, 2022, 2023, 2024):
    print(yr, '人口比 HK/SG %.2f' % (popall['HK'][yr]/popall['SG'][yr]),
          ' GDP(美元)比 HK/SG %.2f' % (gdp_usd['HK'][yr]/gdp_usd['SG'][yr]))
g21 = 368954169748.818 + gdp_usd['HK'][2022] + gdp_usd['HK'][2023]
s21 = 441110903524.645 + gdp_usd['SG'][2022] + gdp_usd['SG'][2023]
print('2021-23 合计 GDP 比 HK/SG %.2f' % (g21/s21))
print('HK 企业研发占 GERD 2024: %.1f%%' % (13906.1/35771.9*100))
