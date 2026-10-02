# 附带发现：config/patents_assignee_sector.csv 中几个疑似错分的申请人在 raw/patents_families_raw.csv 中的族数
# 运行：python3 assignee_side_check.py（只读仓库文件）
import pandas as pd, re
R = '/tmp/claude-0/-home-claude/3e9f71b2-5429-5949-8004-13ec051b1731/scratchpad/ghcheck/'
cfg = pd.read_csv(R + 'config/patents_assignee_sector.csv')
df = pd.read_csv(R + 'raw/patents_families_raw.csv')
names = ['LABORATORY FOR SYNTHETIC CHEMISTRY AND CHEMICAL BIOLOGY LTD', 'LABORATORY OF DATA DISCOVERY FOR HEALTH LTD',
         'LOGISTICS AND SUPPLY CHAIN MULTI TECH R&D CENTRE LTD', 'LOGISTICS AND SUPPLY CHAIN MULTITECH R&D CENTRE LTD',
         'TEMASEK LIFE SCIENCES LAB LTD', 'TEMASEK LIFE SICENCES LABORATORY LTD',
         'AON SINGAPORE CENTRE FOR INNOVATION STRATEGY AND MAN PTE LTD', 'AON SINGAPORE CENTRE FOR INNOVTION STRATEGY AND MAN']
for n in names:
    sec = cfg.loc[cfg.assignee == n, 'sector'].tolist()
    m = df[df['assignees'].fillna('').str.contains(re.escape(n))]
    print(n, sec, len(m), m.groupby(['industry', 'city']).size().to_dict())
m = df[df['assignees'].fillna('').str.contains('SHENZHEN', case=False)]
print('申请人名含 SHENZHEN 的族数:', len(m))
