# 2025年香港与新加坡AI企业专利采集包

目的：补现有表的2025年企业专利族。这里只采AI，金融及生物不混入。
本包不含账号或密钥；已附原项目企业分类与阿里/蚂蚁主体剔除名单。

仓库路径：`scripts/ai_patents_2025/`。先进入本目录运行命令。结果默认被Git忽略；这次提交仅提供工具，不代表2025年已采集成功。结果进入正式raw/clean前仍须按仓库要求登记来源并复核。

## 最简单：网页下载，再本地汇总

1. 用有BigQuery权限的Google账号打开 https://console.cloud.google.com/bigquery ，选择自己的项目。
2. 将 `ai_patents_2025.sql` 全文复制到查询编辑器。先看预计扫描量，再运行。账号若要求两步验证，须自行完成。
3. 保存完整查询结果为CSV，命名 `patents_raw_2025.csv`，放在解压目录。不要只复制预览前几行。
4. 安装Python 3.10或以上，在本目录运行：

```sh
python collect.py --csv patents_raw_2025.csv
```

这条本地汇总命令不需要安装第三方库，也不需要Google登录。

## 自动下载：有Google Cloud环境的同事用

```sh
python -m pip install -r requirements.txt
gcloud auth application-default login
python collect.py --project YOUR_PROJECT
python collect.py --project YOUR_PROJECT --execute --max-gb 50
```

把YOUR_PROJECT换成自己的项目ID。第一条查询只估算扫描量；第二条才实际运行。Cloud Shell通常可省略登录命令。50 GB是扫描上限，不是免费额度承诺，超出上限会停止。

## 回传哪些文件

把 `results` 整个目录回传即可，主要包括：
- `港新AI企业专利_2025年度.csv`：香港、新加坡各一行，Excel可打开。
- `港新AI企业专利_2025季度.csv`：两地四个季度。
- `family_audit_2025.csv`：每个专利族保留/排除/待判断的依据。
- `new_assignees_to_classify.csv`：新申请人。不要默认全是企业。
- 原始CSV及查询记录（自动下载时生成）。网页下载时也请把原始CSV一并回传。

新申请人需要分类时，把 `new_assignees_to_classify.csv` 复制为 `config/new_assignees.csv`，填写sector：company、university、public_rd或individual，再运行同一汇总命令。未填项继续保留待审核。原有未归类申请人沿用之前不计企业的规则，标为legacy_noncompany，不表示已证实是个人。

如果新企业名称疑似阿里/蚂蚁相关主体，审计表会标记，不能自动当作本地实质研发。确认属于原剔除范围后，在config/exclusions.csv增补；若确实应保留但名称触发保守规则，先回传核实，不要随意改名绕过。

## 与之前表一致的口径

- 地区按申请人国家代码HK/SG，不是专利局所在地，也不是直接认定研发所在地。
- CPC范围：G06N、G06V、G10L、G06F40、B25J；这是原项目宽口径AI，包含语音、视觉及机器人。
- 按地区×专利族去重，年度为2015年以来查询窗口内最早的相关申请年。先查询2015—2025，再筛2025，避免老家族的2025后续申请被重复当新家族。
- 企业口径沿用ali_ant_grp版本：有未剔除的企业共同申请人即保留；全为被剔除企业则排除。大学单独申请不计企业。
- 2025年申请尚可能未公开。即便采集成功，也只能称“2025年已公开的企业专利族观察值”，不能视为完整总量或与成熟年份直接比降幅。
- 新分类未完成时，最终观察值列留空，另列已确认数与待判断数，防止把未知当零。
- 跨快照比较可能改变历史归属；建议把原始结果保留，之后需要严格联动分析时统一重拉历史，而不是只看2025增减。

## 验证与边界

本包本地回归核对原2023年结果，并测试重复族、共同申请人、未知分类等情况。由于当前机器没有可用云凭据，未实际执行线上SQL、未取得2025年真实人数/族数。空结果只表示当前查询未命中，不证明现实没有专利。

离线测试（不需要Google账号）：`python -B -m unittest -v test_collect`。

官方说明：
- https://docs.cloud.google.com/bigquery/docs/authentication/getting-started
- https://docs.cloud.google.com/bigquery/docs/running-queries
- https://github.com/google/patents-public-data
