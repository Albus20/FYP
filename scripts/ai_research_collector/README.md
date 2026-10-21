# 港新 AI 论文、会议与专利采集包

交接日期：2026-10-21。默认2015—2025完整日历年，不含2026未完全年。专利2025申请年仍存在公开滞后，不等于完整2025产出。

仓库位置：`scripts/ai_research_collector/`。这是独立采集工具；结果保存在本目录的results/cache，默认被Git忽略。结果转入项目正式raw/clean前，按根目录README完成manifest登记与复核。包含作者ID的个人层面明细不要直接发布到公开GitHub。

## 同事怎么跑

1. 安装 Python 3.10或以上，解压到一个固定文件夹。
2. 双击 `START_WINDOWS.bat`。先选 **1（期刊）**，再选 **2（会议目录）**，最后选 **3（会议港新匹配）**。
3. 期刊和机构匹配需要自己的 OpenAlex API key：https://openalex.org/settings/api 。启动器会隐藏输入，不保存或打包密钥。会议官方目录不需要此key。
4. 中断、网络错误或额度用完：稍后重跑同一命令即可，缓存自动续采。不要删除cache。按Ctrl+C可暂停。
5. 跑完把 **整个文件夹（含results和cache）** 压缩回传，密钥不在文件里。

仅需要先试一年：
```powershell
python -m pip install -r requirements.txt
# 先在启动器输入key运行期刊，或自行设置环境变量 OPENALEX_API_KEY
python collect.py journals --start 2024 --end 2024
python collect.py catalog --start 2024 --end 2024
python collect.py pool --start 2024 --end 2024
```

完整命令：`python collect.py all`。会先采目录、再采期刊、再采港新论文池。建议用启动器分步跑，期刊最先出结果。会议匹配要采覆盖各学科的港新论文池，数据量较大、可能跨多个API额度日；这比逐篇搜索全球数万篇会议论文省调用。每页即时缓存，遇HTTP429停止，绝不自动购买额度。

## 范围

**8本期刊**：TPAMI、JMLR、Nature Machine Intelligence、Science Robotics、Nature Computational Science、Nature Methods、Nature正刊、Science正刊。

- TPAMI/JMLR收研究文章和综述；新增6刊在标题＋可得摘要中用config.json的AI关键词筛选。两种文章类型分开汇总；不把社论、新闻自动算成研究文章。
- 关键词包含人工智能、机器学习、深度学习、神经网络、强化学习、大语言模型、视觉、NLP、生成模型等。不是单独用“AI”二字母，也不单独用“transformer”。
- 无摘要且标题未命中者进入review_queue，不能理解为已经证实非AI。关键词筛选是可复现初筛，仍可能有误报。
- 期刊通过ISSN解析OpenAlex来源，不按出版集团匹配。创刊前年份不能解释成该地区零产出。

**10个会议**：NeurIPS、ICML、ICLR、CVPR、ICCV、ECCV、ACL、EMNLP、AAAI、IJCAI。

- 官方年度目录直接采集，含多卷；不靠OpenAlex会议总记录。目录为全球论文，之后按发表时署名机构筛HK/SG。不要按举办地或作者国籍判断地区。
- 主统计收主会研究论文；ACL长短文纳入，Findings、Workshop、演示、学生论坛等不纳入。IJCAI先收Main Track。AAAI按明确Technical/Main Track纳入。特殊轨道保留原标记供复核；NeurIPS各年轨道标签可能不齐，需检查是否混有Datasets & Benchmarks。
- ICCV/ECCV未举办的年份标记not_held。访问失败、目录结构变化标记needs_retry_or_import；绝不以失败当零。
- **早年ICLR/OpenReview、AAAI可能受访问限制，ECCV早期目录可能不齐。脚本会保留缺口，不保证每个会议每一年自动完整。** 不绕过验证码；可在官方网页手动导出后填manual_catalog_template.csv，再运行：
  `python collect.py import-catalog --file 手工目录.csv`
