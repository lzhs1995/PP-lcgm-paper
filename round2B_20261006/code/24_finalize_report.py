"""全部父模型结束后，生成依赖门未通过时的真实交付报告；不启动分析。"""
from pathlib import Path
import csv,json,collections,datetime
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
def read(name):return json.loads((root/name).read_text(encoding='utf8'))
gate=read('audit/target_parent_gate.json')
receipts=read('audit/target_parent_receipts.json')
assert gate['total']==10 and len(receipts)==10
assert gate['all_members_admissible'] is False,'Valid parents require substantive follow-up; this failure-branch report must not close that work.'
assert {r['id'] for r in receipts}=={f'PARENT_MI{k:02}' for k in range(1,11)}
mi=read('audit/mi_engineering_acceptance.json')
assert mi['status']=='ENGINEERING_DATA_AND_CHAIN_REVIEW_COMPLETE_READY_FOR_PARENT'
assert mi['iterations']==30 and mi['passed']==mi['data_checks']==4300
visual=read('manuscript/build03_visual_review.json')
states=collections.Counter(r['status'] for r in receipts)
parent_lines=[];specs=set()
for r in receipts:
    folder=root/'models'/r['id']/'attempt01'
    contract=json.loads((folder/'input_contract.json').read_text(encoding='utf8'))
    specs.add(contract['specification_sha256'])
    p=folder/'parameters_high_precision.csv'
    values=list(csv.DictReader(p.open(encoding='utf-8-sig'))) if p.exists() else []
    negative=[f"{x['row']}={float(x['estimate']):.8g}" for x in values if x['matrix'] in {'psi','theta'} and x['row']==x['column'] and float(x['estimate'])<0]
    fit=folder/'fit.csv';actual_N='未提取'
    if fit.exists():
        f=list(csv.DictReader(fit.open(encoding='utf-8-sig')))[0]
        actual_N=int(float(f['Observations']));assert actual_N==3274
    parent_lines.append(f"| {r['id']} | {actual_N} | {r['status']} | {'；'.join(negative) or '见原始诊断'} | {r.get('parameter_covariance_bound',False)} |")
assert len(specs)==1
parent_table='\n'.join(parent_lines)
state_text='；'.join(f'{key}：{value}份' for key,value in sorted(states.items()))
negative_count=sum(bool(r.get('high_precision_negative_variance')) for r in receipts)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
scope={'generated_utc':now,'batch':'round2B_20261006','ready_for_publication':True,
 'publication_meaning':'Audit-evidence delivery only; not scientific adoption or journal submission',
 'target_cohort_N':3274,'imputations':10,'iterations':30,
 'MI_engineering_data_checks':4300,'MI_engineering_checks_passed':4300,
 'K_scientific_specifications':4,'K_execution_attempts':8,'target_parent_executions':10,
 'target_parent_states':dict(states),'target_parent_all_members_admissible':False,
 'formal_MI_pooling_performed':False,'core_moderation_performed':False,
 'H4_2b_formal_contrast_performed':False,'new_window_matrix_performed':False,
 'sat12_sensitivity_performed':False,'FIML_sensitivity_performed':False,
 'downstream_disposition':'NOT_RUN_PARENT_GATE_FAILED; not evidence of zero effects',
 'seven_issues_all_resolved':False,'manuscript_build':'build03','manuscripts_are_review_candidates':True,
 'same_build_NLM_review':False,'microdata_included':False,'ZIP_limit_bytes':25000000}
