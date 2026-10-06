> **2026-10-06附录补充已到位：** [附录v38、独立包03及网页复核说明](round2A_appendix_v38_20261006/README.md)。原第二轮包01、02保持不变。

> **2026-10-06最新：第二轮评审点A已执行。** 请先读[第二轮入口](round2_20261006/README.md)与[完整报告](round2_20261006/REPORT.md)。正式MI和核心调节尚未放行；下方为上一轮v45/v38历史发布说明。

# PP-LGCM七项意见：执行结果与独立复核说明

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

### 1a 趋势与时间单位：部分解决

已做：实际载荷及预测均值已核对；旧−0.218不再用于当前推断。

仍开放：自由形状与线性模型选择证据有分歧，不能按显著性选模型。

复核重点：先核对0/10锚点和当前均值，再裁定保留自由形状的理由。

稿件位置：main: XML p0=1016; PDF物理页=17。证据：[01_current_review/summaries/growth_parameter_audit.csv](01_current_review/summaries/growth_parameter_audit.csv)；[01_current_review/summaries/growth_predicted_means.csv](01_current_review/summaries/growth_predicted_means.csv)；[01_current_review/summaries/growth_fit_audit.csv](01_current_review/summaries/growth_fit_audit.csv)。

### 1b 窗口敏感性：部分解决

已做：已执行8个规格；3可审阅、3不可接受、2未收敛。

仍开放：未证明跨窗口稳健；未补估4项核心调节。

复核重点：先处理CESD8五期基准负方差，再决定必要核心关系与调节窗口检验。

稿件位置：main: XML p0=1016; PDF物理页=17。证据：[01_current_review/summaries/sensitivity_current_status.csv](01_current_review/summaries/sensitivity_current_status.csv)；[01_current_review/summaries/sensitivity_parameters.csv](01_current_review/summaries/sensitivity_parameters.csv)；[01_current_review/summaries/sensitivity_fit.csv](01_current_review/summaries/sensitivity_fit.csv)。

### 1c 样本与追访构成：部分解决

已做：T7已汇总有效波数、死亡与未知边界；2225/1981/3274分开报告。

仍开放：未识别样本选择对轨迹的因果贡献。

复核重点：判断现有描述是否足够，必要时指定少量选择性追访敏感性。

稿件位置：appendix: XML p0=18111; PDF物理页=104。证据：[01_current_review/summaries/T7_observed_waves.csv](01_current_review/summaries/T7_observed_waves.csv)；[01_current_review/summaries/T7_missing_patterns.csv](01_current_review/summaries/T7_missing_patterns.csv)；[01_current_review/summaries/T7_mortality_counts.csv](01_current_review/summaries/T7_mortality_counts.csv)。

### 1d 2016长短版：部分解决

已做：已报告额外12题推断版本的描述比较。

仍开放：官方分配标记未找到，不能宣称随机分配检验已完成。

复核重点：裁定非官方分类证据能支持的解释范围。

稿件位置：appendix: XML p0=18110; PDF物理页=104。证据：[01_current_review/summaries/T2_2016_form_comparison.csv](01_current_review/summaries/T2_2016_form_comparison.csv)；[01_current_review/summaries/T2_classification.json](01_current_review/summaries/T2_classification.json)。

### 2a CESD8计分：计分核验已解决

已做：共同8题方向与完整作答规则已核对；两口径逐人恒差8，缺失模式一致。

仍开放：不代表纵向测量不变性成立。

复核重点：核查T3/T4与正文量尺说明是否一致。

稿件位置：main: XML p0=65; PDF物理页=8。证据：[01_current_review/summaries/T3_item_means.csv](01_current_review/summaries/T3_item_means.csv)；[01_current_review/summaries/T4_scale_identity.csv](01_current_review/summaries/T4_scale_identity.csv)；[01_current_review/summaries/measurement_validation.csv](01_current_review/summaries/measurement_validation.csv)。

### 2b CESD20sc来源及量尺：计分核验已解决

