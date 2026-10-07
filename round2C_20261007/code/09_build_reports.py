"""依据最终门槛与数据表生成检查点C报告初稿，发布前仍需逐项审阅。"""
from pathlib import Path
import csv,json,hashlib
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007')
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(n,s):(R/n).write_text(s,encoding='utf8')
def md(h,rs):return '| '+' | '.join(h)+' |\n|'+'|'.join(['---']*len(h))+'|\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in rs)+'\n'
def n(v,d=4):
 try:return f'{float(v):.{d}f}'
 except (TypeError,ValueError):return '—'
def ptext(v):
 x=float(v)
 return '<0.000001' if x<.000001 else f'{x:.6f}'
def main():
 batch=json.loads((R/'audit/batch_complete.json').read_text());verify=json.loads((R/'evidence/independent_verification.json').read_text());assert verify['status']=='PASS'
 gate=rows(R/'audit/family_gates.csv');members=rows(R/'results/member_dispositions.csv');fit=rows(R/'results/model_fit.csv');profile=rows(R/'results/profile_MI01.csv');calls=rows(R/'audit/CALL_REGISTER.csv');execution=rows(R/'audit/MODEL_REGISTER.csv')
 pool=rows(R/'results/conditional_MI_paths.csv') if (R/'results/conditional_MI_paths.csv').exists() else []
 eligible=[g['spec'] for g in gate if g['eligible_for_conditional_pooling']=='TRUE'];adopted='、'.join(eligible) or '无'
 labels={'bii':'亲近度起点→抑郁起点','bis':'亲近度起点→抑郁变化','bss':'亲近度变化→抑郁变化','bsyiy':'抑郁起点→抑郁变化'}
 body=f'''# PP-LGCM Round2C 检查点C报告

本批已完成预定模型对照与采用判断，共登记 **{len(calls)} 次Mplus调用**。符合全部十份成员合法及起点稳定门槛、可以独立报告条件MI结果的模型族为：**{adopted}**。统计任务止于检查点C；本轮没有开展核心调节、H4.2b、窗口模型、新插补或bootstrap。

## 1. 本机执行范围与证据

复用Round2B十份已完成的家庭—个人分层MI数据，每份3274人、2410个家庭、24项控制。数据、原父模型输入和复制后DAT逐一核对SHA-256。旧目录与v47/v39保持不变。C1固定SY条件残差为0，SW增加五个自由同波测量残差协方差，XLIN将X改成日历线性；三类各十份。此外在MI01执行四个正残差固定点，零点复用C1。

新代码的21项预检已执行；本批共保存{sum(int(x['parameter_rows']) for x in execution)}行高精度参数，绑定TECH1顺序与TECH3协方差。独立Python另从高精度参数重建B、PSI、LAMBDA、THETA、G、SIGMA和条件变化协方差，并复算可合并模型的Rubin结果。这是已保存模型参数的独立代数核对，不是第二套软件独立重估CFPS，也不证明模型假设为真。

## 2. 模型族采用判断

'''
 body+=md(['模型族','合法成员/10','MI01起点稳定','允许条件合并'],[[g['spec'],g['admissible'],g['start_stable'],g['eligible_for_conditional_pooling']] for g in gate])
 body+='\n采用门槛包括自由负方差、潜变量与测量残差协方差的半正定性、预期秩、观测协方差正定性、TECH3与标准误对应、严重识别警告和不同起点一致性。固定零残差允许预期零特征值，不允许负方差转移或新的不可识别。未采用输出完整保留；不挑选成员合并，不从非法输出摘取显著路径。\n\n'
 body+=md(['模型族','CFI范围','RMSEA范围','SY残差范围'],[[g['spec'], '—' if not (f:=[x for x in fit if x['id'].startswith(g['spec']+'_')]) else f"{min(float(x['CFI']) for x in f):.3f}–{max(float(x['CFI']) for x in f):.3f}", '—' if not f else f"{min(float(x['RMSEA_Estimate']) for x in f):.3f}–{max(float(x['RMSEA_Estimate']) for x in f):.3f}", '—' if not (m:=[float(x['SY_residual']) for x in members if x['spec']==g['spec'] and x['SY_residual']!='NA']) else f'{min(m):.6f}至{max(m):.6f}'] for g in gate])
 body+='\n**采用判断：SW作为后续评审的主要工作模型候选，C1作为强约束敏感性对照，XLIN不采用。** SW十份均合法，SY残差自由且为正，起点稳定；这支持同期残差结构在本批的实际可估计性，但不证明遗漏同期共变是唯一原因。选择依据结构与合法性，不依据显著性。\n\n## 3. 固定工作规格下的条件MI结果\n\n'
 if pool:
  body+=md(['规格','路径','估计','SE','95%区间','p','MCSE/SE'],[[r['spec'],labels[r['label']],n(r['estimate']),n(r['se']),f"[{n(r['lower'])}, {n(r['upper'])}]",ptext(r['p']),n(r['MCSE_over_SE'],5)] for r in pool])
  if (R/'results/family_sensitivity.csv').exists():
   sensitivity=rows(R/'results/family_sensitivity.csv')
   body+='\n各独立通过门槛的家族间，点估计及区间宽度的描述性对照：\n\n'
   body+=md(['路径','家族数','方向一致','点估计范围','区间宽度范围'],[[labels[r['label']],r['families'],r['direction_consistent'],f"{n(r['estimate_min'])}至{n(r['estimate_max'])}",f"{n(r['interval_width_min'])}至{n(r['interval_width_max'])}"] for r in sensitivity])
   body+='\n这里没有将不同结构合并为一个效应；XLIN还改变X变化的定义。点估计变化与区间是否含零的差别，不构成模型间系数差异的显著性检验。只有一个合法家族时，不能据其单独结果宣称跨结构稳定。\n'
 else:body+='没有符合完整采用门槛的模型族，因此不生成条件MI路径结果。\n'
 body+='''
合并使用同一参数顺序的全部十份估计及对应TECH3协方差；不平均p值。采用完整数据大样本自由度近似下的Rubin规则，不称为有限家庭数的精确推断。固定SY残差不进入自由参数表，也没有人为补造其SE或p值。

以上区间仅对给定工作结构成立，不包含模型选择不确定性，不检验人口残差方差是否等于0。C1进一步规定：给定控制和两个截距后，抑郁剩余变化由亲近度剩余变化完全线性决定。这是强工作假设，不意味着所有人的抑郁变化相同。MCSE/SE超过.05只记录为精度提示，不自动增加插补。X和Y采用冻结的基期标准化输入；自由形状变化和日历线性变化的含义不同，不能按星号或绝对系数大小择优。

## 4. 预定MI01残差剖面

'''
 body+=md(['固定SY残差','路径','估计','SE','单份95%条件区间','合法'],[[n(r['tau'],2),r['label'],n(r['estimate']),n(r['se']),f"[{n(r['lower'])}, {n(r['upper'])}]",r['usable']] for r in profile])
 body+='''
这里每一点均重新估计其余自由参数。区间为固定模型下的单份渐近Wald诊断；非法点不作实质推断。网格不是置信集合，各点区间的并集也不是95%置信区间。方向是否一致、估计幅度变化和区间宽度分别列在`results/profile_sensitivity.csv`。不把“所有点均显著”作为稳健性的定义。

## 5. 两位评审建议的共识和分歧

同意关闭已经具体修复的计分入口、家庭共同值错误及SE漏导；不重做同样的数据审计。两位评审关于非法潜变量协方差不能凭良好拟合放行的判断正确。本机亦复现了前批MI01约−2.536859的代数偏比值及−0.069725484的SY创新方差；它们是同一非法分解的代数表达，不是两个独立证据，更不是人口相关。

同时保留ChatGPT建议的双线性对照与Claude建议的同期残差对照，并运行全部十份。没有采纳用非法父模型的低FMI宣称MI与FIML等价、用普通或校正LRT选择模型、用TRd<3.84定义相容剖面，以及追加清零和更多规格的建议。具体裁定见`audit/REVIEW_SYNTHESIS.md`与运行前冻结的`RUN_CONTRACT.json`。

## 6. 七项问题与本轮终点

'''
 issues=[['1','抑郁趋势、时间单位与窗口','部分解决','旧下降结论撤回，十年时间尺度和当前工作规格明确；窗口未执行'],['2','CESD计分与范围','已解决：计分及实际入口','新模型复用修正计分与基期标准化；不等同测量不变性已证实'],['3','增长方差与识别','本批已完成限定判断','采用状态见三类完整成员门槛；受约束工作模型不证明人口方差为零'],['4','拟合不足','本批已完成结构对照','拟合与几何分别评价；未唯一识别失配原因'],['5','过度表述与版本混杂','当前稿件同步；仍为审阅候选','历史表移入审计材料，当前条件结果与未检验事项分开'],['6','得分、调节与MI','具体数据缺口已修；核心调节未执行','本批仅父模型条件推断，不宣称得分误差或潜交互相容性已解决'],['7','H4.2b','方向与判定文字保留；正式检验未执行','未比较组内星号宣称组间差异，不更改假设以追求支持']]
 body+=md(['编号','问题','状态','解释'],issues)
 with (R/'SEVEN_ISSUES.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['issue','question','status','explanation']);w.writerows(issues)
 body+='''
## 7. 稿件、交付与限制

正文v48和附录v40为本批审阅候选。原v47/v39的DOCX及PDF在历史审计附件中完整保留，来源与哈希逐一对应。当前结果表不重新堆积98张历史表；原理论假设保持可追溯，未来调节未执行不作零效应解释。新稿保留段落的引文字段与其余Word部件通过XML层检查，原生Word导出与逐页视觉核查另有同版回执。静态参考文献来自保留字段的既有CSL元数据；没有伪称完成Zotero插件刷新或全部原文核验。

公开资料不含CFPS微观DAT/DTA、RDS/GH5、真实PID/FID、逐人得分或插补对象。可公开的高精度参数与参数协方差属于模型聚合输出。文件与压缩包各有大小、SHA-256和完整性清单，每包不超过25,000,000字节。模型或检验未通过也完整交付，不扩大规格寻找显著性。

检查点C到此停止。后续核心调节、H4.2b和窗口分析需在审阅这些工作模型与估计含义后另行推进；本报告不把其未执行解释为不存在效应。
'''
 body+='\n## 8. 实质解读与原始聚合输出\n\nSW的变化关联为−0.2464，95%区间［−1.4416，0.9488］；C1为−0.7168，区间［−1.6533，0.2198］。方向相同，但幅度依赖结构且估计不精确。SW的基期亲近度—抑郁路径为−0.3502，区间［−0.6388，−0.0615］，仅支持该工作模型下的负向基期关联。MI01五个固定残差点均合法，变化关联区间宽度从约1.853变为0.458；其他两条预测变化的路径还发生符号改变，不能将某固定点的精确性升级为完整MI证据。\n\n每次模型附带 estimates.dat.txt 和 tech3.dat.txt，分别是Mplus原始参数估计／标准误及参数估计协方差的逐字节镜像；它们是聚合输出，不是微观数据。data.dat未复制、未改名公开。\n'
 body+='\n记录口径：34个基础模型＋2次不同起点核查＝36次调用，未使用修复重试。XLIN因MI01不合法而未执行起点核查；表中start_stable=FALSE是合并门槛未满足，不表示另有一次起点核查失败。`revision_receipts.json`和`native_word_export.json`内PENDING反映各自生成阶段；最终同版状态以`visual_review.json`及`evidence/delivery_document_verification.json`为准。\n'
 write('REPORT.md',body)
 write('MODEL_INDEX.md','# 本批模型索引\n\n'+md(['模型','采用状态','高精度SY残差','原始输出'],[[r['id'],r['status'],r['SY_residual'],f"[OUT](models/{r['id']}/{r['attempt']}/model.out.txt)"] for r in members])+'\n全部调用含起点及重试另见 `audit/CALL_REGISTER.csv`。\n')
 write('README.md','''# PP-LGCM Round2C：检查点C

请先读[报告](REPORT.md)、[给网页评审者的说明](FOR_WEB_REVIEWERS.md)、[采用门槛](audit/family_gates.csv)与[交付范围](DELIVERY_SCOPE.json)。本批数据来源固定于前批提交`a666e0ea8a610159709bb504d3d275f6f582efb9`。

本批包含三类模型各十份、MI01固定残差剖面及必要起点核查。正文v48/附录v40是当前审阅候选；`manuscript/historical_audit/`内v47/v39仅供追溯。所有模型输入输出均有TXT镜像，当前PDF亦附逐页Markdown与全文，便于网页端直接读取。

下载包和SHA-256见[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)；逐文件清单见[FILE_MANIFEST.csv](FILE_MANIFEST.csv)。每包≤25,000,000字节。GitHub目录提供与ZIP同版的可读文件。未公开CFPS微观数据、真实PID/FID或插补对象。

本轮停止在检查点C；没有新调节、H4.2b、窗口模型、新MI或bootstrap。不要将未执行当作无效应，也不要将C1的固定零方差当作边界检验结果。
''')
 write('FOR_WEB_REVIEWERS.md',f'''# 可直接转交ChatGPT网页端和Claude网页端

本次请复核PP-LGCM的检查点C。

固定版本入口：`https://github.com/lzhs1995/PP-lcgm-paper/tree/review-round2C-20261007/round2C_20261007`。

本批实际登记{len(calls)}次Mplus调用。可条件合并的模型族：{adopted}。请按以下顺序读取：

1. `RUN_CONTRACT.json`和`audit/REVIEW_SYNTHESIS.md`：说明为什么保留C1、SW和XLIN全部十份，以及未采纳哪些外部建议。
2. `audit/CALL_REGISTER.csv`、`audit/family_gates.csv`、`audit/start_checks.csv`：核对调用数、全部成员合法性和起点稳定性。
3. `models/`：每次完整INP/OUT、TECH1/TECH4、参数、TECH3协方差和绑定回执；原始输出有`.txt`镜像。
4. `results/`与`evidence/independent_verification.json`：检查四条条件关系及MI01剖面。先区分合法／非法，再评价方向、幅度与区间，不按星号替代敏感性判断。
5. `manuscript/`中的v48/v40与`readable/`中的同版PDF全文：评阅当前结论是否严格对应采用状态。v47/v39在`historical_audit/`中只作追溯。

请重点审阅：矩阵重建是否正确；固定SY=0的解释是否足够清楚；自由形状X和线性X的估计对象有何区别；正残差剖面是否显示实质模型依赖；条件Rubin区间的边界是否被准确限定。不要要求用非法父模型作常规LRT，也不要将本轮未做的调节或H4.2b解释为无关联。

这次可在公开资料上复算模型参数几何与合并统计量，但不能声称已独立重估CFPS个体记录。无需重传旧包或全量微观数据。若存在具体代码问题，请指出文件、参数及其后果，不以泛泛重做全部分析替代定位。
''')
 feedback=R/'FOR_WEB_REVIEWERS.md'
 feedback.write_text(feedback.read_text(encoding='utf8')+'\n本机采用判断：SW作为主要工作模型候选，C1作为固定零敏感性对照；XLIN十份均不合法。SW变化关联估计−0.2464，95%区间［−1.4416，0.9488］，C1为−0.7168，［−1.6533，0.2198］。请评价这种采用判断及精度表述是否合理，并区分“本批父模型可条件报告”与“七项意见全部解决”。\n\n优先反馈三个问题：（1）SW的潜变量及测量残差几何是否支持上述采用判断；（2）固定残差剖面是否充分揭示约束敏感性；（3）若后续恢复四项核心调节，哪一种估计对象和误差处理最可辩护。本轮未执行这些后续检验，请勿将它们计为已失败或已完成。\n',encoding='utf8')
 # 仅在实际同版PDF视觉核查完成后允许生成可发布范围声明。
 visual=json.loads((R/'manuscript/visual_review.json').read_text());assert visual['status']=='PASS'
 scope={'checkpoint':'C','ready_for_publication':True,'calls':len(calls),'eligible_families':eligible,'new_MI':False,'moderation':False,'H4_2b':False,'window_models':False,'bootstrap':False,'microdata_included':False,'manuscripts':'v48/v40 review candidates; not final submission','native_plugin_refresh':False,'conditional_inference_only':True,'sources':'Round2B completed MI10 and fixed source hash bindings'}
 write('DELIVERY_SCOPE.json',json.dumps(scope,ensure_ascii=False,indent=2))
 print(json.dumps(scope,ensure_ascii=False))
if __name__=='__main__':main()
