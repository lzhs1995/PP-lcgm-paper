"""从已核验终态结果编制公开报告及网页端反馈说明。"""
from pathlib import Path
from datetime import datetime,timezone
import csv
import json
import shutil
import pandas as pd
from build_manuscripts import Results,seven_rows,hypothesis_rows,ZN

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def mdtable(headers,rows):
    def safe(x):return str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+
      ['| '+' | '.join(map(safe,r))+' |' for r in rows])
def write(name,s):(OUT/name).write_text(s,encoding='utf-8')


def main():
    r=Results();summary=read(OUT/'EXECUTION_SUMMARY.json')
    independent=read(ROOT/'audit/independent/independent_verification.json')
    families=pd.read_csv(ROOT/'results/FAMILY_STATUS.csv')
    pool=pd.read_csv(ROOT/'results/POOLED_KEY_PATHS.csv')
    mult=pd.read_csv(ROOT/'results/MULTIPLICITY.csv')
    execution=pd.read_csv(OUT/'EXECUTION_DETAILS.csv')
    fits=pd.read_csv(OUT/'E0_FIT.csv');sd=fits[fits.id.str.startswith('CFPS_SD_')]
    feature=['1 趋势、时间、窗口','2 CES-D计分','3 方差与识别','4 拟合','5 表述','6 调节与MI','7 H4.2b']
    issues=seven_rows(r)
    pd.DataFrame(issues,columns=['issue','status','scope']).to_csv(OUT/'SEVEN_ISSUES.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(hypothesis_rows(r),columns=['hypothesis','original_prediction','current_scope']).to_csv(OUT/'HYPOTHESES.csv',index=False,encoding='utf-8-sig')
    ft=mdtable(['分支','E0无交互','E1连续调节','最终MI'],[
      ['SD','10/10通过','MI01及一次修复均为SY负残差','仅E0可合并'],
      ['性别差','MI01及修复SX、SY负残差','首试估计失败；修复跨待机后超时','不可合并'],
      ['老大差','MI01—05通过；MI06的SY为负','MI01的SY为负','不可合并；未删MI06'],
      ['长子差','MI01及修复SY为负','MI01的SY为负','不可合并']])
    pr=[]
    for _,p in pool.iterrows():
        h=mult[(mult.z==p.z)&(mult.spec==p.spec)&(mult.label==p.label)]
        pr.append([p.label,f'{p.estimate:.6f}',f'{p.se:.6f}',f'[{p.lower:.6f}, {p.upper:.6f}]',f'{p.p:.6f}',f'{h.iloc[0].holm:.6f}' if len(h) else '不在该校正族'])
    paths=mdtable(['SD E0路径','估计','SE','95%条件MI区间','P','固定4项Holm P'],pr)
    versions=read(ROOT/'reporting/context_evidence/REPORT_CODE_VERSION_CHAIN.json')
    vr=mdtable(['文件','中间快照SHA-256','最终本机/发布SHA-256'],[
      [x['file'],x['interim_stage_sha256'],x['final_local_sha256']] for x in versions['versions']])
    write('REPORT.md',f'''# PP-LGCM Round2E：本机执行、共识裁定与未竟问题

本批已终止估计并完成聚合独立复核。四种“SW＋实际2012年连续Z₀”均有真实E0/E1首份试验；只有SD的E0取得完整十份可采用估计。**四项E1调节均没有可报告的MI推断。** 本批不再启动潜IZ队列，H4按已确认的“先交付本批，再议H4”安排延期。

这是用于进一步评议的研究阶段交付，不是整篇论文全部假设已完成、所有结果无效或所有调节不存在的结论。

## 1. 对两方建议的本机裁定

两方关于“保留SW、观测Z₀优先、完整合法起点、实际支持点、有限预算和全部失败保留”的方向合理，已落实。SW仍保留五个同波X—Y残差协方差、家庭聚类、MLR和原控制集。C1在结构上嵌套于SW，但其零方差边界意味着普通df=6卡方参照不能直接当作正式边界检验；本轮没有再跑父模型修复。

以下建议经过复核作了限定，而非原样执行：

| 议题 | 本批采用规则及理由 |
| --- | --- |
| “负SY且z>−1.96就全族sy@0” | 不采用为自动主要家族规则。不显著的负方差不证明真实方差为0；选择边界模型也改变假设。只预留SD同一成员的E0B/E1B各一次诊断，不替换自由家族。 |
| 直接拼接整段SVALUES | 保留目标完整语法，按高精度BY/ON/WITH/均值/方差语义键映射共同自由参数。用起始值*，不把它们固定为@；不剪裁负方差，不默认回退。 |
| 替代起点失败或LL更低也通过 | 不接受。只有预定数值一致性满足才可通过；失败不是稳定性的证明。 |
| 101次正常路径扩为201次 | 未扩张；101含合成调用，8小时引擎/10小时墙钟是总预算。最多4次修复、2次单成员边界诊断。 |
| 再做60分钟潜路线小试 | 本批不执行，防止继续长队列挤占可交付工作。 |
| 自动接H4 | 按用户选择不自动接续。本批H4调用0。 |
| “观测Z₀误差一定衰减调节” | 不作此断言；非法D0导出的所谓信度不作正式证据。观测Z₀与潜IZ的估计对象确已不同。 |
| “相容性问题仅剩一个乘积项” | 只能确认当前插补没有完整SX×Z₀的相容联合结构；不能证明其他相容性问题不存在或影响较小。 |
| H4任意方向同向幅度更大 | 不能验证原文“弱化更强”。缓解、弱化需分别绑定方向及边际关系；同一交互不是两项独立发现，SX变化也不等于IX初始水平。 |

## 2. 数据准入和实际执行对象

复用Round2D四分支各10份私有分析文件，40/40哈希、人数、家庭数、Z₀及控制列秩通过本机准入核验。SD为3274人/2410户，性别差2339人/1730户，老大差3159人/2320户，长子差2894人/2134户。没有取分支交集、强制五期平衡、把结构性无定义填0或重新插补。详见[数据绑定](contracts/DATA_BINDING.csv)。

E0＝SW＋ix/sx/iy/sy对Z₀回归＋x1/y1对Z₀回归。E1只增加`SX XWITH Z₀`及其对SY的回归。X中间载荷自由，端点0/1；Y为0/.4/.6/.8/1。SX是自由基底的端点变化，不是恒定年增长率；SY是十年日历线性近似。

CFPS估计由原生ClaudeR作业`8a148647`执行，未重复提交；前置作业`7e08df97`完成17项R自检、5项预算/恢复自检、6次真实Mplus合成调用及9项接口核查。合成成功不计作CFPS实证发现。队列冻结的7个源文件哈希在每次准入前检查，本批估计后未修改；文稿与复核脚本在独立reporting目录。后续原生查询返回“No job found”，不把该响应当完成证明；终态以已落盘队列、34份引擎回执、结果及独立复核确认，详见[原生证据说明](audit/NATIVE_EVIDENCE_NOTE.md)。

## 3. 真实结果和处置

{ft}

共34次Mplus调用＝6次合成＋26次主要CFPS尝试（含修复）＋2次SD边界诊断。23次USABLE包含6次合成、15次无交互E0成员和2次边界诊断，**不是23项实证发现**。另有9次不合法解、1次估计失败、1次超时。完整80个原定E0/E1目标逐个保留执行或停止原因，见[目标处置表](TARGET_DISPOSITIONS.csv)。

自由E1的首份未通过，故未准入15→20点、替代完整起点稳定性或真实1核—4核配对；这些检查是未执行，不是已经通过或又一次失败。没有因P值选择分支。四次修复配额已用于性别差E0、长子差E0、SD E1、性别差E1；老大差MI06没有剩余修复配额，也未删除它或混合约束家族。

SD E0的CFI为{sd.CFI.min():.6f}—{sd.CFI.max():.6f}，RMSEA为{sd['RMSEA : Estimate'].min():.6f}—{sd['RMSEA : Estimate'].max():.6f}；十份成员合法。逐份拟合统计是描述，未把CFI、χ²或P值平均后当合并检验。条件MI路径为：

{paths}

`gi0`、`gs0`分别是实际基期差异与抑郁潜基期、变化的条件路径；区间均跨0。较高亲近度基期与较低抑郁基期的关联仍可报告，但不代替调节。SD差异的估计不能解释为“没有效应”，也不能据此宣布H1.2已否定。完整总方差、FMI和MCSE/SE见[合并结果](results/POOLED_KEY_PATHS.csv)。

SD MI01的E0B/E1B固定SY条件残差为0后，单份均通过基础合法性检查。E1B的δ＝−0.257156，SE＝0.166587，**只是一份固定模型诊断**；未通过独立积分/起点精度配对，未形成十份MI，也未取代主要E1。它表明该约束可改变当前可估计性，不能证明真实方差为0或原假设已成立。证据见[边界诊断](results/SD_BOUNDARY_DIAGNOSTIC.json)及[原始模型](models/CFPS_SD_E1B_01_diagnostic/model.out.txt)。

## 4. 耗时与待机：不能把墙钟都解释为计算

累计引擎占用墙钟{summary['engine_wall_seconds']:.2f}秒（{summary['engine_wall_seconds']/60:.2f}分钟），包括合成及待机；批次从{summary['batch_started_utc']}到{summary['queue_terminal_utc']}，至队列终态{summary['batch_wall_until_queue_terminal_seconds']/60:.2f}分钟。累计已记录进程CPU约{summary['cpu_seconds_recorded']:.2f}秒，属于采样量，不等于精确CPU计费。总预算未耗尽，停止由各分支失败及合同规定决定。

性别差E1修复存在真实的名义单次上限超出：limit＝1800秒，回执2002.49秒，超出202.49秒。Windows Kernel-Power记录04:02:09.269进入新型待机，04:28:58.636恢复；CPU仅增加很少，恢复时监督器终止自有进程。完整时间仍计入预算，未裁剪成1800秒，未补跑。[电源事件](audit/SYSTEM_POWER_EVENTS.json)、[超时回执](models/CFPS_SEXGAP_E1_01_q15_repair/engine_receipt.json)、[耗时表](PERFORMANCE_FINAL.csv)均保留。

因此，本轮大部分观测交互在几十至百余秒内形成终态，主要障碍仍是参数合法性；性别差这一次不能称为33分钟持续数值计算。不同模型、积分维数和起点都已变化，这不是对上一轮同一模型的受控加速实验。合成4核接口通过，但实际SD E1不合法使真实配对未触发，故不承诺4核加速幅度。后续若另批估计，应事前保持系统唤醒，继续区分引擎墙钟、进程CPU与主机待机。

## 5. 支持点、MI和H4边界

SD原始零对应标准化Z₀＝−0.475926；−1反算为负的原始SD，不用作主展示点。参考点已在实际估计前冻结，含原始零、正值中位数和P90；有符号分支按P10/P90与非零侧中位数规则处理。±0.1标准化单位附近的人数、家庭数均在[支持点表](contracts/SUPPORT_POINTS.csv)。本批没有合法E1家族，故没有伪造条件斜率；保留参考点不表示该斜率已估计。

十份现有家庭—个人MI继续复用。只插补基期控制变量，不把纵向Z、死亡后的结局或结构性资格差值插补出来；基期Z和后期X/Y进入预测不证明与SX×Z₀严格相容。原预测矩阵覆盖、目标、链诊断和本轮条件推断范围随[相容性审计](reporting/context_evidence/round2D/audit/MI_CONGENIALITY_AUDIT.json)提供。低FMI不等于纵向缺失少或区间精确。

H4三资源的1编码已核对为初中及以上、城市、个人收入金额>0；最后一项不是高收入。原H4.2a/b全文保留。δG＝δ1−δ0是正式组间问题，必须分开统计差异与原预测成分；不能比较两组星号，也不能将任意交互绝对幅度更大判为整项H4.2b获支持。本批没有执行H4，也没有计算九项同时区间。

## 6. 文稿与文献核对

正文v50、附录v42以本轮实际E0/E1替换旧空表，将三过程失败集中到历史原因表；SW原结果继续保留。新稿使用真实支持点，补正A9/A10范围、2012年原始零值限定和H4成分。Word引用指令原字节保留，显示的两作者引用统一；没有全库Zotero刷新。

本机确实找到并抽取三篇PDF，针对所涉段落核对：Li & Zhang（2023）p.925及930—932支持纠正抑郁方向；Zhang等（2025a）p.2089、2093—2094、2111—2112要求“最远关系”限定并区分类型异质性与SX×Z乘积；Zhang & Liu（2024）p.3871确认固定基期标准化出处。[定位与来源哈希](reporting/context_evidence/LITERATURE_VERIFICATION.csv)公开，文献全文不随包发布。没有声称所有参考文献逐篇重审。

稿件是外部评议阶段版本。局部源证据、数值、表格和页面检查不等于整篇论文的最终科学接受；本轮未完成NLM三轮审稿，亦不以旧版本NLM记录替代新稿审阅。

## 7. Round2D报告脚本哈希不一致的解释

`changed_bound_sources.json`记录的是中间收口快照。之后公开的`PROSE_SYNC_20261009.md`修正了“未执行H4”的措辞，`SYNTHETIC_STATUS_CORRECTION.md`修正了将合成调用计入实际家族的状态错误；最终文件另有变化。逐字节核对确认最终本机文件与Round2D已发布文件一致。中间清单没有同步更新是溯源文档缺口，应说明而非改写旧包。

{vr}

这里还区分估计和汇总：后一次修正包括`07_pool.R`的家族执行状态判别，不改变24份原始调用、输入输出、数据或MI参数合并公式。已保留最终状态修正原生回执；不能笼统把所有变更都说成纯排版。详见[版本链](reporting/context_evidence/REPORT_CODE_VERSION_CHAIN.json)。

## 8. 独立复核、七项状态及下一步

本轮验证不再使用“全包读过”替代具体范围：40份私有数据准入；全部34次当前调用；{independent['printed_rows']}行打印参数；{independent['free_parameters']}个高精度自由参数及TECH3协方差；{independent['matrices']}个适用矩阵；{independent['full_start_slots_verified']}个语义起点槽；1个完整家族的Rubin/FMI及固定族Holm复算。失败/超时空TECH3按真实失败保留。[独立复核结果](audit/independent/independent_verification.json)与可公开重算程序一同提供；公开包不包含微观数据，不能据此重新拟合CFPS。

{mdtable(['原问题','状态','范围'],issues)}

本批结束后不再自动估计。下一轮先请两方针对本轮真实证据回答有限问题：是否值得将保留SW的SD E1B作为明确强约束敏感性设计完成完整MI与精度核查；如何处理仍未解决的自由SY估计；H4能否在该明确前提下另立合同，以及应否先做信息/形状诊断。没有新的科学规格和预算就不恢复潜IZ长队列，不因剩余时间继续加跑。

推荐阅读入口为[网页端反馈任务书](FOR_WEB_REVIEWERS.md)。任何下一轮建议都应保留“合法但不精确”“目前不可采用”“尚未执行”的区别，并说明改变了什么估计对象。
''')
    write_other_reports(r,summary,independent,ft)
    print('REPORTS_WRITTEN',flush=True)


def write_other_reports(r,summary,independent,ft):
    write('STAGE_SUMMARY.md',f'''# Round2E阶段结论

本批执行完成，H4按用户选择留待交付后再议。34次调用（6合成、28实际CFPS），没有新增潜IZ模型。主要E1调节0/4家族可合并，SD E0为唯一完整可采用家族。

{ft}

SD E0：Z₀→抑郁基期−0.006315，95%区间[−0.098233, 0.085603]；Z₀→抑郁变化0.033769，[−0.145789, 0.213328]；两项固定四分支Holm P均为1。不要将区间跨0解释为效应不存在。

两个SD MI01固定SY＝0诊断均通过单成员基础检查；E1B的δ＝−0.257156、SE＝0.166587，仅作约束诊断，没有十份MI或积分/起点精度配对。

引擎占用墙钟{summary['engine_wall_seconds']/60:.2f}分钟，至队列终态墙钟{summary['batch_wall_until_queue_terminal_seconds']/60:.2f}分钟；其中一次性别差修复跨越约27分钟系统待机，回执2002.49秒、记录CPU331.09秒，恢复后终止。单次名义上限超出202.49秒已公开，全部时间照实计入预算。

独立核验覆盖34调用、{independent['free_parameters']}高精度参数、{independent['printed_rows']}打印行、{independent['matrices']}适用矩阵、{independent['full_start_slots_verified']}起点槽，以及唯一完整家族的MI/FMI/Holm重算。正文v50、附录v42为评议阶段稿。

七项意见：第2项关闭；第3/4项在SW层面关闭；第1/5/6项仍有未竟范围；第7项H4.2b未执行。完整依据见[报告](REPORT.md)和[后续评议问题](FOR_WEB_REVIEWERS.md)。
''')
    write('README.md','''# PP-LGCM Round2E（2026-10-10）

本轮改为SW＋观测2012年连续Z₀，四种差异均有真实试验。只有SD E0完成十份可采用估计；四项E1调节均未形成可报告MI。H4本批不自动执行。全部尝试及失败保留，不继续潜IZ长队列。

建议网页端依次读取：

1. [阶段结论](STAGE_SUMMARY.md)
2. [完整报告：建议裁定、真实结果、待机与未竟问题](REPORT.md)
3. [可直接转发给ChatGPT/Claude的任务书](FOR_WEB_REVIEWERS.md)
4. [模型索引及全部INP/OUT](MODEL_INDEX.md)
5. [正文v50可读版](manuscripts/main_readable.md)、[附录v42可读版](manuscripts/appendix_readable.md)
6. [正文PDF](manuscripts/PP_LGCM_review_v50_round2E.pdf)、[附录PDF](manuscripts/PP_LGCM_appendix_review_v42_round2E.pdf)
7. [七项问题状态](SEVEN_ISSUES.csv)、[80目标处置](TARGET_DISPOSITIONS.csv)、[家族状态](results/FAMILY_STATUS.csv)
8. [独立验证](audit/independent/independent_verification.json)、[完整合同](contracts/RUN_CONTRACT.json)、[公开范围](DELIVERY_SCOPE.json)

资料包：[报告与稿件包第1部分](packages/01_reports_manuscripts_01.zip)、[模型与代码包第1部分](packages/02_models_code_01.zip)。若发生分拆，**以[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)列出的全部包为准**。每个ZIP≤25,000,000字节，文件级大小及SHA-256见[FILE_MANIFEST.csv](FILE_MANIFEST.csv)。

从包解压到同一目录后，可执行不接触微观数据的复核：

```text
python reporting/verify_release.py --root . --output independent_recheck --terminal
```

需Python及numpy、pandas、scipy；该命令只复算保存的模型参数、矩阵和MI，不运行Mplus。公开包不含CFPS微观DAT、真实PID/FID、逐人得分、收入记录或MI对象。estimates.dat与tech3.dat仅为模型参数/参数协方差，不能据其重拟合CFPS。

上轮固定证据：[Round2D提交cf5ab4fb](https://github.com/lzhs1995/PP-lcgm-paper/tree/cf5ab4fb9e1e59742462a7dadd85ff6fdbdb83b0/round2D_20261008)。当前是外部评议阶段交付，不是全文科学终稿；无效、未执行与未获明确支持分开报告。
''')
    write('FOR_WEB_REVIEWERS.md','''# 给ChatGPT网页端与Claude网页端的Round2E反馈

请直接读取本目录README、REPORT、STAGE_SUMMARY、MODEL_INDEX及同版正文v50/附录v42；需要批量复核时下载PACKAGE_MANIFEST列出的全部ZIP，解压到同一目录，核对FILE_MANIFEST及运行reporting/verify_release.py。所有新调用的INP/OUT另有等字节.txt镜像。

本机执行已结束。无需我补传全量CFPS，也不要把公开聚合复算说成重新拟合微观数据。本轮34次调用、40份私有文件准入、1个可合并SD E0、0个可合并E1。SD/老大差/长子差自由E1首份出现SY负残差；性别差首试失败，修复跨系统待机后超时。老大差E0 MI01—05可用，MI06不合法，未删MI06合并。两个SD单份固定零诊断可用，但并非完整核心结果。

我采纳了观测Z₀优先、保留SW、全参数合法起点、真实支持点和预算停止。没有采纳“负方差不显著即全族固定零”“替代起点失败算稳定”“非法D0信度证明误差衰减”“剩余预算继续潜模型”这些推断。H4依用户选择未自动接续。

请围绕以下具体问题形成有终点的建议：

1. 在自由SD E1失败、同一成员E1B通过基础合法性但尚无精度配对的证据下，是否值得把E1B定义为**明示强约束的敏感性规格**，另批完成10份MI及积分/起点检查？若不建议，请给出保留核心理论估计对象且计算预算明确的最小替代。
2. SY接近0与本模型的方差分解应怎样解释？请区分样本负估计、模型误设、弱信息与形式识别，不把不显著负方差证明为总体0，也不因单份边界结果可用就认定原假设获验证。
3. 老大差E0再次在MI06触边，其他分支也有不合法成员。下一轮应允许哪一种预先固定的全族处理？请明确约束含义、合法性检查和推断边界，不删成员、不逐项调残差直到显著。
4. 若未来采用强约束SD工作规格，H4应该在哪些前提下开展？H4原文含缓解与弱化两成分；SX变化与IX水平并非同一个操作化。请分别给出系数、条件斜率、资源组间差值和理论方向的对应，不能用任意同向绝对幅度更大替代“弱化更强”。
5. 现有MI含基期Z及后期X/Y辅助项、未建立SX×Z₀相容联合结构。最有信息量的有限敏感性应是什么？不要把“仅缺乘积项”或“偏差必定衰减”当已验证结论。
6. 计时中已发现真实系统待机事件，单次墙钟超限202.49秒完整记账。大多数观测E1在几十至百余秒出结果，实际SD 1核/4核配对未触发。请区分性能问题与统计可采用性，不再只建议增加数小时或积分点。

请同时核对新稿的文献修正：Li & Zhang（2023）方向、Zhang等（2025a）“最远关系”限定及类型异质性、Zhang & Liu（2024）固定基期标准化出处。三篇原文已在本机核对，定位和哈希附于LITERATURE_VERIFICATION；没有全文公开授权的PDF未上传。

希望你们返回：①七项意见逐项状态；②接受/拒绝各候选路线的统计理由；③一个事前固定的后续模型合同（规格、样本、参考点、边界规则、完整MI、精度容差、调用/时间上限和停止规则）；④稿件应保留的最小结论。不要默认启动H4、潜IZ、窗口、量尺、Bayes或得分两阶段大全套。下一轮只在明确合同后执行。
''')
    modelrows=[]
    for p in sorted((ROOT/'models').glob('*/receipt.json')):
        x=read(p);prefix='models/'+x['id']
        modelrows.append([x['id'],x['sample'],x['status'],f'{x["seconds"]:.2f}',
          f'[INP]({prefix}/model.inp.txt) / [OUT]({prefix}/model.out.txt)',
          f'[起点]({prefix}/start_mapping.csv) / [回执]({prefix}/receipt.json)'])
    write('MODEL_INDEX.md','# 全部实际调用索引\n\n包含失败、超时与合成；USABLE不等于完整MI采用。源字节与TXT镜像一致。\n\n'+
      mdtable(['调用ID','数据','状态','引擎墙钟秒','原始文件','审计'],modelrows)+'\n')
    manifest=ROOT/'manuscript/delivery/manuscript_validation.json'
    visual=ROOT/'manuscript/delivery/visual_review.json'
    ready=manifest.exists() and visual.exists() and read(manifest)['status']=='PASS' and read(visual)['status']=='PASS'
    scope=dict(release_type='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW',round='Round2E',preview=False,
      ready_for_publication=ready,scientific_project_complete=False,public_microdata=False,
      independent_status=independent['status'],H4='DEFERRED_BY_USER_STAGE_CHOICE',
      primary_E0_families_adopted=1,primary_E1_families_adopted=0,calls=34,
      public_content='aggregate model outputs, parameters, covariance, code, contracts, reports and review manuscripts',
      excluded=['microdata','participant PID/FID values','individual scores','income records','MI objects'],
      explicit_deviation='One nominal 1800-second wall cap ended at 2002.49 seconds after recorded system standby; fully charged, no retry added.',
      NLM_three_pass='NOT_PERFORMED_FOR_THIS_STAGE',
      created_utc=datetime.now(timezone.utc).isoformat())
    write('DELIVERY_SCOPE.json',json.dumps(scope,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