已做：2012实际20题；后期官方等化分减20；2016完整长卷5304人逐人一致。

仍开放：等化分不是独立20题测量；理论20—80与样本实际范围20—72须区分。

复核重点：核对官方文件与重建规则，勿将等化敏感性视独立测量验证。

稿件位置：appendix: XML p0=18109; PDF物理页=104。证据：[01_current_review/summaries/CESD20_scale_validation.json](01_current_review/summaries/CESD20_scale_validation.json)；[01_current_review/summaries/T1_wave_scale_sample.csv](01_current_review/summaries/T1_wave_scale_sample.csv)。

### 3a 方差不显著的含义：概念修订完成

已做：不以方差显著性作为后续回归准入；当前CESD8方差已更新。

仍开放：未完成同样本同尺度四步模型链；不能用单位转换解释显著性变化。

复核重点：核对总方差/条件残差方差及模型结构差异。

稿件位置：main: XML p0=1015; PDF物理页=17。证据：[01_current_review/summaries/growth_parameter_audit.csv](01_current_review/summaries/growth_parameter_audit.csv)。

### 3b 负方差与识别：未解决

已做：保留旧诊断及本轮负方差证据。

仍开放：CESD8五期直接模型SY残差负方差，不能直接追加交互。

复核重点：提出有理论依据、预先限定的诊断顺序与停止条件。

稿件位置：appendix: XML p0=18115; PDF物理页=104。证据：[01_current_review/summaries/sensitivity_current_status.csv](01_current_review/summaries/sensitivity_current_status.csv)；[01_current_review/summaries/sensitivity_all_attempts.csv](01_current_review/summaries/sensitivity_all_attempts.csv)。

### 4a 拟合评价：部分解决

已做：已报告增值拟合与绝对拟合指标分歧。

仍开放：尚未完成必要残差结构替代及基准模型修复。

复核重点：先诊断基础轨迹和同期残差，再决定少量替代设定。

稿件位置：appendix: XML p0=18116; PDF物理页=104。证据：[01_current_review/summaries/growth_fit_audit.csv](01_current_review/summaries/growth_fit_audit.csv)；[01_current_review/summaries/sensitivity_fit.csv](01_current_review/summaries/sensitivity_fit.csv)。

### 4b 修正指数与拟合诊断：限制已记录

已做：保留RESIDUAL与失败信息，不靠降低阈值或逐条加路径达标。

仍开放：插补模型不提供修正指数；残差诊断不能由这一限制免除。

复核重点：限定使用实际可得诊断，不平均修正指数。

稿件位置：appendix: XML p0=18115; PDF物理页=104。证据：[01_current_review/summaries/sensitivity_fit.csv](01_current_review/summaries/sensitivity_fit.csv)；[01_current_review/summaries/sensitivity_current_status.csv](01_current_review/summaries/sensitivity_current_status.csv)。

### 5a 过度概括与弱证据：文字修订完成，待独立复核

已做：收缩假设及路径表述，弱证据列为探索性；撤回天花板必然保守。

仍开放：文字修订不使历史估计自动成为修正数据的正式结果。

复核重点：逐段核查是否仍有因果、阈值、全套稳健或普遍显著的残留概括。

稿件位置：main: XML p0=2745; PDF物理页=36。证据：[01_current_review/summaries/sensitivity_parameters.csv](01_current_review/summaries/sensitivity_parameters.csv)。

### 5b 性别差与指标标签：文字修订完成，待独立复核

已做：区分儿子相对女儿的差值与单方效应；最新排行标签按来源修正。

仍开放：不能从相对差值分辨儿子上升或女儿下降。

复核重点：核对表4.5.5/4.5.6、Sibling4长子及老小/幼子附加模型。

稿件位置：main: XML p0=2734; PDF物理页=36。证据：[02_evidence/historical_snapshot/existing_evidence/table455456/REPORT.md](02_evidence/historical_snapshot/existing_evidence/table455456/REPORT.md)；[01_current_review/change_logs/v45_v38_change_log.csv](01_current_review/change_logs/v45_v38_change_log.csv)。