(root/'DELIVERY_SCOPE.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding='utf8')
issues=[
 (1,'抑郁趋势、时间单位与窗口','部分解决','撤回旧显著下降；统一3274人聚类来源；十年单位用于新条件模型','增长形状最终采用、正式主要关联和核心调节窗口稳健性仍未完成','audit/clustered_shape_comparison.csv; audit/target_parent_gate.json'),
 (2,'CES-D计分与范围','已解决：限计分及实际分析入口','修正CESD与基期标准化进入本轮数据及父模型','跨期测量不变性为独立问题，不由恒差8或计分校验证明','audit/source_contract.json; models/PARENT_MI01/attempt01/input_contract.json'),
 (3,'增长因子方差与识别','部分解决；无约束主父模型未通过','同条件诊断、原队列逐插补估计和高精度负方差检查均已实际执行','不得将条件残差负值按打印零放行，也不能由不显著证明没有个体变化','audit/model_adoption_summary.csv; audit/target_parent_receipts.json'),
 (4,'模型拟合不足','部分解决','澄清条件ON与联合WITH；诊断原零关系及同波残差方案','拟合改善没有消除负残差；尚无通过本轮验收的正式主父模型','audit/K1_conditional_likelihood_comparison.csv; MODEL_INDEX.md'),
 (5,'过度表述与版本混杂','关键文字及版本标记已修；正式表仍未形成','正文v47/附录v39 build03修正来源、编码、历史标签、交互术语和局部符号','候选稿保留历史数值供审计，不是修正数据正式结果表或投稿定稿','manuscript/build03_editorial_receipt.json; manuscript/build03_visual_review.json'),
 (6,'因子得分、潜调节与MI','具体数据缺口已修；核心推断未完成','修正得分SE导出缺口已关闭；新家庭—个人分层MI完成10份30轮及4300项检查','父模型门未通过，未合并非法成员；潜交互、得分不确定性与MI相容性未闭合','audit/mi_engineering_acceptance.json; audit/target_parent_gate.json'),
 (7,'H4.2b判定','文字判定已修；正式统计检验未完成','保留原假设方向和历史证据未获一致支持的限定','相应三阶交互/组间差异未执行，不能以组内星号或整组检验替代','FOR_WEB_REVIEWERS.md; DELIVERY_SCOPE.json')]
with (root/'SEVEN_ISSUES.csv').open('w',newline='',encoding='utf8') as f:
    w=csv.writer(f);w.writerow(['issue','topic','status','resolved','remaining','evidence']);w.writerows(issues)
report=f'''# PP-LGCM Round2B 实际执行与复核报告

生成时间（UTC）：{now}。批次目录名称沿用20261006；执行持续至2026-10-07 PDT。

## 本轮结论

家庭共享变量的插补错误已在本次工程批次中修复并通过逐成员检查；修正数据上的无约束主父模型仍未通过验收。10份父模型的状态为：{state_text}。其中{negative_count}份检出高精度负方差。没有剔除失败成员后合并，也没有继续向这些父模型追加交互。

本轮限定的来源核查、K1—K4、10份30轮分层插补及10份原队列父模型已实际执行。七项问题并未全部解决；第2项在计分与实际入口范围内可关闭，得分SE导出和家庭共同值错误是第6项中已解决的具体缺口。正式MI主结果、核心调节和H4.2b统计检验仍未形成。未执行的后续检验不等于效应为零。

## 两方意见的合并裁定

主方案采用家庭—个人分层MI，主结构控制排除wave与sat12；sat12保留为敏感性候选。CESD8为主口径，CESD20sc为敏感性口径。采用十年单位只是尺度变换，不增加变化信息。后期真实观测可作为插补辅助，不因此成为基期混杂变量。

采用ON写法澄清条件参数化，不承诺修复负方差；不把边界比较p约.90或方差不显著解释为所有人的变化相同。K4只作预定零条件残差敏感性，没有升为主模型。FIML敏感性仍须有与家庭共同变量及协变量类型相符的联合模型，本轮没有将现成模板未经方法核验即当作替代主分析。完整裁定见audit/REVIEW_DECISIONS.md。

## 实际数据来源

3274人均与补齐前2012年来源匹配，家庭键亦一致。年龄实际分类是61—75岁与76岁及以上。pinc12为自评相对收入1—5级；pinc212与finc12分别为个人、家庭收入金额，原构造除以10000。PINC412表示个人收入是否大于零。

恢复教育2人、地区1人、城乡7人、婚姻1人的基期缺失；旧婚姻补齐来自2010年，不能称为2012直接观测。家庭收入全缺失71户90人，其中19户为多成员户、52户为单成员户。城乡全缺失6户7人，地区1户1人。三项共享变量均无原观测冲突，也无可从其他已知成员直接恢复的部分缺失家庭。

主24列完整者2830。原1981人诊断集合恢复真实基期缺失后，完整者1976；K1为1981人，K2—K4为1976人，不能把比较差异全部归于控制集。

## K1—K4及条件参数化诊断

| 规格 | N | 实际结果 | 采用范围 |
|---|---:|---|---|
| K1：原26项条件ON |1981|SY条件残差−0.043055676|不可接受，仅诊断|
| K2：核实后的24项基期控制 |1976|SY条件残差−0.006640966|不可接受，仅诊断|
| K3：K2成组增加同波XY残差关联 |1976|SX条件残差−0.01790166|不可接受，不能只看SY变正|
| K4：K2的SY条件残差固定零 |1976|SY ON SX约−0.95824，SE约0.56805|受约束敏感性，不是主结果|

四次首次输入拒绝和四次修正语法后的运行都保留。输入错误未被写成估计后不收敛。TECH8不适用于普通COMPLEX估计的提示不等于模型失败。

K1与上一轮WITH联合模型的实际数据同值、同缺失；四条共同结构路径换算十年单位后均在旧打印值的舍入范围内。旧联合LL扣除同样本26项C的解析正态边际LL后，与新条件LL仍相差约0.161，不能宣称完整数值等价。该计算是参数化诊断，不是新增似然比检验；旧输出缺少高精度保存参数，不声称全部条件协方差与SE精确对应。

3274人聚类单变量的形状比较重新对应到同版本输出：校正差异统计量约8.452，df=3，p约.038。自由形状变化均值0.037、SE约0.035、p=.290，没有恢复旧显著下降结论。其自由形状因子不解释为恒定逐年斜率。

## 家庭—个人分层MI

本批m=10、30轮、seed=20261007、donors=5。finc12、urban12、prov12采用家庭层2lonly.pmm；七项个人变量采用家庭随机截距2l.pmm。实际生产脚本、方法、请求和实际预测矩阵、访问顺序、初始化规则及来源哈希均保留；微观输入和初始化对象只保存在本机。

全部10份成员共4300项检查通过，包括原观测值及有限性、目标缺失完成、家庭共同值一致、派生变量、个人/家庭键顺序、纵向指标和结构性缺失冻结。方法和预测矩阵未被自动改写，loggedEvents为0。最终PSRF范围为{mi['final_psrf_range'][0]:.6f}—{mi['final_psrf_range'][1]:.6f}；最终链图已检查，未见持续共同漂移或链间分离，方差偶发尖峰保留，没有截掉重抽。

这些结果支持本次工程数据层和链运行验收，不证明MAR、模型正确或与潜变量交互严格相容，也不证明10份足够估计所有目标。正式精度本应结合合法父模型的FMI和Monte Carlo误差评价；因父模型门未通过，本轮没有对非法结果计算正式合并或据此增加插补份数。

公开链汇总对待插补记录少于10条的变量抑制数值；其中NA是发布保护，不是插补残留缺失。地区、婚姻各只有1条待插补记录，其链内样本方差本来未定义。完整对象留本机；公开抑制规则和源/发布哈希另有回执。

## 原3274人队列父模型

全部成员使用同一科学规格：主24项基期控制，X自由形状、CESD8日历线性，十年单位，家庭聚类MLR；额外允许SX与IY的条件残差关联；SY条件残差不约束，无同波XY测量残差关联。没有因为1976人诊断样本失败而拒绝检验实际目标队列。

| 成员 | 实际估计N | 状态 | 高精度负方差 | 参数协方差已绑定 |
|---|---:|---|---|---|
{parent_table}

各成员完整INP/OUT、输入数据哈希、高精度参数、TECH1/TECH3/TECH4证据及回执已保留。TECH3是参数估计协方差，TECH4不是其替代；参数顺序、SE平方与协方差对角线、标准化协方差特征值均检查。不投影矩阵为正定，也不把打印0.000视为合法零方差。

后续处置：正式MI合并、sat12和FIML敏感性、四项核心调节、H4.2b正式三阶/组间差异、新的最小窗口矩阵均未执行。核心理由是当前无约束父规格未通过全部成员验收。K4的受约束诊断不能自动转成主规格；如后续考虑边界主模型或其他估计对象，需要先明确约束含义及适用推断，不能为取得显著结果自动扩展搜索。

## 稿件及公开交付

采用正文v47、附录v39的build03复核候选，分别39页和109页。附录103张表均有版本定位，其中98张为历史表；历史数字保留供追溯，没有冒充新估计。更新年龄、收入、控制来源、聚类数值、连续得分/给定切点二分交互术语及历史状态；build03另修4处历史wave注脚并澄清局部I4/S4符号。

原生Word导出、文本提取及页面检查已完成。build03与build02相比130页渲染像素相同，18个变化页面重新查看；5个文本节点修改的域、图像、非文本XML及其他ZIP部件保持一致。未新增引文，未做Zotero原生刷新。既有NotebookLM答复绑定build02且存在已裁定错误，不能标作build03终审通过。候选稿不是投稿定稿，正式主结果表尚未形成。

公开包仅含文稿、代码、完整模型输出、聚合核验和参数协方差。没有微观DAT/DTA/RDS/GH5、真实PID/FID、逐人得分或插补对象。网页端可核对语法、输出、版本和公开统计，不能声称已独立重跑全部CFPS记录。每包上限25,000,000字节，最终大小、文件数、SHA-256及CRC见PACKAGE_MANIFEST.json；GitHub提交和匿名下载核验在发布后另行给出。

文稿build03是父模型批次完成前冻结的编辑候选。其“预定10份30轮”等文字保留了当时状态，尚未内嵌本批最终诊断表；本次交付的最新执行状态以本报告、DELIVERY_SCOPE和完整回执为准。不将这一候选版宣称为正式分析已完成的定稿。

逐项状态见SEVEN_ISSUES.csv；读取顺序见README.md；可直接转发的复核范围见FOR_WEB_REVIEWERS.md。
'''
(root/'REPORT.md').write_text(report,encoding='utf8')
readme='''# PP-LGCM Round2B 复核资料

本次交付已完成分层MI工程批次及原队列逐插补父模型；无约束父模型未通过全部成员验收，七项问题没有全部解决。完整统计状态以报告和执行范围为准，不能从文件完整性推断模型有效。

1. [实际执行报告](REPORT.md)与[执行范围](DELIVERY_SCOPE.json)
2. [七项意见逐项状态](SEVEN_ISSUES.csv)
3. [请两家网页端复核的说明](FOR_WEB_REVIEWERS.md)
4. [证据索引](EVIDENCE_INDEX.md)、[执行索引](MODEL_INDEX.md)与[模型采用总表](audit/model_adoption_summary.csv)
5. [分层MI工程验收](audit/mi_engineering_acceptance.json)与[父模型门槛结果](audit/target_parent_gate.json)
6. [正文全文](readable/main/full.md)与[附录全文](readable/appendix/full.md)，亦可逐页读取对应目录

Word/PDF在manuscript目录，最新采用build03，是父模型批次完成前冻结的编辑候选；最终批次状态以REPORT和DELIVERY_SCOPE为准。旧版引文、历史系数和前轮NLM记录有明确来源，不作为当前有效主结果。模型目录提供完整INP/OUT及TXT镜像、高精度参数与估计协方差。

压缩包各自可完整解压，每包不超过25,000,000字节；[包清单](PACKAGE_MANIFEST.json)提供字节数、文件数和SHA-256，[逐文件清单](FILE_MANIFEST.csv)提供内部对应。两包是报告/文稿与模型/代码的分组；若超限会继续分包。浏览器可直接读取本目录文本，无需先下载ZIP。

代码用于记录本机实际执行流程；完整本机运行仍依赖未公开的合法数据、R包及Mplus。仓库没有微观分析数据或插补对象，不具备网页端全量重跑条件。小样本插补汇总的NA保护规则见audit/mi_release_policy.json。
'''
(root/'README.md').write_text(readme,encoding='utf8')
print(json.dumps({'report_generated':True,'parent_states':dict(states),'negative_variance_members':negative_count,'scientific_release':False},ensure_ascii=False))
