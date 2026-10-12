"""以已核验终态生成在线可读报告和模型索引；不填补缺失估计。"""
from pathlib import Path
import json
import pandas as pd
from document_support import number as fmt, pvalue, interval
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def md(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v).replace('\n','<br>') for v in r)+' |' for r in rows])
def save(name,s):(ROOT/'reports'/name).write_text(s,encoding='utf-8')
def main():
 R=ROOT/'reports';S=read(ROOT/'runtime/selection_2f.json');A=read(R/'SUMMARY.json');V=read(ROOT/'audit/independent/independent_verification.json')
 assert V['status']=='PASS' and A['terminal']['status'] in ['FINISHED','STOPPED_WITH_REASON']
 D=read(ROOT/'manuscript/delivery/manuscript_validation.json')
 visual=read(ROOT/'manuscript/delivery/visual_review.json')
 assert D['status']=='PASS' and visual['status']=='PASS'
 calls=pd.read_csv(R/'CALLS.csv');dc=pd.read_csv(R/'DIAGNOSTIC_PARAMETERS.csv');cmp=pd.read_csv(R/'NUMERIC_PATH_COMPARISONS.csv')
 fam=A['families'];complete=[k for k,v in fam.items() if v['status']=='COMPLETE_10_USABLE'];decision=A['decision'];t=A['timing']
 power=read(ROOT/'audit/SYSTEM_POWER_EVENTS_2F.json')
 power_note=(f"电源日志查询窗口为{power['start_utc']}至{power['end_utc']}，取得{len(power['events'])}条记录。"
  '本轮记录包含两次506（进入新型待机）和一次507（退出）；没有42/107事件。所有引擎回执均无超过阈值的轮询间隙且无超时，'
  '但新型待机事件本身不能等同于CPU停止，未配对的506也不能据此换算暂停时长。保持唤醒请求不保证没有此类事件；墙钟均照实计入。')
 if not complete:headline='本轮没有形成通过预定验收的SD调节十份MI；SW和SD E0继续保留。'
 elif 'E1' in complete:headline='自由SD E1已完成十份MI；是否支持调节以条件区间和固定四项Holm结果为准。'
 else:headline='仅SD E1B形成十份MI，作为SY条件残差固定零的强约束敏感性；没有自由残差调节推断。'
 nrows=[]
 for _,r in calls[(calls['sample']=='CFPS')&(calls.category=='NUMERIC')].iterrows():
  nrows.append([r.id.replace('CFPS_SD_',''),int(r.points),r.status,fmt(r.LL),fmt(r.sy,6),fmt(r.get('dc')),
     fmt(r.get('dc_SE')),fmt(r.exact_LL_difference,6)])
 f1=S.get('F1',{});f2=S.get('F2',{})
 pair=[]
 for step in ['F1','F2']:
  for key,label in [('start_check','30点双起点'),('integration_a','a来源20→30'),('integration_b','b来源20→30')]:
   c=S.get(step,{}).get(key,{})
   pair.append([step,label,c.get('outcome','未执行'),fmt(c.get('delta_LL'),6),fmt(c.get('max_path_over_SE'),6),fmt(c.get('max_SE_relative'),6)])
 detail=''
 f1rows=cmp[(cmp.step=='F1')&(cmp['mode']=='start')&(cmp.scope=='prespecified key path')]
 if len(f1rows):
  worst=f1rows.loc[(f1rows.absolute_change/f1rows.path_tolerance).idxmax()]
  delta=f1rows[f1rows.label=='dc'].iloc[0]
  bss=f1rows[f1rows.label=='bss'].iloc[0]
  detail=(f"E1B双起点：δ相差{fmt(delta.absolute_change,8)}，冻结容差为{fmt(delta.path_tolerance,8)}；"
   f"bss相差{fmt(bss.absolute_change,8)}，容差为{fmt(bss.path_tolerance,8)}。"
   f"最大目标路径差为{fmt(f1rows.change_over_high_precision_SE.max(),6)}个SE，最大SE相对差为{fmt(f1rows.SE_relative.max(),6)}。"
   f"这些差异需要与预定门槛一起呈现，不能只写“LL一致”，也不能将小差异夸大为已证明模型在理论上不可识别。\n")
 fixed=calls[(calls['sample']=='CFPS')&((calls.attempt=='F5')|(calls.id=='CFPS_SD_E1B_01_F1_q30b'))]
 fx=[]
 for _,r in fixed.iterrows():
  slope=[]
  for p in ['raw_zero','positive_median','P90']:
   d=dc[(dc.id==r.id)&(dc.label==p)]
   slope.append(fmt(d.iloc[0]['estimate'])+' ('+fmt(d.iloc[0]['se'])+')' if len(d) else '—')
  fx.append([fmt(r.sy),r.status,fmt(r.LL),fmt(r.get('dc'))+' ('+fmt(r.get('dc_SE'))+')',*slope])
 e0=pd.read_csv(ROOT/'baseline/results/POOLED_KEY_PATHS.csv')
 e0table=md(['路径','估计','SE','条件95%区间'],[[r.label,fmt(r.estimate,4),fmt(r.se,4),interval(r)] for _,r in e0.iterrows()])
 cc=calls[(calls['sample']=='CFPS')&(calls.data_tag=='CC')]
 cc_note=''
 if any(cc.output_diagnosis=='STANDARD_ERRORS_UNAVAILABLE'):
  cc_note=('**完整控制E0已实际执行，但没有可用标准误。** Mplus在“正常终止”之后明确警告标准误无法计算、模型可能未识别；'
   '首先指出参数126（SX），条件数−0.280×10⁻⁶，并列出其他相关参数。没有生成estimates.dat，TECH3为零字节，'
   '程序因此记录`EXTRACTION_FAILED`及`cannot open the connection`。原始回执保持不变，'
   '补充诊断见[OUTPUT_DIAGNOSTICS.md](OUTPUT_DIAGNOSTICS.md)。这不是未执行，也不是上传损坏，不能据此声明敏感性通过；'
   'Mplus的“可能未识别”警告也不等于已经证明总体结构不可识别。\n')
 status=md(['核查','比较','结果','打印LL差','最大路径差/SE','最大SE相对差'],pair)
 report=f'''# Round2F本机执行报告：SD数值核查与敏感性

{headline} 本轮按冻结合同得到决定 **{decision}**；队列终态为 `{A['terminal']['status']}`。这是本批执行终态，不表示七项研究问题全部解决。

## 1. 本轮确实完成了什么

本轮沿用Round2E已验证的SD样本（3274人、2410户）、24项控制、CESD8、SW两过程结构和十份家庭—个人MI。新增 **{t['calls']}次真实Mplus调用**，其中合成接口{t['sample_counts'].get('SYNTHETIC',0)}次、CFPS{t['sample_counts'].get('CFPS',0)}次。未重新计分、清洗、插补，也未启动H4、其他差异分支或潜IZ长队列。

数据和来源哈希核验、完整控制样本准备、精确LL校准、三次真实合成检查、SD自由/固定模型的20/30点双起点检查、合同内正残差固定点及完整控制诊断均有实际回执。哪些诊断未准入见第4节。原始附件与本机方案取舍见[CONSENSUS.md](CONSENSUS.md)；实际15个执行源及合同的冻结清单见contracts目录，执行后未更改。

引擎实际墙钟合计 **{t['engine_wall_seconds']:.2f}秒**（{t['engine_wall_seconds']/60:.2f}分钟），累计进程CPU **{t['cpu_seconds']:.2f}秒**，从批次开始到队列终态约 **{t['batch_wall_seconds']:.0f}秒**（{t['batch_wall_seconds']/60:.2f}分钟）。终态时间戳只精确到秒；冻结程序的末次引擎账本快照为{t['budget_snapshot_wall_seconds']:.2f}秒，尚不含其后读回与队列收尾，两种时间分别保留。上限分别为39次、10800秒引擎墙钟和14400秒批次墙钟。没有用剩余额度开启新的科学规格。系统电源事件和每次CPU/墙钟另存；轮询间隙不作为待机扣账。所有已执行调用的保持唤醒请求均为 `{t['all_actual_calls_keep_awake']}`，不能由此声称绝不会发生系统暂停。

{power_note}

## 2. 自由残差与固定零模型的比较

下表均为MI01单次结果。`USABLE`仅表示该次通过基本合法性检查；`INADMISSIBLE_SY_ONLY`仍是不合法的潜变量残差分解。两类结果都不能绕过双起点和完整家族要求。

{md(['规格 / 起点','积分点','单次状态','打印LL','SY残差','δ','SE','精确LL−打印LL'],nrows)}

a来源是Round2E已合法的E1B，b来源是同份合法E0，全部共同自由参数按语义映射。自由E1从a来源释放SY时明示正初值0.02，不把负方差剪裁成合法来源。全部LMS使用绝对变化准则10⁻⁵、相对变化准则10⁻⁹。

{status}

{detail}
F1总准入：`{f1.get('passed')}`；F2总准入：`{f2.get('passed')}`。决定只依合法性、数值容差与预算，不依δ的方向或P值。若自由模型仍有负残差，就只能作诊断；固定零模型即使每次合法，也须通过双起点核查。

20→30点通过说明本次积分比较没有发现超容差变化；它不证明全局最优，也不排除更精细优化引起变化。当前接近的LL不能证明路径完全稳定。精确LL是在保存参数处用同一观测数据重新计算；它核对条件高斯似然和映射，不重新拟合，不验证稳健SE或分布假设。

## 3. 家族和MI结论

本轮完整采用的家族为：**{', '.join(complete) if complete else '无'}**。逐份状态见[results/FAMILY_STATUS_2F.csv](results/FAMILY_STATUS_2F.csv)。无完整家族时，合并表中的缺值是“没有估计”，不是δ=0、P=1或MI缺失信息率为0。没有删除失败成员，也没有把不同SY限制/积分点混成十份。

既有SD E0十份原始参数及TECH3再次独立合并，与Round2E报告一致：

{e0table}

可保留的结论：在该工作模型下，较高亲近度潜在基期与较低抑郁潜在基期相关；变化关联不精确。两条Z₀路径区间跨零、固定四项Holm P均为1.000，未获支持，但不能据此断言家内差异没有关联。E0没有交互，不能替代E1或H4。

E1B固定的是给定IX、SX、IY、Z₀、SX×Z₀及控制后的额外SY随机差异，不是SY总方差为零。固定子模型中的区间不包含选择这一限制的不确定性。gi0也不代表Z₀与实际基期Y的全部关联，因为保留y1对Z₀的直接路径；有交互时gs0是SX=0的条件路径。

## 4. 正残差与样本诊断

{md(['固定SY','单次状态','打印LL','δ (SE)','原始零b(z) (SE)','正值中位b(z) (SE)','P90 b(z) (SE)'],fx)}

0点展示预先区分的30点b来源候选，仍须遵守第2节准入失败/通过的结论。0.020/0.034/0.080在同一带交互E1结构下重估其他参数；0.034来自既有E0十份残差均值0.0339186401。所有这些均为单份诊断，不是方差置信区间，不是完整MI敏感性，不挑显著点。

在这三个正固定点之间，δ点估计从−0.2637变化到−0.2600，数值相近；但连同0点候选，原始零支持点的条件斜率从−0.439变为−0.267，SE从0.850变为0.438。可见残差限制会改变路径分解和不确定性，不能仅凭δ相近就宣布对限制不敏感。所有表列条件斜率的单份区间均较宽；正式推断仍受数值准入与十份MI要求限制。

完整控制样本为2830人、2105户，由九个原分析协变量的原始缺失掩码定义，不要求sat12完整。其实际调用见[CALLS.csv](CALLS.csv)和附表A13；不存在合格优先规格时，交互完整控制调用不启动。P99数据已准备（3.76636049455，改变32个Z₀值），但只有合格规格才拟合；数据准备不等于敏感性检验完成。当前完整控制交互与P99的状态须按附表A13/A25读取，不能写成未检出差异。

{cc_note}

完整控制会改变样本构成，P99会改变解释变量尾部；即使单份结果可用，也不能据此证明MI严格相容或测量误差只会衰减。旧C1无交互残差剖面不能替代本轮交互固定点。

## 5. 七项意见和稿件

{md(['问题','状态','证据范围'],pd.read_csv(R/'SEVEN_ISSUES.csv').values.tolist())}

正文v51、附录v43已按当前结果修订。H1.2/H1.4的假设判断与模型状态分开；性别差历史失败按信息矩阵病态、迭代停滞、叠加待机完整说明；默认EM剩余LL约0.01仅为外推，未写成已测得误差；Zhang等(2025a)按最远关系类型限定。SY限制、MI采用范围和gs0条件含义写入方法及结果说明。H4继续区分统计组间差异与原理论成分，不以任意绝对幅度支持“弱化更强”。

稿件保留原Word的{sum(d['fields'] for d in D['documents'])}个域、{sum(d['footnotes'] for d in D['documents'])}个脚注及除document.xml以外的全部ZIP部件。两版PDF共{sum(d['pages'] for d in D['documents'])}页、{sum(d['tables'] for d in D['documents'])}张表、{sum(d['cells'] for d in D['documents'])}个单元格，已完成原生Word导出、逐表逐格核验和页面视觉审阅。PDF提取的下划线错序通过同一单元格的字符坐标复读核实，仍要求整格完全一致；附表A22已加宽数值列防止末位数字换行。验证收据在manuscripts目录。它是本轮文档与数值一致性验收，不是全文终审、NLM三轮或所有文献全文复核。Zhang & Liu(2024) p.3871沿用既有本机核对记录，网页端独立页码核对仍未补齐。

## 6. 独立复核与公开范围

本轮独立程序直接解析原始Mplus参数、TECH1和TECH3，核对 **{V['calls']}次新调用、{V['free_parameters']}个自由参数、{V['printed_rows']}行打印参数、{V['matrices']}个适用矩阵、{V['full_start_slots_verified']}个起点槽**，并重新核验数值决定及预算。参数与矩阵计数覆盖14份有保存结果的调用；完整控制E0以原始严重警告和缺失/空保存文件核验，不伪造参数或协方差。另复算旧SD E0十份，不把它计为本轮新估计。具体结果见[audit/independent/independent_verification.json](audit/independent/independent_verification.json)。

本机原数据用于P0哈希、样本核对和保存参数处的精确LL校准；公开复核只读聚合参数。公开包不含微观data.dat、真实PID/FID、逐人收入/得分、MI对象或文献全文。因此网页端能够核验原始输出、协方差、起点映射和合并算术，不能据本包重新拟合CFPS或重算逐人似然。公开包里的exact_LL回执是本机证据，不能冒称云端已重新计算。

每包上限25,000,000字节，清单列出大小、SHA-256和逐文件校验值。上传后还会从固定提交匿名下载全部包并运行包内公开验证器；该步骤的最终回执与固定提交由交付消息说明。

## 7. 后续推进建议

先让网页端审阅这一新结果，避免重启Round2E或再次给旧潜IZ模型加时。本轮完成不以显著性为标准，也不以跑满39次为目标。

下一合同若继续数值工作，应只针对当前未通过的具体环节：区分小而实测的起点差异与实质不确定性，核对保存点的梯度/局部曲率，明确是否需要更严格的优化停止准则或独立条件高斯优化验证。须事前固定可检验门槛、少量调用及停止规则；不能看到δ后降低当前门槛。未获得合格MI家族前，不把H4接在后面。

结构层面的后续仍是SW的Y形状、窗口/量尺，以及其他差异分支各自的边界处置。它们可能改变研究操作化，需各自论证；SD的数值或P值不能作为其他分支的准入依据。暂不自动增加SX@0、二分、Bayes或全量重插补。
'''
 save('REPORT.md',report)
 links=[]
 for _,r in calls.iterrows():
  base='models/'+r.id
  parameter_links=[]
  for name,label in [('parameters_high_precision.csv','参数'),('tech3.dat','TECH3'),('receipt.json','回执')]:
   if (ROOT/base/name).exists():parameter_links.append('['+label+']('+base+'/'+name+')')
  if r.output_diagnosis=='STANDARD_ERRORS_UNAVAILABLE':parameter_links.insert(0,'标准误无法计算；TECH3为空')
  links.append([r.id,r['sample'],r.status,'[INP]('+base+'/model.inp.txt) / [OUT]('+base+'/model.out.txt)',
       ' / '.join(parameter_links)])
 save('MODEL_INDEX.md','# 全部实际Mplus调用索引\n\nUSABLE只表示单次合法；完整家族与数值决定见REPORT。合成调用不计为CFPS研究发现。\n\n'+md(['调用','样本','单次状态','原始输入输出','参数与证据'],links)+'\n\n旧SD E0十份与历史对照见baseline目录；合法起点原件见upstream/START_SOURCES.json。\n')
 save('README.md',f'''# PP-LGCM Round2F：SD数值核查与敏感性（2026-10-11）

{headline} 决定{decision}；{t['calls']}次真实Mplus调用；正文v51、附录v43。此目录是完整的本批阶段交付，论文七项问题尚未全部解决。

建议先读[给网页端的说明](FOR_WEB_REVIEWERS.md)、[执行报告](REPORT.md)、[三方建议裁定](CONSENSUS.md)，再核对[全部调用](MODEL_INDEX.md)与[七项状态](SEVEN_ISSUES.csv)。当前稿件提供[正文Markdown](manuscripts/main_readable.md)、[附录Markdown](manuscripts/appendix_readable.md)、同版Word与PDF。

下载[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)列出的全部ZIP，解压到同一目录；每包≤25,000,000字节，都是独立有效ZIP。先校验每包大小、SHA-256和CRC，再按[FILE_MANIFEST.csv](FILE_MANIFEST.csv)核验内部文件。`.inp.txt/.out.txt`是原始输入输出的逐字节镜像，便于网页端读取。sources目录是原建议材料，实际执行版本仅为code目录及其冻结合同。

可在安装numpy、pandas、scipy的Python中运行：

```text
python reporting/verify_round2f.py --root . --output ../round2f_independent_check --terminal
```

该程序只复算公开聚合证据，不调用Mplus、不读取微观数据。精确观测似然回执由本机使用私有原数据产生，网页端不能仅凭本包重算它。生产估计和排版脚本保留本机路径与布局供审查；公开复核器使用上述相对根目录即可运行。

前轮基线：[Round2E固定提交](https://github.com/lzhs1995/PP-lcgm-paper/tree/a323b0eace23bb471a5b4b7e66fff5361de5d874/round2E_20261010)。本轮固定标签为`review-round2F-20261011`；上传后交付消息提供完整提交SHA和匿名下载复算结果。未公开任何参与者记录或插补对象。
''')
 save('FOR_WEB_REVIEWERS.md',f'''# 可直接交给ChatGPT Pro与Claude网页端的说明

请以这个 **Round2F** 目录为最新资料，以Round2E为历史基线，不再按旧Round2E任务书启动四分支队列。{headline}

本轮已结合你们的意见在Windows本机执行：SD 3274人/2410户、原24项控制及十份MI只读复用；自由E1与E1B各在20/30点、严格EM准则下使用两套合法完整起点。决定{decision}，实际{t['calls']}次Mplus调用，完整新增MI家族{len(complete)}个。全部成功、非法和未准入结果都保留。

请先读取[REPORT.md](REPORT.md)和[CONSENSUS.md](CONSENSUS.md)。关键变化是：不能只凭LL接近、单次合法或负方差不显著认定家族可采用；固定SY=0也不能自动成为主调节证据。{detail}

严格20→30点、双起点的逐路径证据见[NUMERIC_PATH_COMPARISONS.csv](NUMERIC_PATH_COMPARISONS.csv)，原始INP/OUT、TECH3、参数与起点来源见[MODEL_INDEX.md](MODEL_INDEX.md)。当前论文为[正文v51](manuscripts/main_readable.md)和[附录v43](manuscripts/appendix_readable.md)，保留SW与SD E0，不将调节未形成MI写成无效应。

{cc_note}

你们的原建议已作如下取舍：采纳严格收敛、自由模型只作诊断的数值比较、0.020/0.034/0.080固定点、完整控制及有准入条件的P99；同时固定20/30点与30点后续家族。省去E0B整族、性能配对、SE分解及自动H4。总上限39次、3小时实际引擎墙钟、4小时批次；待机不扣时。原Claude包的积分设置继承、RUNNING恢复与轮询间隙扣账等问题已在冻结前修正，未在看到统计结果后改估计代码或容差。

请重点给出四项可执行评议：

1. **数值失败的准确解释。** 当前双起点路径差、SE变化和LL差分别说明什么？请避免把预定门槛未通过夸大为理论不可识别，也不要仅因差异相对SE小就事后宣布本轮通过。
2. **下一次最少且可判定的诊断。** 如建议继续，请明确要检验的优化假说、原始输出依据、最多几次调用/多长时间，以及足以结束该路线的停止条件。保存点梯度/局部曲率或独立条件高斯优化是否比继续增加积分点更有针对性？请先论证，不默认重开十份或四分支长队列。
3. **论文能保留的实质结论。** SD E0两条Z₀路径均不精确；SY@0属于强限制；gi0不是实际基期Y总关联，gs0在E1中条件于SX=0。请核查v51/v43是否仍有把单份、模型合法性、支持原假设和MI推断混淆的位置。
4. **后续优先级。** 在H4尚无合格主家族入口的情况下，下一步应先处理优化精度、SW的Y形状，还是收窄论文可检验范围？其他分支与H4均需独立合同，不以SD的P值决定。

请下载PACKAGE_MANIFEST列出的全部ZIP并逐包核验，再使用公开复核程序。每包不超过25,000,000字节。没有微观DAT、真实PID/FID、逐人得分或MI对象；请不要宣称已经云端重新拟合CFPS或验证全部逐人记录。若未成功读取某个文件，明确列出，不把下载失败当统计失败。无须现在补传全量数据。

本机独立核对已通过{V['calls']}次新调用、{V['free_parameters']}个自由参数、{V['matrices']}个矩阵和{V['full_start_slots_verified']}个起点槽，并再次合并旧SD E0十份。上传成功后的固定提交和匿名下载复算回执随用户交付说明提供；不以本地PASS替代远端复算。
''')
 scope=dict(release_type='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW',preview=False,ready_for_publication=True,
   public_microdata=False,independent_status='PASS',new_calls=t['calls'],new_complete_families=len(complete),decision=decision,
   headline=headline,full_paper_complete=False,manuscripts=['v51','v43'])
 (R/'DELIVERY_SCOPE.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding='utf-8')
 print('REPORTS_BUILT',decision,t['calls'],complete,flush=True)

if __name__=='__main__':main()