- imported目录会替换该会议年度自动目录。IJCAI的track填Main Track；AAAI填Technical Track；其余主会填main。请只导入官方正式录用文章。
- 匹配使用规范化精确标题和相邻发表年；同题多记录核对第一作者，歧义保留待查。不会把模糊标题搜索第一条直接当正确结果。
- OpenAlex港新论文池同时带作者、机构、引用、摘要等。未匹配的目录论文可能是外国论文，也可能缺港新机构元数据；本包**不自动用PDF补齐机构**。目录份额标为“已识别份额”，不承诺真实完整份额。

**原来不限期刊的AI样本**另有 `python collect.py all-ai`：沿用OpenAlex主主题1702，以便与之前研究者口径衔接；与精选顶刊顶会表分开，不相加。

**专利**：G06N、G06V、G10L、G06F40、B25J，申请人国家HK/SG，全球公开专利库；按地区×专利族去重、归入查询窗口内最早申请年/季度。是宽口径AI相关技术，不是每项都已人工确认AI。保留申请人、CPC、公开编号，缺family_id的记录单列不冒充专利族。

专利步骤：
1. `python patents.py` 生成 `ai_patents.sql`，复制到Google BigQuery运行，先看扫描量，再导出CSV。
2. `python patents.py --csv 你导出的.csv` 生成年度表和申请人待分类表。
3. 可选Python直连：`pip install google-cloud-bigquery`，配置自己的Google Cloud登录后，先 `python patents.py --project 项目ID`（仅估算，不执行收费查询）；实际运行加 `--execute`。默认扫描上限25GB，可显式调整`--max-gb`。
4. 申请人sector默认unclassified，需分company/university/public_rd。未分类前年度表是**全部申请人的专利族**，不能称企业专利。申请人地址也不自动等于总部或实质研发所在地。

## 交付文件

results/下CSV可直接用Excel打开：

| 文件 | 含义 |
|---|---|
| papers_HK_SG.csv | 港新论文明细，含作者ID、机构、引用与关键词 |
| annual_summary.csv | 年度×地区×期刊/会议汇总，article/review分开 |
| conference_coverage.csv | 目录数、可识别港新数及匹配准备状态 |
| catalog_status.csv | 各会议年度采集成功/失败/未举办状态 |
| review_queue.csv | 缺摘要、同题歧义、未匹配目录记录 |
| patents_raw.csv | 用Python执行BigQuery时生成的原始专利明细 |
| patents_annual.csv | 专利族年度统计 |
| patent_assignees_to_classify.csv | 企业/大学/公共机构分类工作表 |

annual_summary仅输出已识别的非空组；无行不自动等于零。作者只统计该篇论文上有本地机构的作者ID；不能把全部合著者算作港新人才。各期刊作者人数不能直接相加。年度表暂不计算三年滚动存量或季度人才指数，明细可供后续计算。引用为采集时快照，高引分位缺失不当作0。

会议年份与论文在线发表年可能不同，会议用会议年、期刊用发表年。港新合著论文可在两地各计1篇；合并两地时必须去重。

## 官方资料入口

- OpenAlex认证：https://help.openalex.org/api/authentication/
- NeurIPS：https://proceedings.neurips.cc/
- ICML：https://proceedings.mlr.press/
- ICLR：https://proceedings.iclr.cc/ 、https://openreview.net/venue?id=ICLR.cc
- CVPR/ICCV：https://openaccess.thecvf.com/
- ECCV：https://www.ecva.net/papers.php
- ACL/EMNLP：https://aclanthology.org/
- AAAI：https://ojs.aaai.org/index.php/AAAI/issue/archive
- IJCAI：https://www.ijcai.org/all_proceedings
- Patents：https://console.cloud.google.com/marketplace/product/google_patents_public_datasets/google-patents-public-data
