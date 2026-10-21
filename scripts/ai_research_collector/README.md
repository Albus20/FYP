# ���� AI ���ġ�������ר���ɼ���

�������ڣ�2026-10-21��Ĭ��2015��2025���������꣬����2026δ��ȫ�ꡣר��2025�������Դ��ڹ����ͺ󣬲���������2025������

�ֿ�λ�ã�`scripts/ai_research_collector/`�����Ƕ����ɼ����ߣ���������ڱ�Ŀ¼��results/cache��Ĭ�ϱ�Git���ԡ����ת����Ŀ��ʽraw/cleanǰ������Ŀ¼README���manifest�Ǽ��븴�ˡ���������ID�ĸ��˲�����ϸ��Ҫֱ�ӷ���������GitHub��

## ͬ����ô��

1. ��װ Python 3.10�����ϣ���ѹ��һ���̶��ļ��С�
2. ˫�� `START_WINDOWS.bat`���Զ���� Python ���ڱ�Ŀ¼����������������ѡ **1���ڿ���**�����ֱ�ӻس����� **2024**�����ܳɹ����ؿ���������� **all** ��2015��2025����ѡ **2������Ŀ¼��**�����ѡ **3���������ƥ�䣩**����ݷ�Χ����һ�¡�
3. �ڿ��ͻ���ƥ����Ҫ�Լ��� OpenAlex API key��https://openalex.org/settings/api �����������������룬�����������Կ������ٷ�Ŀ¼����Ҫ��key��
4. �жϡ��������������꣺�Ժ�����ͬһ����ɣ������Զ����ɡ���Ҫɾ��cache����Ctrl+C����ͣ��
5. ����� **�����ļ��У���results��cache��** ѹ���ش�����Կ�����ļ��

2026-10-21�����棺OpenAlex��ҳ�Ѹ�Ϊÿҳ100��������ʵʱ���Ⱥ�`logs/`������־����;ʧ��Ҳ�ᵼ���������ݡ�ԭ���е�Ŀ¼�ͻ�������֤���ϣ�`papers_HK_SG.csv`��`annual_summary.csv`ԭ�Ƚ��б�ͷ��������Ϊ�ɼ���ɡ�API key����ʱ����ʾ�ַ���ճ���󰴻س����ɡ���װʧ�ܿ�`logs/setup.log`���ɼ�ʧ�ܻش����µ�`logs/*_journals.log`��`*_pool.log`���ɶ�λ����δ��ɵ���ݱ�����ҳ���棬���ܻ����ʹ�û��档

����Ҫ����һ�꣺
```powershell
python -m pip install -r requirements.txt
# ��������������key�����ڿ������������û������� OPENALEX_API_KEY
python collect.py journals --start 2024 --end 2024
python collect.py catalog --start 2024 --end 2024
python collect.py pool --start 2024 --end 2024
```

�������`python collect.py all`�����Ȳ�Ŀ¼���ٲ��ڿ����ٲɸ������ĳء��������������ֲ��ܣ��ڿ����ȳ����������ƥ��Ҫ�ɸ��Ǹ�ѧ�Ƶĸ������ĳأ��������ϴ󡢿��ܿ���API����գ������ƪ����ȫ������ƪ��������ʡ���á�ÿҳ��ʱ���棬��HTTP429ֹͣ�������Զ������ȡ�

## ��Χ

**8���ڿ�**��TPAMI��JMLR��Nature Machine Intelligence��Science Robotics��Nature Computational Science��Nature Methods��Nature������Science������

- TPAMI/JMLR���о����º�����������6���ڱ��⣫�ɵ�ժҪ����config.json��AI�ؼ���ɸѡ�������������ͷֿ����ܣ��������ۡ������Զ�����о����¡�
- �ؼ��ʰ����˹����ܡ�����ѧϰ�����ѧϰ�������硢ǿ��ѧϰ��������ģ�͡��Ӿ���NLP������ģ�͵ȡ����ǵ����á�AI������ĸ��Ҳ�������á�transformer����
- ��ժҪ�ұ���δ�����߽���review_queue����������Ϊ�Ѿ�֤ʵ��AI���ؼ���ɸѡ�ǿɸ��ֳ�ɸ���Կ������󱨡�
- �ڿ�ͨ��ISSN����OpenAlex��Դ���������漯��ƥ�䡣����ǰ��ݲ��ܽ��ͳɸõ����������

**10������**��NeurIPS��ICML��ICLR��CVPR��ICCV��ECCV��ACL��EMNLP��AAAI��IJCAI��

- �ٷ����Ŀ¼ֱ�Ӳɼ��������������OpenAlex�����ܼ�¼��Ŀ¼Ϊȫ�����ģ�֮�󰴷���ʱ��������ɸHK/SG����Ҫ���ٰ�ػ����߹����жϵ�����
- ��ͳ���������о����ģ�ACL���������룬Findings��Workshop����ʾ��ѧ����̳�Ȳ����롣IJCAI����Main Track��AAAI����ȷTechnical/Main Track���롣����������ԭ��ǹ����ˣ�NeurIPS��������ǩ���ܲ��룬�����Ƿ����Datasets & Benchmarks��
- ICCV/ECCVδ�ٰ����ݱ��not_held������ʧ�ܡ�Ŀ¼�ṹ�仯���needs_retry_or_import��������ʧ�ܵ��㡣
- **����ICLR/OpenReview��AAAI�����ܷ������ƣ�ECCV����Ŀ¼���ܲ��롣�ű��ᱣ��ȱ�ڣ�����֤ÿ������ÿһ���Զ�������** ���ƹ���֤�룻���ڹٷ���ҳ�ֶ���������manual_catalog_template.csv�������У�
  `python collect.py import-catalog --file �ֹ�Ŀ¼.csv`
- importedĿ¼���滻�û�������Զ�Ŀ¼��IJCAI��track��Main Track��AAAI��Technical Track������������main����ֻ����ٷ���ʽ¼�����¡�
- ƥ��ʹ�ù淶����ȷ��������ڷ����ꣻͬ����¼�˶Ե�һ���ߣ����屣�����顣�����ģ������������һ��ֱ�ӵ���ȷ�����
- OpenAlex�������ĳ�ͬʱ�����ߡ����������á�ժҪ�ȡ�δƥ���Ŀ¼���Ŀ�����������ģ�Ҳ����ȱ���»���Ԫ���ݣ�����**���Զ���PDF�������**��Ŀ¼�ݶ��Ϊ����ʶ��ݶ������ŵ��ʵ�����ݶ

**ԭ�������ڿ���AI����**���� `python collect.py all-ai`������OpenAlex������1702���Ա���֮ǰ�о��߿ھ��νӣ��뾫ѡ����������ֿ�������ӡ�

**ר��**��G06N��G06V��G10L��G06F40��B25J�������˹���HK/SG��ȫ�򹫿�ר���⣻��������ר����ȥ�ء������ѯ����������������/���ȡ��ǿ��ھ�AI��ؼ���������ÿ����˹�ȷ��AI�����������ˡ�CPC��������ţ�ȱfamily_id�ļ�¼���в�ð��ר���塣

ר�����裺
1. `python patents.py` ���� `ai_patents.sql`�����Ƶ�Google BigQuery���У��ȿ�ɨ�������ٵ���CSV��
2. `python patents.py --csv �㵼����.csv` ������ȱ��������˴��������
3. ��ѡPythonֱ����`pip install google-cloud-bigquery`�������Լ���Google Cloud��¼���� `python patents.py --project ��ĿID`�������㣬��ִ���շѲ�ѯ����ʵ�����м� `--execute`��Ĭ��ɨ������25GB������ʽ����`--max-gb`��
4. ������sectorĬ��unclassified�����company/university/public_rd��δ����ǰ��ȱ���**ȫ�������˵�ר����**�����ܳ���ҵר���������˵�ַҲ���Զ������ܲ���ʵ���з����ڵء�

## �����ļ�

results/��CSV��ֱ����Excel�򿪣�

| �ļ� | ���� |
|---|---|
| papers_HK_SG.csv | ����������ϸ��������ID��������������ؼ��� |
| annual_summary.csv | ��ȡ��������ڿ�/������ܣ�article/review�ֿ� |
| conference_coverage.csv | Ŀ¼������ʶ���������ƥ��׼��״̬ |
| catalog_status.csv | ��������Ȳɼ��ɹ�/ʧ��/δ�ٰ�״̬ |
| review_queue.csv | ȱժҪ��ͬ�����塢δƥ��Ŀ¼��¼ |
| patents_raw.csv | ��Pythonִ��BigQueryʱ���ɵ�ԭʼר����ϸ |
| patents_annual.csv | ר�������ͳ�� |
| patent_assignees_to_classify.csv | ��ҵ/��ѧ/�����������๤���� |

annual_summary�������ʶ��ķǿ��飻���в��Զ������㡣����ֻͳ�Ƹ�ƪ�������б��ػ���������ID�����ܰ�ȫ�����������������˲š����ڿ�������������ֱ����ӡ���ȱ��ݲ�����������������򼾶��˲�ָ������ϸ�ɹ��������㡣����Ϊ�ɼ�ʱ���գ�������λȱʧ������0��

����������������߷�������ܲ�ͬ�������û����ꡢ�ڿ��÷����ꡣ���º������Ŀ������ظ���1ƪ���ϲ�����ʱ����ȥ�ء�

## �ٷ��������

- OpenAlex��֤��https://help.openalex.org/api/authentication/
- NeurIPS��https://proceedings.neurips.cc/
- ICML��https://proceedings.mlr.press/
- ICLR��https://proceedings.iclr.cc/ ��https://openreview.net/venue?id=ICLR.cc
- CVPR/ICCV��https://openaccess.thecvf.com/
- ECCV��https://www.ecva.net/papers.php
- ACL/EMNLP��https://aclanthology.org/
- AAAI��https://ojs.aaai.org/index.php/AAAI/issue/archive
- IJCAI��https://www.ijcai.org/all_proceedings
- Patents��https://console.cloud.google.com/marketplace/product/google_patents_public_datasets/google-patents-public-data
