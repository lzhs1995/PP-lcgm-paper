"""生成网页复核材料；原文件只读，不估计模型，不上传。"""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, re, shutil, zipfile
import xml.etree.ElementTree as ET
import fitz

OUT = Path('C:/Users/LZHS/pp_lgcm_review/20261005')
PROJECT = Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis')
CODE = PROJECT/'work/cfps_review_20261005'
ROOT = OUT/'web_review_v45_v38'
A = ROOT/'01_current_review'
B = ROOT/'02_evidence'
NOW = datetime.now(timezone.utc).isoformat()
LIMIT = 25_000_000
COPY_LOG = []
CHECKS = []
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def readj(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def csvrows(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8', newline='\n')
def writej(p, obj): write(p, json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def writecsv(p, rows, fields=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def copy(src, dst, category):
    src=Path(src); dst.parent.mkdir(parents=True, exist_ok=True)
    before=sha(src);shutil.copy2(src,dst);assert sha(dst)==before
    COPY_LOG.append({'source':str(src),'destination':dst.relative_to(ROOT).as_posix(),'bytes':dst.stat().st_size,'sha256':before,'category':category})

def make_manifest(base):
    rows=[]
    for p in sorted(base.rglob('*')):
        if p.is_file() and p.name!='MANIFEST.csv':
            rows.append({'relative_path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    writecsv(base/'MANIFEST.csv',rows)
    return rows

assert not ROOT.exists(), '不覆盖既有交付目录'
ROOT.mkdir();A.mkdir();B.mkdir()
final=readj(OUT/'final_delivery_validation.json')
state=readj(OUT/'state.json')
assert state['main_version']=='v45' and state['appendix_version']=='v38'
assert state['manuscript_release'] is False
baseline=readj(OUT/'baseline_manifest.json')['files']
for r in baseline: assert sha(r['path'])==r['sha256']
archive=OUT/'LGCM_audit_stage1_20261005.zip'
assert sha(archive)==final['zip_sha256']

# 从已冻结的旧ZIP读取，保留当时的版本与说明。
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for info in z.infolist():
        if info.is_dir():continue
        rel=Path(info.filename)
        assert not rel.is_absolute() and '..' not in rel.parts
        dest=B/'historical_snapshot'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        with z.open(info) as src, dest.open('wb') as dst:shutil.copyfileobj(src,dst)
    for row in csvrows(B/'historical_snapshot/manifest.csv'):
        assert sha(B/'historical_snapshot'/row['relative_path'])==row['sha256']
CHECKS.append('旧ZIP所有条目CRC和内部清单SHA256通过，历史快照原样保留')

# 最新文稿与原始对照稿，不更改Word内容。
documents={}
for role, entry in zip(['main','appendix'],final['final_documents']):
    for ext in ['docx','pdf']:
        src=Path(entry[ext]); assert sha(src)==entry[ext+'_sha256']
        dst=A/'current_manuscript'/src.name;copy(src,dst,'current_manuscript')
        documents[(role,ext)]=dst
original=Path('C:/Users/LZHS/OneDrive/20251026 PP-LGCM整合/20260214 附件')
for name in ['20260214 代际亲近度对老年心理健康的影响——基于家内差异的视角.docx','20260214 Appendix.docx']:
    copy(original/name,A/'original_20260214'/name,'original_comparison_only')
for p in sorted((OUT/'summaries').iterdir()):
    if p.is_file() and p.suffix in ['.csv','.json']:copy(p,A/'summaries'/p.name,'aggregate_only')
for name in ['Astra_LGCM_Audit_Package_Instructions..md','给astra的打包清单_v2..md']:
    copy(OUT/'source_evidence'/name,A/'review_requests'/name,'original_instructions')
for name in ['change_log.csv','v44_change_log.csv','v45_v38_change_log.csv']:
    copy(OUT/'manuscript'/name,A/'change_logs'/name,'historical_edit_log')

# 后续脚本与回执独立存放，禁止冒充旧执行快照。
script_rows=[]
for p in sorted(CODE.iterdir()):
    if p.is_file() and p.suffix.lower() in ['.r','.py']:
        dst=B/'post_snapshot_updates/scripts'/p.name;copy(p,dst,'current_script_snapshot')
        old=B/'historical_snapshot/review_scripts'/p.name
        script_rows.append({'script':p.name,'current_sha256':sha(p),'old_snapshot_sha256':sha(old) if old.exists() else '', 'relation':'unchanged' if old.exists() and sha(old)==sha(p) else ('changed_since_snapshot' if old.exists() else 'not_in_old_snapshot'),'meaning':'当前代码快照；是否执行须查相应回执'})
writecsv(B/'post_snapshot_updates/script_versions.csv',script_rows)
for name in ['EXECUTION_REPORT.md','OPINION_DECISIONS.md','opinion_decisions.csv','state.json','final_delivery_validation.json']:
    copy(OUT/name,B/'post_snapshot_updates/receipts'/name,'final_receipt')
for name in ['final_pdf_receipt.json','v44_assembly_receipt.json','v45_v38_assembly_receipt.json','pdf_local_validation.json']:
    copy(OUT/'manuscript'/name,B/'post_snapshot_updates/receipts'/name,'manuscript_receipt')
for name in ['v43_disposition.md','v44_disposition.md','review_disposition.json']:
    copy(OUT/'reviews'/name,B/'prior_reviews_read_after_independent_review'/name,'prior_review')
for name in ['adjudication.json','source_manifest.json','pass1_full_concise/result.json','pass2_full_concise/result.json','pass3_full_concise/result.json']:
    copy(OUT/'reviews/v45_v38'/name,B/'prior_reviews_read_after_independent_review/v45_v38'/name,'prior_review')

# 将汇总中的真实输出路径接回包内；补齐旧包缺少的得分来源。
output_hash_map={sha(p):p for p in (B/'historical_snapshot/mplus').rglob('*.out')}
reference_rows=[]
extra=[]
for f in sorted((OUT/'summaries').glob('*.csv')):
    for rowno,r in enumerate(csvrows(f),2):
        for field in ['source','output']:
            source=r.get(field,'')
            if not source or not source.lower().endswith('.out'):continue
            p=Path(source)
            if not p.exists():
                reference_rows.append({'summary':f.name,'csv_row':rowno,'field':field,'source':source,'sha256':'','package_path':'','status':'SOURCE_NOT_FOUND'});continue
            h=sha(p)
            expected=r.get('source_sha256') or r.get('sha256')
            assert not expected or expected==h, (f,rowno,'源哈希不一致')
            if h not in output_hash_map:
                dest=B/'post_snapshot_updates/additional_score_sources'/h[:12]/p.name
                copy(p,dest,'additional_full_output')
                inp=p.with_suffix('.inp')
                if inp.exists():copy(inp,dest.with_suffix('.inp'),'additional_input')
                extra.append({'output':dest.relative_to(B).as_posix(),'sha256':h,'input_present':inp.exists(),'source':str(p)})
                output_hash_map[h]=dest
            reference_rows.append({'summary':f.name,'csv_row':rowno,'field':field,'source':source,'sha256':h,'package_path':output_hash_map[h].relative_to(B).as_posix(),'status':'PRESENT'})
assert all(r['status']=='PRESENT' for r in reference_rows)
writecsv(B/'summary_output_crosswalk.csv',reference_rows)
writecsv(B/'post_snapshot_updates/additional_sources.csv',extra)

# PDF按物理页抽取文本；Word段落只作定位，PDF/DOCX仍为版式与公式权威。
paras={};pdfpages={}
for role in ['main','appendix']:
    with zipfile.ZipFile(documents[(role,'docx')]) as z:
        tree=ET.fromstring(z.read('word/document.xml'))
        paras[role]=[''.join(t.text or '' for t in p.findall('.//w:t',NS)) for p in tree.findall('.//w:p',NS)]
    with fitz.open(documents[(role,'pdf')]) as pdf:
        pdfpages[role]=[page.get_text(sort=True) for page in pdf]
    text='PDF文本辅助检索，按物理页计数；图片、公式、表格请以原PDF/DOCX核对。\n\n'
    text+='\n\n'.join('===== PDF PAGE '+str(i+1)+' =====\n'+t for i,t in enumerate(pdfpages[role]))
    write(A/'searchable_text'/f'{role}_pdf_text.txt',text)

# 19个问题的当前处置与定位，不沿用旧candidate字样当作最终状态。
items=[
('1a','趋势与时间单位','部分解决','实际载荷及预测均值已核对；旧−0.218不再用于当前推断。','自由形状与线性模型选择证据有分歧，不能按显著性选模型。','先核对0/10锚点和当前均值，再裁定保留自由形状的理由。','main',1016,['growth_parameter_audit.csv','growth_predicted_means.csv','growth_fit_audit.csv']),
('1b','窗口敏感性','部分解决','已执行8个规格；3可审阅、3不可接受、2未收敛。','未证明跨窗口稳健；未补估4项核心调节。','先处理CESD8五期基准负方差，再决定必要核心关系与调节窗口检验。','main',1016,['sensitivity_current_status.csv','sensitivity_parameters.csv','sensitivity_fit.csv']),
('1c','样本与追访构成','部分解决','T7已汇总有效波数、死亡与未知边界；2225/1981/3274分开报告。','未识别样本选择对轨迹的因果贡献。','判断现有描述是否足够，必要时指定少量选择性追访敏感性。','appendix',18111,['T7_observed_waves.csv','T7_missing_patterns.csv','T7_mortality_counts.csv']),
('1d','2016长短版','部分解决','已报告额外12题推断版本的描述比较。','官方分配标记未找到，不能宣称随机分配检验已完成。','裁定非官方分类证据能支持的解释范围。','appendix',18110,['T2_2016_form_comparison.csv','T2_classification.json']),
('2a','CESD8计分','计分核验已解决','共同8题方向与完整作答规则已核对；两口径逐人恒差8，缺失模式一致。','不代表纵向测量不变性成立。','核查T3/T4与正文量尺说明是否一致。','main',65,['T3_item_means.csv','T4_scale_identity.csv','measurement_validation.csv']),
('2b','CESD20sc来源及量尺','计分核验已解决','2012实际20题；后期官方等化分减20；2016完整长卷5304人逐人一致。','等化分不是独立20题测量；理论20—80与样本实际范围20—72须区分。','核对官方文件与重建规则，勿将等化敏感性视独立测量验证。','appendix',18109,['CESD20_scale_validation.json','T1_wave_scale_sample.csv']),
('3a','方差不显著的含义','概念修订完成','不以方差显著性作为后续回归准入；当前CESD8方差已更新。','未完成同样本同尺度四步模型链；不能用单位转换解释显著性变化。','核对总方差/条件残差方差及模型结构差异。','main',1015,['growth_parameter_audit.csv']),
('3b','负方差与识别','未解决','保留旧诊断及本轮负方差证据。','CESD8五期直接模型SY残差负方差，不能直接追加交互。','提出有理论依据、预先限定的诊断顺序与停止条件。','appendix',18115,['sensitivity_current_status.csv','sensitivity_all_attempts.csv']),
('4a','拟合评价','部分解决','已报告增值拟合与绝对拟合指标分歧。','尚未完成必要残差结构替代及基准模型修复。','先诊断基础轨迹和同期残差，再决定少量替代设定。','appendix',18116,['growth_fit_audit.csv','sensitivity_fit.csv']),
('4b','修正指数与拟合诊断','限制已记录','保留RESIDUAL与失败信息，不靠降低阈值或逐条加路径达标。','插补模型不提供修正指数；残差诊断不能由这一限制免除。','限定使用实际可得诊断，不平均修正指数。','appendix',18115,['sensitivity_fit.csv','sensitivity_current_status.csv']),
('5a','过度概括与弱证据','文字修订完成，待独立复核','收缩假设及路径表述，弱证据列为探索性；撤回天花板必然保守。','文字修订不使历史估计自动成为修正数据的正式结果。','逐段核查是否仍有因果、阈值、全套稳健或普遍显著的残留概括。','main',2745,['sensitivity_parameters.csv']),
('5b','性别差与指标标签','文字修订完成，待独立复核','区分儿子相对女儿的差值与单方效应；最新排行标签按来源修正。','不能从相对差值分辨儿子上升或女儿下降。','核对表4.5.5/4.5.6、Sibling4长子及老小/幼子附加模型。','main',2734,[]),
('6a','参照文献方法','证据不足','明确不能仅凭乘积指标法一词认定与本研究相同XWITH/LMS实现。','作者实际语法与部分全文/代码配对未确认。','区分方法类别与实际估计器；不推断作者造假。','main',104,[]),
('6b','因子得分不确定性','部分解决','已汇总可得SE与得分分布，说明两阶段近似。','未做全流程家庭bootstrap、完整误差传播或保证无偏。','优先判断得分质量与模型目标；限定必要误差传播检验。','main',1186,['T6_score_precision.csv','T6_score_cutpoints.csv']),
('6c','连续与二分调节','部分解决','已报告切点、等值人数、不等大分组与交叉表。','不能解释为已确认阈值；连续与二分并非相同假设。','同时评价连续结果，二分保留探索性质，勿按显著性择优。','main',1186,['T5_baseline_relationship.csv','T6_score_cutpoints.csv','T6_observed_score_crosstabs.csv']),
('6d','三过程失败定位','证据不足','输入格式拒绝、估计未收敛、不可接受解已区分。','尚无同时满足原语法、完整输出与先后顺序的最简/最后ML与Bayes失败对。','按单过程→三过程无交互→单交互定位；缺项不得补造。','main',104,['sensitivity_all_attempts.csv']),
('6e','多重插补合并与LRT','未解决','保留25项比较与候选D2的证据边界；不平均P值。','精确配对、嵌套、自由度、必要协方差及正式合并推断未齐备。','判断可否用正确合并的单交互系数推断；联合检验须补齐适用条件。','appendix',18119,[]),
('7a','H4.2b判定','文字修订完成，统计仍开放','保留原方向，明确未获一致支持；不比较组内星号。','正式三阶交互/组间差异检验仍依赖MI及协方差证据。','分别检验教育、城乡、收入差异，明确未预期结果为探索性。','main',2734,[]),
('7b','机制解释','文字修订完成，待独立复核','未测量机制作为理论解释，撤回已验证的文化归因。','未识别生活理性、情感转向等中介机制。','检查讨论是否仍将理论故事写成已验证机制。','main',2745,[]),
]
assert len(items)==19
matrix=[];excerpts=[]
compact=lambda t:re.sub(r'\s+','',t)
for ident,title,status,done,open_,next_,role,index,evidence in items:
    text=paras[role][index];assert text
    prefix=compact(text)[:32]
    pages=[str(i+1) for i,t in enumerate(pdfpages[role]) if prefix in compact(t)]
    loc=f'{role}: XML p0={index}; PDF物理页='+(','.join(pages) if pages else '见段落摘录，未自动匹配')
    refs=['01_current_review/summaries/'+name for name in evidence]
    for name in evidence:assert (A/'summaries'/name).exists()
    if ident in ['5b']:refs+=['02_evidence/historical_snapshot/existing_evidence/table455456/REPORT.md','01_current_review/change_logs/v45_v38_change_log.csv']
    if ident in ['6a','6d']:refs+=['02_evidence/historical_snapshot/pending_actions.md']
    if ident in ['6e','7a']:refs+=['02_evidence/historical_snapshot/source_evidence/existing_LRT_D2_candidates.csv']
    matrix.append({'issue_id':ident,'issue':title,'status':status,'completed':done,'open':open_,'next_review_question':next_,'manuscript_location':loc,'evidence_paths':';'.join(refs)})
    excerpts.append({'issue_id':ident,'document':role,'paragraph_index_zero_based':index,'pdf_physical_pages':','.join(pages),'text':text})
writecsv(A/'19项问题_证据与稿件对应.csv',matrix)
writecsv(A/'当前稿件定位摘录.csv',excerpts)

brief='''# PP-LGCM七项意见：执行结果与独立复核说明

截至本交付：CFPS全量复现及论文图表来源对应完成；后续意见核查、有限补验和正文v45/附录v38修订完成；科学采用仍开放。CHARLS按用户要求暂停。CESD8主分析、CESD20sc敏感性。

本次工作仅整理复核材料，没有重新估计模型或更改文稿。当前稿件同时包含历史结果、修正测量结果与本轮有限补验，不能视为整篇所有模型均已按修正数据通过验收。NOT_RELEASED标记保留。

## 七项问题的状态

| 问题 | 当前判断 | 已做与待做 |
|---|---|---|
| 1 趋势、时间、窗口 | 部分解决 | 载荷、预测均值及八规格已核查；跨窗口稳健性未成立，四核心调节窗口检验与测量不变性未完成。 |
| 2 CES-D计分 | 计分核验已解决 | CESD8恒差8；CESD20官方等化口径核清。不能因此声称跨期测量等价。 |
| 3 方差与精度 | 概念已修订，模型问题开放 | 不设显著性准入门槛；负方差和完整四步诊断仍待处理。 |
| 4 拟合 | 诊断与表述部分完成 | 报告指标分歧，基准模型及必要残差结构修复未完成。 |
| 5 过度表述 | 文字修订完成，待独立复核 | 收缩路径、弱证据、差值与机制解释；不保证全文已无残留过度表述。 |
| 6 调节与MI | 关键统计问题未解决 | 得分SE、切点和历史输出可追溯；完整模型诊断、误差传播、25项比较的正式MI合并仍开放。 |
| 7 H4.2b | 假设判定已修订，统计仍开放 | 原假设保留，未获一致支持；正式组间差异检验仍待证据补齐。 |

## 必须区分的新旧结果

旧稿−0.218不能继续作为当前五期抑郁变化结论。修正测量后原3274人自由形状模型的变化因子均值为0.037（SE=0.035，p=.284）；载荷依次0、6.590、11.594、3.266、10，模型预测均值约13.550、13.794、13.979、13.671、13.920。自由形状变化因子不等于恒定年变化率；同样本线性结果为0.054（SE=.011，p<.001），AIC与BIC的形状选择证据存在分歧。

本轮补验固定共同样本2225人，直接关联再限定原26协变量完整为1981人，不能替代3274人的MI主分析。8个科学规格产生12次引擎调用，4次是输入格式被拒后的保留尝试，不是12个科学模型。3个规格有不可接受的负方差，2个未收敛，3个可审阅但拟合仍有分歧；后三者变化相关路径的95%近似区间均跨零。没有新增四项核心交互。

2016年长短版比较来自额外12题的非官方推断，不是官方随机分配标记的验证。官方CESD20sc理论计分20—80；5304份完整长卷验证样本的实际观察范围20—72，不应混淆。减20后的统一0—60敏感性量尺也不构成独立20题测量验证。

## 两套网页意见的本地共识

保留五期研究问题并检查量尺、时间和样本；不用预期方向或显著性筛选结果；方差不显著不是后续回归禁入条件；拟合不能靠临时降阈值解决；因子得分与二分模型均需限定解释；MI不能平均P值；H4.2b须保留原预测并直接检验组间差异。

对于参照研究，原文写“乘积指标法”能支持方法类别的描述，但不能单独确认与本研究相同的XWITH/LMS、估计器、积分和约束。未确认作者实际代码时不作同算法或造假推断。两份原始附件收在review_requests；此处是本次整理的共识摘要，不冒充原网页完整对话。

## 请优先裁定

1. CESD8五期直接基准的负残差方差应如何诊断，哪些有限替代设定有理论依据？
2. 八规格目前究竟允许保留哪些关系结论，哪些只能列为历史或探索性？
3. 完整三过程潜交互、双过程加观测基期调节、连续得分近似分别应处于什么位置？
4. 25项MI比较应补齐哪些最小证据；能否先基于正确合并的单交互系数推断？
5. 当前稿件是否仍有越过证据边界的段落或表注？请给出确切位置。

不要求把七项全部判为解决。对缺项请明确说明“未找到”“未执行”或“证据不足”。先独立复核，再查包02中的既有NLM回执；其通过不代表统计科学放行。

## 逐项执行与证据
'''
for r in matrix:
    brief+=f"\n### {r['issue_id']} {r['issue']}：{r['status']}\n\n已做：{r['completed']}\n\n仍开放：{r['open']}\n\n复核重点：{r['next_review_question']}\n\n稿件位置：{r['manuscript_location']}。证据：{'；'.join(r['evidence_paths'].split(';')) or '当前稿件定位摘录.csv及包02缺项清单'}。\n"
write(A/'七项意见_逐条答复.md',brief)

# 当前8规格直接从已有汇总读回，补充每份完整输出和TXT定位。
sens=csvrows(OUT/'summaries/sensitivity_current_status.csv')
for r in sens:
    r['package_output']='02_evidence/'+output_hash_map[r['sha256']].relative_to(B).as_posix()
writecsv(A/'八规格_状态与完整输出.csv',sens)

# 对原语法/输出/R提供逐字节TXT镜像，保留哈希等价性。
mirror_rows=[]
original_texts=[p for p in sorted(B.rglob('*')) if p.is_file() and p.suffix.lower() in ['.inp','.out','.r']]
for p in original_texts:
    rel=p.relative_to(B)
    dest=B/'web_txt'/Path(str(rel)+'.txt')
    copy(p,dest,'byte_identical_txt_mirror')
    mirror_rows.append({'original':rel.as_posix(),'txt':dest.relative_to(B).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
writecsv(B/'TXT_MIRRORS.csv',mirror_rows)

# 提供小型优先证据读本，完整字节仍以原文件/TXT镜像为准。
reader='''优先核查读本：以下按明确边界串联完整输入/输出，不含个体数据。\n解码仅用于阅读；SHA256针对原字节。表格排版/编码有疑问请核对原文件。\n\n'''
reader+='一、8个预定规格，含全部失败尝试\n'
all_attempts=csvrows(OUT/'summaries/sensitivity_all_attempts.csv')
reader_sources=[]
for r in all_attempts:
    h=r.get('sha256','')
    if h in output_hash_map and output_hash_map[h] not in reader_sources:reader_sources.append(output_hash_map[h])
for r in extra:
    p=B/r['output']
    if p not in reader_sources:reader_sources.append(p)
for p in reader_sources:
    for q in [p.with_suffix('.inp'),p]:
        if q.exists():
            raw=q.read_bytes()
            for enc in ['utf-8-sig','gb18030','cp1252']:
                try:text=raw.decode(enc);break
                except UnicodeDecodeError:continue
            else:raise ValueError('无法解码 '+str(q))
            reader+=f'\n===== BEGIN FILE: {q.relative_to(B).as_posix()} ; SHA256={sha(q)} =====\n'+text+f'\n===== END FILE: {q.name} =====\n'
write(A/'优先证据_八规格与得分来源.txt',reader)
assert len(reader_sources)==18, ('期望12次尝试及6份得分输出',len(reader_sources))

prompt='''请对《代际亲近度对老年心理健康的影响——基于家内差异的视角》做独立方法复核。当前审阅对象是正文v45和附录v38（NOT_RELEASED），20260214原稿仅用于对照。不要把旧版本缺陷自动归到最新版，也不要因已有执行报告或NLM肯定就认定问题已解决。

背景：CFPS全量复现与论文图表来源对应已完成。随后完成七项意见的本地核查、有限补验和文稿修订；统计科学采用仍开放。CESD8主分析，CESD20sc敏感性；CHARLS暂停。材料没有个体数据，因此你可以复核代码/输入输出/汇总和推断逻辑，但不能声称独立重算了个人记录。

先列出实际可读取的文件与版本。阅读“七项意见_逐条答复.md”“19项问题_证据与稿件对应.csv”、最新两个PDF及八规格汇总。需要更多证据时，按包02索引要求我上传对应的TXT或文件。若网页端不能解压ZIP，请明确说明并等待指定材料，不得假装读过。不要要求立即上传CFPS原始库。

核查七项：1趋势/时间/窗口/样本；2 CESD计分与等化来源；3增长因子方差与精度；4拟合与残差结构；5过度表述；6调节、因子得分、二分与MI合并；7 H4.2b与正式组间差异检验。

关键事实须独立查证：当前原3274人CESD8自由形状均值0.037(SE=.035,p=.284)，载荷0/6.590/11.594/3.266/10；旧−0.218不再适用。共同样本2225、完整协变量子样本1981与3274人MI主分析不同。本轮8规格、12次引擎调用（含4次输入格式拒绝），3不可接受、2未收敛、3可审阅但拟合有分歧；四核心交互未新增。2016版本为非官方推断。得分误差没有完整传播。25项MI比较精确配对/合并仍开放，候选D2不是正式采用结果。不能平均P值，不能比较两组星号代替差异检验。原文“乘积指标法”不能独自证明完全相同的XWITH/LMS实现。

请输出：
1. 七项逐条“已解决/部分解决/未解决/证据不足”，分别评价文字修订与统计实质。
2. 每条提供当前稿件位置、实际证据文件/模型/行段；指出已读取与缺失材料。对本地报告持不同意见时说明理由。
3. 仍然存在的错误或过度表述，给可直接替换的文字，并标明该文字是否依赖新估计。
4. 最小必要后续清单：优先级、要回答的问题、已有可复用材料、必要输入、验收/停止条件。先处理基准负方差与MI推断，不按显著性探索大量模型。
5. 分别判断哪些结果可进入主文、哪些仅能探索性/附录报告、哪些应暂缓；完整三过程、两过程加观测基期调节、连续得分近似与二分不是可无损互换的同一估计对象。

保持原假设和真实数据，不以“必须上升/显著”为目标。不推断参考作者造假。先形成独立结论，再按需查阅prior_reviews_read_after_independent_review下的既有NLM回执。
'''
for platform in ['ChatGPT-Pro','Claude']:
    write(A/f'给{platform}_复核提示词.txt',prompt)
    copy(A/f'给{platform}_复核提示词.txt',ROOT/f'给{platform}_复核提示词.txt','upload_shortcut')

write(B/'README.md','''# 完整证据与代码：第二包

当前稿件为正文v45/附录v38。historical_snapshot来自原7,108,834字节审计ZIP，内部README/意见状态/脚本保持打包时原样（v43/v37语境），不得覆盖后声称一直是最新版。post_snapshot_updates存放后续当前脚本、最终回执，以及本次补齐的6份得分来源完整输出/语法。

按论文表查historical_snapshot/model_index.csv（747条来源记录，不是747个独立模型）；按完整文件查ALL_OUTPUTS.csv；按汇总源查summary_output_crosswalk.csv。旧model_details.csv是较早自动解析表，其normal_marker/input_error等字段可能误读MI汇总或警告内容，不是最终诊断结论；结合convergence_inventory_final.csv、完整输出与最新敏感性终态判断。没有把所有旧模型重新诊断或升级为正式采用。

web_txt提供每份.inp/.out/.R的逐字节TXT镜像，TXT_MIRRORS.csv给出配对及哈希。源文件同名时必须保留目录或使用哈希定位。最新脚本快照不等于曾以该版本执行的证明；script_versions.csv保留相对旧快照的变化，执行证据另见回执。

prior_reviews_read_after_independent_review只作独立判断后的参考，不预设审阅者同意NLM。未包括登录、网络认证原始回执。

本包为代码/输出/汇总审计材料，不包含实际.dat、逐人得分、插补RDS或ID映射。语法保留本机路径及数据变量名，DATA/SAVEDATA引用不是附带数据，不能称为云端一键可重跑工程。环境信息是历史执行时记录，非本次重新连接RStudio取得；本次没有运行Mplus、升级软件或上传文件。
''')
allouts=[]
for h,p in sorted(output_hash_map.items()):
    allouts.append({'output_sha256':h,'model_key':h[:12],'output_path':p.relative_to(B).as_posix(),'input_path':p.with_suffix('.inp').relative_to(B).as_posix() if p.with_suffix('.inp').exists() else '', 'txt_path':'web_txt/'+p.relative_to(B).as_posix()+'.txt','evidence_layer':'additional_score_source' if 'additional_score_sources' in p.parts else 'frozen_audit_snapshot'})
writecsv(B/'ALL_OUTPUTS.csv',allouts)
assert len(allouts)==245
writej(B/'SNAPSHOT_PROVENANCE.json',{'original_zip':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size,'original_outputs':239,'additional_outputs':6,'total_unique_outputs':245,'timestamp_utc':NOW,'original_snapshot_unmodified':True,'new_model_runs':0})

readme='''# 阅读与上传说明

当前交付：正文v45、附录v38；第一批无个体数据复核材料。科研问题仍有开放项，详见“七项意见_逐条答复.md”。本次整理没有重估模型、修改稿件或上传到网页端。

## 推荐操作

1. 在本机解压两个ZIP，保持01_current_review与02_evidence目录同级。两个ZIP均可独立解压，每包不超过25,000,000字节。
2. 给ChatGPT-Pro、Claude各开一个新对话，粘贴对应“复核提示词.txt”；两端使用同一材料版本、同一判断标准。
3. 第一轮上传01_current_review内“七项意见_逐条答复.md”、current_manuscript下正文v45及附录v38两个PDF、“19项问题_证据与稿件对应.csv”。依据界面附件数量限制分批上传，不要求一次塞入全部材料。
4. 第二轮上传“八规格_状态与完整输出.csv”“优先证据_八规格与得分来源.txt”及审阅者需要的summaries文件。这里有全部12次本轮引擎尝试和6份得分来源的完整文本；不只呈现成功结果。
5. 深查既有交互/MI时，上传02_evidence中的ALL_OUTPUTS.csv、historical_snapshot/model_index.csv和相应web_txt文件。原始R较长，按原行号定位读取；单份TXT与原字节哈希一致。原始代码引用的本机数据路径不保证网页可运行。
6. 若需对照最初意见，上传review_requests下的两份原始附件，以及original_20260214下原稿；明确它们是历史版本。
7. 两端完成独立结论后，再按需提供02_evidence/prior_reviews_read_after_independent_review中的旧审阅回执。

如果网页不能解压ZIP，直接上传解压后的PDF、MD、CSV、TXT。current_manuscript中的DOCX用于精确核对Word表格/公式；searchable_text按PDF物理页提取，仅辅助搜索，不能替代原文版式。

## 材料定位

01_current_review：当前与原始稿件、19项答复、T1—T7/八规格汇总、稿件位置摘录、提示词和小型优先证据读本。
02_evidence：239份旧完整输出的冻结快照、补齐的6份得分输出、对应语法/代码、后续脚本与回执、全部输出/TXT索引。

旧包README中的v43/v37、旧意见表candidate字样属于历史时点；本次“七项意见_逐条答复.md”和当前v45/v38定位表说明最新处置。MANIFEST.csv覆盖各包内容，根目录DELIVERY_VALIDATION.json与SHA256SUMS.txt记录最终验证和压缩包哈希。

## 后续反馈格式

请将两端的七项判定、引用证据、替换文字与最小必要补验清单一并带回。结论冲突时先对齐版本/样本/量尺/模型，再判断方法差异。本地不预设全部问题必须判为解决。
'''
write(A/'00_阅读与上传说明.md',readme)
write(ROOT/'00_阅读与上传说明.md',readme)
write(A/'README.md','当前稿件、答复与汇总入口：00_阅读与上传说明.md。\nPDF/DOCX保持原字节，七项状态不是论文科学放行证明。\n')

# 引用、排除项与来源复核。
for r in matrix:
    for ref in filter(None,r['evidence_paths'].split(';')): assert (ROOT/ref).is_file(),ref
for r in sens:assert (ROOT/r['package_output']).is_file()
for r in reference_rows:assert (B/r['package_path']).is_file()
for r in mirror_rows:assert sha(B/r['original'])==sha(B/r['txt'])==r['sha256']
for r in COPY_LOG:assert sha(r['source'])==r['sha256'],r['source']
for r in baseline:assert sha(r['path'])==r['sha256']
# 避免仅依靠扩展名：额外检查CSV表头与高置信凭据赋值。
forbidden={'.dat','.rds','.rdata','.sav','.dta','.msi','.exe','.wbk','.fscores'}
credential=re.compile(r'(?i)(?:api[_-]?key|password|access[_-]?token)\s*[:=]\s*[\x22\x27][^\x22\x27\s]{8,}')
scan=[]
for base in [A,B]:
    for p in base.rglob('*'):
        if not p.is_file():continue
        assert p.suffix.lower() not in forbidden,p
        if p.suffix.lower() in {'.r','.py','.json','.inp','.out','.txt','.csv','.md'}:
            text=p.read_text(encoding='utf-8-sig',errors='replace')
            # 扫描器源代码包含正则定义，但不包含实际凭据。
            hits=credential.findall(text)
            if hits:scan.append({'file':p.relative_to(ROOT).as_posix(),'type':'credential_literal','count':len(hits)})
        if p.suffix.lower()=='.csv':
            rows=csvrows(p)
            if rows and set(k.lower() for k in rows[0]).intersection({'pid','fid','person_id','household_id','phone','address','email'}):
                scan.append({'file':p.relative_to(ROOT).as_posix(),'type':'individual_identifier_column'})
assert not scan,scan
writecsv(ROOT/'COPY_PROVENANCE.csv',COPY_LOG)
CHECKS.extend(['全部19项证据路径及汇总输出引用存在','245份唯一完整输出已建索引；6份追加来源均有对应输入','TXT镜像逐字节等同原文件','原稿/脚本等12个基线文件哈希未变','白名单、敏感扩展、CSV个人标识列和凭据赋值检查通过'])

packages=[]
for base,zipname in [(A,'01_当前稿与七项答复.zip'),(B,'02_完整输出与代码.zip')]:
    rows=make_manifest(base)
    zp=ROOT/zipname
    with zipfile.ZipFile(zp,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(base.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(ROOT).as_posix())
    assert zp.stat().st_size<=LIMIT,(zp,zp.stat().st_size)
    with zipfile.ZipFile(zp) as z:
        assert z.testzip() is None
        for r in rows:
            with z.open(base.name+'/'+r['relative_path']) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
    packages.append({'file':zp.name,'bytes':zp.stat().st_size,'sha256':sha(zp),'files':len(rows)+1,'crc_and_entry_sha256':'PASS','limit_bytes':LIMIT})
write(ROOT/'SHA256SUMS.txt','\n'.join(p['sha256']+'  '+p['file'] for p in packages)+'\n')
writecsv(ROOT/'PACKAGE_MANIFEST.csv',packages)
receipt={'status':'PASS','created_at_utc':NOW,'current_main':'v45','current_appendix':'v38','packages':packages,'issues':19,'original_outputs':239,'additional_score_outputs':len(extra),'unique_outputs':len(allouts),'summary_reference_count':len(reference_rows),'txt_mirrors':len(mirror_rows),'checks':CHECKS,'individual_data_included':False,'manuscript_modified':False,'new_mplus_runs':0,'uploaded':False,'scientific_release':False,'cfps_historical_reproduction':'COMPLETE','charls':'PAUSED_BY_USER'}
writej(ROOT/'DELIVERY_VALIDATION.json',receipt)
print(json.dumps(receipt,ensure_ascii=False,indent=2))
