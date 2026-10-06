"""白名单发布第二轮评审点A；数据留在本机，报告与模型证据可在线读取。"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,hashlib,shutil,re,zipfile,html
import fitz
ROOT=Path(r'C:\Users\LZHS\pp_lgcm_review\round2_20261006')
PROJECT=Path(r'C:\Users\LZHS\Desktop\cnm\tasks\01_R_analysis')
WORK=PROJECT/'work/cfps_round2_20261006'
REPO=PROJECT/'work/cfps_review_20261005/github_publish'
PUB=REPO/'round2_20261006';PUB.mkdir(exist_ok=True)
BASE='https://github.com/lzhs1995/PP-lcgm-paper'
TAG='review-round2A-20261006'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8',newline='\n')
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def csvout(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(rows,cols):
 esc=lambda x:str(x).replace('|','\\|').replace('\n',' ')
 return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+''.join('| '+' | '.join(esc(r.get(c,'')) for c in cols)+' |\n' for r in rows)
copies=[]
def cp(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 copies.append({'source_name':src.name,'public_path':dst.relative_to(PUB).as_posix(),'sha256':sha(dst),'bytes':dst.stat().st_size})

assert json.loads((ROOT/'audit/verification_summary.json').read_text(encoding='utf8'))['status']=='PASS'
attempts=readcsv(ROOT/'audit/attempt_index.csv');assert len(attempts)==19
for p in sorted((ROOT/'audit').rglob('*')):
 if p.is_file() and p.suffix in {'.csv','.json'}:cp(p,PUB/'audit'/p.relative_to(ROOT/'audit'))
for p in WORK.glob('*'):
 if p.suffix in {'.R','.py'}:cp(p,PUB/'code'/p.name)
for r in attempts:
 source=ROOT/'models'/r['id']/r['attempt'];dest=PUB/'models'/r['id']/r['attempt']
 for p in source.iterdir():
  if p.name in {'model.inp','model.out','receipt.json','parameters.csv','fit.csv','TECH1_parameter_map.csv','TECH3_parameter_covariance.csv','TECH4_latent_covariance.csv','TECH4_latent_correlation.csv'}:
   cp(p,dest/p.name)
   if p.name in {'model.inp','model.out'}:cp(p,dest/(p.name+'.txt'))
 for p in [dest/'model.inp',dest/'model.out']:assert p.exists()
 # 关键章节节选提供可直接阅读入口；完整原文同时保留。
 txt=(source/'model.out').read_text(encoding='utf8',errors='replace');lines=txt.splitlines()
 selected=[];active=False
 for i,line in enumerate(lines,1):
  s=line.strip()
  if s in {'MODEL FIT INFORMATION','MODEL RESULTS','QUALITY OF NUMERICAL RESULTS'}:active=True
  if s in {'STANDARDIZED MODEL RESULTS','CONFIDENCE INTERVALS OF MODEL RESULTS','RESIDUAL OUTPUT','TECHNICAL 1 OUTPUT'}:active=False
  if active or any(k in line for k in ['*** ERROR','WARNING:','NOT POSITIVE','NEGATIVE VARIANCE','TERMINATED NORMALLY']):selected.append(f'{i:06d} {line}')
 write(dest/'KEY_OUTPUT.md',f'# {r["id"]} / {r["attempt"]}\n\n状态：**{r["status"]}**。数值仅在合法模型和对应研究范围内解释。\n\n[完整输出](model.out.txt) · [输入](model.inp.txt)\n\n```text\n'+ '\n'.join(selected)+'\n```\n')

for name in ['PP_LGCM_review_v46_round2A_NOT_RELEASED.docx','PP_LGCM_review_v46_round2A_NOT_RELEASED.pdf','revision_receipt.json','pdf_verification.json']:
 cp(ROOT/'manuscript'/name,PUB/'manuscript'/name)
pdf=PUB/'manuscript/PP_LGCM_review_v46_round2A_NOT_RELEASED.pdf'
with fitz.open(pdf) as doc:
 full='# 正文v46：评审点A审阅副本\n\n仅更新历史标记与启示边界，未替换为正式MI主表。公式和布局以PDF为准。\n'
 for i,p in enumerate(doc,1):
  text=p.get_text(sort=True)
  write(PUB/'readable'/f'page-{i:03}.md',f'# PDF物理页 {i}\n\n[PDF](../manuscript/{pdf.name}#page={i})\n\n```text\n{text}\n```\n')
  full+=f'\n## 第{i}页\n\n```text\n{text}\n```\n'
 write(PUB/'readable/manuscript_full.md',full)

fits=readcsv(ROOT/'audit/model_fit.csv');core=[r for r in fits if r['attempt']=='attempt01' and r['id'] not in ['D1981_P1_linear_xcov']]
core=[r for r in core if r['id']!='D1981_P1_linear_residual'];assert len(core)==11
score=readcsv(ROOT/'audit/corrected_score_precision.csv')
report='''# PP-LGCM七项意见第二轮核验：评审点A报告

**状态：第一批来源核查和有限基础诊断完成；正式MI、四项核心调节及H4.2b正式检验尚未恢复。**

本轮固定上一轮提交 `90fe928451209cc7a544e7bde467081ce4a73f4a`，承接已完成的CFPS历史复现。CESD8为主指标，CESD20sc为敏感性；CHARLS继续暂停。原稿和原数据未改动。此包是供第二轮方法复核的阶段性交付，不能视为七项问题全部解决或论文定稿。

## 1. 执行范围与计数

完成11个预定基础科学规格，另完成2个结构敏感性规格，并对原条件模型执行2次有效的不同起点核查，共15次进入估计的运行。另有4次派生输入因生成器遗漏DATA段被Mplus拒绝，保留为输入错误。合计19份完整INP/OUT，不能称为19个科学规格。

首批11规格中7个没有发现原始输出所报的负方差或非法矩阵，可继续审阅；4个不可接受。两个结构敏感性分别为X增长因子—协变量协方差放开模型和SY条件残差固定零的边界模型。边界模型仅作敏感性，不能自动取代无约束主模型。执行与解析均通过RStudio原生工具、MplusAutomation 1.3及Mplus 9完成；前台会话原装MplusAutomation 1.2未修改，隔离worker使用既有1.3库。

## 2. 数据版本与计分入口

新模型的五期CESD原分与上一轮测量核验对象逐记录相同，缺失差异和数值差异均为0。2012原旧计分至修正计分有2593人发生变化，均值从16.232变为13.575；2016及以后原始总分不变。基期标准化常数随2012修正而改变，因此后续各期标准化CESD也必须更新。这是从实际数据逐记录比较得到的聚合结论，不是由均值差反推算法。

亲近度均值的现有五期标准化值符合相同仿射变换，最大误差约2.41×10⁻⁷，符合原数据浮点保存精度。诊断中冻结该X量尺。1981人诊断统一使用原3274人2012年的修正CESD均值13.5754428833及SD 4.2592386459，不逐样本重新标准化。

Mplus MI v3实际输入的CESD、关系基期指标和婚姻变量与当前修正数据对齐。但历史插补的USEVAR确实包括基期CESD及关系指标；后期CESD位于仅随输出保存的AUXILIARY区，不能一概说都参与了插补模型。数据已经进入MI输入与MI结果可正式采用，是两个不同验收环节。

## 3. 同样本诊断结果

1981人四步采用相同样本、同尺度、相同家庭聚类和相同X自由形状：U0抑郁无控制；U1抑郁加26控制；P0双过程无26控制；P1双过程加26控制。P0与P1均含SY ON IY，不把四步自动视为普通嵌套LRT序列。

'''+table(core,['id','status','N','CFI','TLI','RMSEA_Estimate','SRMR'])+'''
在线性Y设定下，U0、U1、P0均可继续审阅，P1出现SY负条件残差方差；该负值被打印为0.000，但Est./SE为−0.138且原输出明确报警，不能按打印零值放行。自由形状在U0、U1即出现负方差，P0虽未报非法解但变化信息弱，P1再次出现负条件残差方差。不同起点回到相同打印似然与参数，不能用增加迭代或一次正常终止解释为问题已解决。

原3274人两种增长模型补齐家庭聚类后均可继续审阅。自由形状变化均值仍为0.037，SE约0.035，p从原未聚类的.284变为.290；实际载荷仍为0、6.590、11.594、3.266、10。当前无证据恢复旧的显著下降判断。

原2225人四期线性对照正常估计：截距方差10.790，变化因子方差0.117（SE=.055，p=.034），CFI=.986、TLI=.983。它说明同一四期数据在简约时间结构下可以估计；没有证明四期自由形状已经修复，更不等于四项调节窗口稳健性已通过。

TECH3参数估计协方差、TECH1序号对应、TECH4潜变量协方差/相关、局部残差与模型预测均值均已导出。若TECH4协方差仅打印三位小数，近零斜率方差可导致舍入后矩阵出现微小负特征值；不能据此推翻原始合法解。P0两个模型的打印相关矩阵最小特征值分别约.252和.087，明显大于四阶矩阵的三位小数舍入扰动界.002；边界模型则不能要求严格正定。原始负方差警告与纯打印舍入分别处理。

## 4. 局部失配与两项敏感性

P1的最大标准化局部失配集中在X与协变量：C24（生活满意度）—X1的normalized residual为7.740，另有健康、帮助、地区、户口等与X的失配。TECH1核实IX/SX与26项C的52个协方差及相应回归均未自由估计，协方差起点/固定值为零。它是实际模型约束，不是“协变量已控制所以自动允许相关”。

据此，将原拟议的同期X—Y残差检查替换为更直接的X增长因子—C协方差检查，保持两项结构敏感性的预算，并记录这一诊断驱动的调整。放开后CFI由.909升至.970、TLI由.887升至.952、SRMR由.049降至.017，支持默认零关联约束是局部失配的重要来源。但SY负残差方差仍在，因此仍不可采用。该WITH参数化同时将C的均值/协方差纳入联合估计，参数数目由78变为507，输出似然口径改变，不能直接相减两份LL或跨口径比较AIC/BIC作为检验。

另一个SY条件残差固定零模型正常结束，且将相关残差协方差同步约束为零；CFI=.909、TLI=.889，局部失配未随边界约束消失。SY ON SX为−1.005，SE=.675，95%近似区间[−2.328,.318]，不能据其方向确认变化关联。该约束改变了模型，不是把原负估计截为零。

这两项分别揭示“X与控制变量的结构限制”和“SY剩余变化信息接近边界”，并未共同构成一个已验收主模型。本轮不继续扫描组合约束寻找显著结果。

## 5. MI：发现新的家庭层级问题

既有Mplus MI v3仍有14/40个人收入插补值、184/900家庭收入插补值为负；最后公开TECH8的PSR=1.111也不是充分的收敛证据，继续不采用。

对既有PMM v3逐一核查10个成员：哈希匹配；原观测单元格改变=0；负收入=0；个人收入二分类派生错误=0。**但19个涉及家庭收入缺失的多成员家庭，在每一份插补中都出现同一家庭成员具有不同家庭收入，10份均为19/19；原观测家庭收入的组内冲突为0。** 这是本轮新发现，见`audit/pmm_member_audit.csv`。

因此不能把“供体支持/链摘要通过”当作正式MI已修复。共享家庭收入必须在家庭单位生成并映射回个人，再与个人层协变量插补及目标模型相容地处理；不事后取平均或任选成员的收入。当前PMM仍为方法敏感性候选，不能投入正式主分析。26项变量字典另列实际标签、缺失和编码；wave属于后续追访信息，其他标为BASELINE_NAME_VERIFY_SOURCE的变量仅核实命名/数据，未声称所有生成时点已获审计通过。

## 6. 修正因子得分SE缺口已找回

修正Oldest/FirstSon的原始SAVEDATA均保存I4_SE和S4_SE，旧候选CSV只导出PID/I4/S4。本轮从对应已哈希绑定的模型读回，并验证全部得分与候选CSV完全相同。没有给新得分配历史SE，也没有重估第一阶段。

'''+table(score,['indicator','factor','N','N_SE','score_SD','SE_median','cutpoint','equal_cut','low','high'])+'''
原保存格式为F10.3，存在大量并列；不能把切点解释为未知理论阈值，也不能仅凭并列就断言全部由舍入造成。SE已恢复不等于得分误差已传播到乘积项推断；SE/得分SD也不是可直接使用的可靠性系数。

## 7. 七项问题当前处置

| 问题 | 本轮进展 | 尚未关闭 |
|---|---|---|
| 1 趋势、时间、窗口 | 聚类复核及四期线性定位完成 | 核心关系与调节窗口稳健性 |
| 2 CES-D计分 | 新分析入口逐期一致，计分问题继续按已解决处理 | 纵向测量不变性属于另一问题 |
| 3 增长方差 | 同样本四步链与起点重复完成，负残差位置明确 | 无约束条件模型仍不可接受 |
| 4 拟合 | 52个默认零关联及其局部失配得到实证定位 | 单独修正该层仍未解决负方差 |
| 5 过度表述 | v46在主表标题醒目标记历史/混合版本；启示降为待检验线索 | 正式MI主表尚不能替换 |
| 6 调节、得分、MI | 修正得分SE恢复；MI输入依赖、家庭冲突查明 | 正式MI、完整三过程失败链及核心调节推断未闭合 |
| 7 H4.2b | 保留原假设和未获一致支持判定 | 当前数据正式三阶交互/组间检验未执行 |

## 8. 评审点A的分支决定

- 可以采用本轮来源核查、计分入口、聚类差异、四期时间结构诊断、局部失配和得分精度事实。
- 1981人无控制模型中的关联只能在其样本和无控制设定下解释；不能替代原3274人正式MI主分析。
- 正式MI主分析、四项调节扩展、H4.2b三阶检验、全流程bootstrap及正式MI窗口矩阵，本轮均不扩展：无约束条件父模型未通过且两套MI候选各有具体问题。未运行分支没有伪造结果，也不意味着原假设已被否定。
- 下一步首先固定家庭共享收入的层级插补规则及全部控制变量的时间含义；再在同样本检验能合理表达X—C关联的条件参数化，并单独评估SY边界。完整潜交互仍优先，但在父模型与缺失处理获验收前，不再次启动数百模型或长时间积分。

## 9. 验证与可复核范围

独立Python直接解析Mplus原文，与R读回对照1443个参数行全部一致；19次输入/数据/输出哈希核对通过。原修正数据与测量核验对象哈希未改变。置信区间汇总按打印估计与SE计算，受原输出舍入限制，精确解释请同时查看完整CINTERVAL部分。

公开包包含完整INP/OUT、TECH1/3/4、参数、聚合证据、代码和审阅稿。不含实际DAT、插补对象、逐人得分、PID/FID或ID映射。可以核对代码、诊断、参数及检验逻辑；不能宣称据此在云端全量重跑CFPS。当前提供的协方差矩阵属于本轮单数据诊断，不能冒充逐插补矩阵或25项正式MI检验成果。

首批60次资源采样中捕获的Mplus峰值RSS约34.9 MiB、private约247.6 MiB；只代表被采到的基础模型，不包含后续所有敏感性峰值。运行采用单worker/单处理器，未升级Mplus、未终止外部任务。这不能证明所有Windows程序已优化或软件版本普遍加速。
'''
write(PUB/'REPORT.md',report)
write(PUB/'MODEL_INDEX.md','# 本轮19次执行：科学规格、起点与输入错误分别计数\n\n'+table([{**r,'evidence':f'[关键输出](models/{r["id"]}/{r["attempt"]}/KEY_OUTPUT.md)'} for r in attempts],['id','attempt','purpose','N','status','seconds','evidence']))
evidence=[('数据入口','analysis_entry.csv'),('原旧—修正计分','old_corrected_comparison.csv'),('26项控制变量','covariates_26.csv'),('MI输入对齐','mi_input_alignment.csv'),('PMM逐成员家庭冲突','pmm_member_audit.csv'),('修正得分精度','corrected_score_precision.csv'),('增长方差','growth_variances.csv'),('主要路径','target_paths.csv'),('局部残差','largest_local_residuals.csv'),('52项默认约束','x_covariate_constraints.csv'),('矩阵诊断','matrix_diagnostics.csv'),('起点稳定性','start_stability.csv'),('预测均值','predicted_means.csv'),('独立核验','independent_validation.csv')]
write(PUB/'EVIDENCE_INDEX.md','# 证据阅读顺序\n\n'+''.join(f'- [{a}](audit/{b})\n' for a,b in evidence)+'\n[模型逐项索引](MODEL_INDEX.md)提供完整INP/OUT、行号节选和矩阵。\n')
write(PUB/'README.md',f'''# PP-LGCM第二轮：评审点A（2026-10-06）

**已执行基础诊断并交付；正式MI与核心调节尚未放行。** 重要新增发现：条件双过程的默认X—协变量零关联影响拟合；PMM候选出现19个共享家庭收入冲突家庭；修正排行得分的SE已从原保存文件找回。

1. [核验报告与七项状态](REPORT.md)
2. [证据阅读顺序](EVIDENCE_INDEX.md)
3. [19次执行索引](MODEL_INDEX.md)：11个基础规格、2个结构敏感性、2次有效起点核查、4次输入错误。
4. [正文v46审阅PDF](manuscript/{pdf.name}) · [DOCX](manuscript/{pdf.with_suffix('.docx').name}) · [可检索全文](readable/manuscript_full.md)
5. [给ChatGPT网页端的详细说明](FOR_CHATGPT.md)
6. [包清单](PACKAGE_MANIFEST.json)：每包≤25,000,000字节；也可直接读取展开文件。

v46只增加历史标记与启示边界，保留NOT_RELEASED；附录仍为[上一轮v38](../01_current_review/current_manuscript/PP_LGCM_appendix_review_v38_NOT_RELEASED.pdf)。旧版固定提交为`90fe928451209cc7a544e7bde467081ce4a73f4a`。本轮固定标签为`{TAG}`。

未提供微观数据或插补对象。论文全量历史复现已完成；当前为后续七项意见的统计修复。CHARLS暂停。
''')
forward=f'''# 给ChatGPT网页端：请复核PP-LGCM第二轮评审点A

我的本机Codex已按上一轮建议执行第一批来源核查和有限基础诊断，并公开了本轮材料。请独立判断，不把“运行完成”理解为“七项问题全部解决”。

固定阅读入口：

- 首页：{BASE}/blob/{TAG}/round2_20261006/README.md
- 完整报告：{BASE}/blob/{TAG}/round2_20261006/REPORT.md
- 证据索引：{BASE}/blob/{TAG}/round2_20261006/EVIDENCE_INDEX.md
- 模型索引：{BASE}/blob/{TAG}/round2_20261006/MODEL_INDEX.md
- 原始Markdown： https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/{TAG}/round2_20261006/REPORT.md

如GitHub页面不可读，请使用相同固定标签的raw.githubusercontent.com路径。所有关键输出有TXT镜像及带原始行号的节选；矩阵和参数有CSV。请列出实际读到的文件，不能把看到目录当作读取全部内容。

本轮交付包括11个基础科学规格、2个结构敏感性规格、2次有效起点核查，另保留4次由派生输入生成错误导致的Mplus读入拒绝。19份完整INP/OUT全部入册。独立解析核对1443个参数行一致。原CFPS历史全量复现已经完成；CESD8主分析、CESD20sc敏感性，CHARLS暂停。

请重点复核五个新结论：

1. 同一1981人样本中，线性U0/U1/P0可继续审阅，而条件P1出现SY负残差；自由形状U0/U1/P1也不可接受。不同起点重复了同一非法解。是否支持先解决模型结构及变化信息，而非增加迭代？
2. P1的52个IX/SX—C协方差默认固定零，局部失配集中在C—X。放开后拟合改善但负方差仍在；该WITH实现同时引入C的联合均值/协方差，参数78→507，似然口径不同。请评价下一步改用条件参数化、边界敏感性及协变量时间来源的最小可辩护方案，不直接相减两份LL。
3. 四期2225人线性模型正常且方差为正；它解决了什么定位问题，哪些窗口稳健性仍不能推断？
4. 两套MI候选问题不同：Mplus MI有负收入及不足的链诊断；PMM取值支持和原观测保持通过，却在每份候选的19个涉及共享家庭收入缺失的多成员家庭产生组内不一致。请明确家庭层与个人层插补的可执行规则，以及与潜交互分析的相容边界。不能用事后平均收入修复。
5. 修正Oldest/FirstSon的SE在原始SAVEDATA中存在，旧CSV漏导，本轮已找回并与候选得分逐项匹配。请评价精度、F10.3并列和后续不确定性处理，勿把SE/SD直接称可靠性，也勿断言测量误差必然保守。

请对七项问题分别给出已解决、部分解决、未解决或证据不足，并引用具体文件/模型。保留H4.2b原方向，正式组间检验仍未执行；不能按两组星号判定差异。当前没有正式MI合并、四项调节窗口矩阵或全流程bootstrap成果。

正文v46是NOT_RELEASED审阅副本：只把历史主表及混合版本表标记得更清楚，并把启示改为待检验线索；没有把诊断模型填成正式主表。附录v38和上一轮提交90fe928保留不变。

最后请给出：可接受的诊断事实、仍不可采用的推断、需要修正的报告措辞，以及下一批最少的模型/插补工作。每个后续规格请明确研究对象、样本、时间尺度、缺失规则、合法性标准和停止条件；不要展开数百组合，也不要要求结果必须显著。

包中没有微观DAT、真实PID/FID、逐人得分或插补对象，只能独立复核已有输出与方法逻辑，不能声称云端重新估计过原始CFPS。各ZIP为独立包，均≤25MB，详见PACKAGE_MANIFEST.json。
'''
write(PUB/'FOR_CHATGPT.md',forward);write(ROOT/'给ChatGPT网页端_第二轮评审点A说明.md',forward)
write(PUB/'code/README.md','''# 代码与复现边界

代码为本轮Windows实际使用脚本，保留路径便于本机追溯；其他环境须自行配置路径和合法数据。不要直接运行发布构建/推送脚本到其他仓库。

顺序：prepare_round2.R → run_round2.R；audit_lineage_scores.R与audit_pmm.R只读已有数据/输出；prepare_followups.py准备有限诊断，run_round2.R通过round2.manifest选取清单；summarize_round2.R导出矩阵；validate_and_collect.py独立复核原始参数。

初次准备曾遇到haven标签转换和矩阵列名断言错误，均在Mplus启动前修复。派生输入首版TITLE替换误吞DATA段，4次输入拒绝已归档。当前生成器按DATA段边界替换并检查FILE语句。现有目录实行不覆盖；复现应在新的输出根目录执行。

脚本快照包含执行后修复及报告工具；具体每次估计以对应INP/OUT及数据SHA为准，不能仅凭最新脚本推断历史输入。精确微观数据仅保存在作者本机，不在公开包中。
''')

# 检查公开文本中没有真实PID/FID完整数字；元数据路径保留但个人数据不出本机。
ids=set((ROOT/'private/identifiers.txt').read_text(encoding='utf8').splitlines())
violations=[]
for p in PUB.rglob('*'):
 if not p.is_file():continue
 assert p.suffix.lower() not in {'.dat','.rds','.dta','.sav','.rdata','.gh5','.fscores'}
 if p.suffix.lower() in {'.csv','.json','.txt','.md','.r','.py','.inp','.out'}:
  text=p.read_text(encoding='utf8',errors='replace')
  found=set(re.findall(r'(?<![A-Za-z0-9_.])\d{6,12}(?![A-Za-z0-9_.])',text))&ids
  if found:violations.append({'path':str(p.relative_to(PUB)),'count':len(found)})
assert not violations,violations
csvout(PUB/'COPY_MANIFEST.csv',copies)
write(PUB/'VALIDATION.json',json.dumps({'status':'PASS','raw_parameter_rows_verified':1443,'attempts':19,'participant_identifier_hits':0,'individual_data_files_included':False,'scientific_release':False},indent=2)+'\n')

# 独立ZIP；若任何组超过上限，按文件贪心拆成多个可独立解压包。
groups=[('01_report_manuscript',[p for p in PUB.rglob('*') if p.is_file() and p.relative_to(PUB).parts[0] not in {'models','code','packages'} and p.name not in {'PACKAGE_MANIFEST.json','PUBLICATION_MANIFEST.csv'}]),('02_models_code',[p for p in PUB.rglob('*') if p.is_file() and p.relative_to(PUB).parts[0] in {'models','code'}])]
packages=[];(PUB/'packages').mkdir(exist_ok=True)
for prefix,paths in groups:
 batches=[[]];budget=0
 for p in sorted(paths):
  if budget+p.stat().st_size>22_000_000 and batches[-1]:batches.append([]);budget=0
  assert p.stat().st_size<25_000_000,(p,p.stat().st_size)
  batches[-1].append(p);budget+=p.stat().st_size
 for i,items in enumerate(batches,1):
  z=PUB/'packages'/f'{prefix}_{i:02}.zip'
  with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
   for p in items:archive.write(p,p.relative_to(PUB).as_posix())
  assert z.stat().st_size<=25_000_000
  with zipfile.ZipFile(z) as archive:assert archive.testzip() is None
  packages.append({'path':z.relative_to(PUB).as_posix(),'bytes':z.stat().st_size,'sha256':sha(z),'files':len(items)})
write(PUB/'PACKAGE_MANIFEST.json',json.dumps({'max_bytes':25_000_000,'packages':packages},indent=2)+'\n')
manifest=[{'path':p.relative_to(PUB).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(PUB.rglob('*')) if p.is_file() and p.name!='PUBLICATION_MANIFEST.csv']
csvout(PUB/'PUBLICATION_MANIFEST.csv',manifest)
prefix='> **2026-10-06最新：第二轮评审点A已执行。** 请先读[第二轮入口](round2_20261006/README.md)与[完整报告](round2_20261006/REPORT.md)。正式MI和核心调节尚未放行；下方为上一轮v45/v38历史发布说明。\n\n'
for name in ['README.md','FOR_WEB_REVIEWERS.md','REVIEW_BRIEF.md']:
 p=REPO/name;s=p.read_text(encoding='utf8')
 if not s.startswith('> **2026-10-06最新：'):write(p,prefix+s)
write(ROOT/'runtime/publication_prepared.json',json.dumps({'status':'PREPARED','files':len(manifest)+1,'packages':packages,'tag':TAG,'timestamp':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
print(json.dumps({'files':len(manifest)+1,'packages':packages},indent=2))