### 6a 参照文献方法：证据不足

已做：明确不能仅凭乘积指标法一词认定与本研究相同XWITH/LMS实现。

仍开放：作者实际语法与部分全文/代码配对未确认。

复核重点：区分方法类别与实际估计器；不推断作者造假。

稿件位置：main: XML p0=104; PDF物理页=11。证据：[02_evidence/historical_snapshot/pending_actions.md](02_evidence/historical_snapshot/pending_actions.md)。

### 6b 因子得分不确定性：部分解决

已做：已汇总可得SE与得分分布，说明两阶段近似。

仍开放：未做全流程家庭bootstrap、完整误差传播或保证无偏。

复核重点：优先判断得分质量与模型目标；限定必要误差传播检验。

稿件位置：main: XML p0=1186; PDF物理页=19。证据：[01_current_review/summaries/T6_score_precision.csv](01_current_review/summaries/T6_score_precision.csv)；[01_current_review/summaries/T6_score_cutpoints.csv](01_current_review/summaries/T6_score_cutpoints.csv)。

### 6c 连续与二分调节：部分解决

已做：已报告切点、等值人数、不等大分组与交叉表。

仍开放：不能解释为已确认阈值；连续与二分并非相同假设。

复核重点：同时评价连续结果，二分保留探索性质，勿按显著性择优。

稿件位置：main: XML p0=1186; PDF物理页=19。证据：[01_current_review/summaries/T5_baseline_relationship.csv](01_current_review/summaries/T5_baseline_relationship.csv)；[01_current_review/summaries/T6_score_cutpoints.csv](01_current_review/summaries/T6_score_cutpoints.csv)；[01_current_review/summaries/T6_observed_score_crosstabs.csv](01_current_review/summaries/T6_observed_score_crosstabs.csv)。

### 6d 三过程失败定位：证据不足

已做：输入格式拒绝、估计未收敛、不可接受解已区分。

仍开放：尚无同时满足原语法、完整输出与先后顺序的最简/最后ML与Bayes失败对。

复核重点：按单过程→三过程无交互→单交互定位；缺项不得补造。

稿件位置：main: XML p0=104; PDF物理页=11。证据：[01_current_review/summaries/sensitivity_all_attempts.csv](01_current_review/summaries/sensitivity_all_attempts.csv)；[02_evidence/historical_snapshot/pending_actions.md](02_evidence/historical_snapshot/pending_actions.md)。

### 6e 多重插补合并与LRT：未解决

已做：保留25项比较与候选D2的证据边界；不平均P值。

仍开放：精确配对、嵌套、自由度、必要协方差及正式合并推断未齐备。

复核重点：判断可否用正确合并的单交互系数推断；联合检验须补齐适用条件。

稿件位置：appendix: XML p0=18119; PDF物理页=104。证据：[02_evidence/historical_snapshot/source_evidence/existing_LRT_D2_candidates.csv](02_evidence/historical_snapshot/source_evidence/existing_LRT_D2_candidates.csv)。

### 7a H4.2b判定：文字修订完成，统计仍开放

已做：保留原方向，明确未获一致支持；不比较组内星号。

仍开放：正式三阶交互/组间差异检验仍依赖MI及协方差证据。

复核重点：分别检验教育、城乡、收入差异，明确未预期结果为探索性。

稿件位置：main: XML p0=2734; PDF物理页=36。证据：[02_evidence/historical_snapshot/source_evidence/existing_LRT_D2_candidates.csv](02_evidence/historical_snapshot/source_evidence/existing_LRT_D2_candidates.csv)。

### 7b 机制解释：文字修订完成，待独立复核

已做：未测量机制作为理论解释，撤回已验证的文化归因。

仍开放：未识别生活理性、情感转向等中介机制。

复核重点：检查讨论是否仍将理论故事写成已验证机制。

稿件位置：main: XML p0=2745; PDF物理页=36。证据：当前稿件定位摘录.csv及包02缺项清单。
