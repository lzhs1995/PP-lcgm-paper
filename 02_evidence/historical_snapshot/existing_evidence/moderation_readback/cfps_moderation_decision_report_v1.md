# CFPS PP-LGCM 调节效应诊断与后续决策（2026-10-04）

## 运行边界

本次通过在线 `default@8787` RStudio/ClaudeR 会话，对既有 Mplus `.out` 做
`MplusAutomation::readModels()` 只读回读。没有启动 Mplus，没有重新估计，没有
修改六份 R script、原始数据、原始 `.inp/.out` 或论文 DOCX。R 入口脚本为
`work/cfps_moderation_readback_20261004.R`。

## 观测到的既有输出

- 选取 56 个已存在的调节模型输出，成功读回 56/56 个文件。
- 读出 168 行交互参数；其中 12 行报告的 p<.05，21 行报告的 p<.10。
- 这些计数包含多个历史文件/规格变体，不能作为“12 个显著调节效应”，也不能
  用来选择最小 p 值的模型。
- 图形审查显示：type1 的低 p 值行相对集中，type3/4 的区间更宽、标准误更大，
  urban 相关行的 p 值整体没有形成稳定的低值聚集；这只能提示精度和样本/规格差异
  值得检查，不能解释为某个调节假设已经成立。
- 按模型族和调节变量的原始计数见 `cfps_moderation_summary_v1.csv`；参数和
  近似区间见 `cfps_moderation_parameter_readback_v1.csv`；图形仅用于审计：
  `cfps_moderation_pvalue_distribution_v1.png` 和
  `cfps_moderation_effect_intervals_v1.png`。

## NLM 来源复核

NotebookLM 已在 PP-LGCM 验证笔记本上完成来源问答。原始回答与后续决策矩阵保存在
`reports/nlm_moderation_review_20261004/nlm_decision_matrix_v1.json`。它确认：
历史连续交互多数不显著；若干二分交互或历史简单斜率不能替代正式的交互和 MI/LRT
验收；单组简单斜率显著而另一组不显著，不能推出组间差异显著。

## 可以立即做的工作

1. 在现有输出上继续做 B1：只在十个插补成员的配对似然、自由参数数和修正量均有
   完整证据时重建 D2；当前 CFPS 科学门仍规定正式 LRT p 值释放为 0，不能用算术
   平均 p 值替代。
2. 做 B2：从同一已验收模型的条件斜率和参数协方差中直接检验高低组斜率差，而不是
   比较两条单独 p 值。
3. 做 B3：把近零/负的 `S5` 条件残差方差作为边界敏感性诊断，比较点估计、SE 和
   诊断，不因 p 值变好而自动采用约束模型。

## 只有预注册后才能新估计的候选

完整三过程 LMS、时变协变量敏感性 PP-LGCM、以及年龄轴队列序贯模型都只是理论上
可能的检查，不能写成已发现的显著效应。每一项都必须在隔离目录中运行，保留所有
尝试及失败记录，并在当前内存达到准入门槛、MI 数据诊断通过、模型收敛且无鞍点/边界
警告后才可进入正式比较。

## 禁止的“追求显著”做法

禁止按 p 值事后选择增长形态、从连续变量改成二分以获得显著、删除会削弱结果的控制
变量、只报告显著简单斜率、平均 MI p 值、报告不可比 LRT、隐藏失败或收敛警告，以及
把现有历史候选当作科学接受结果。可以提高的是估计的可解释性、测量质量和功效；不能
预先承诺 p<.05。

## 当前项目位置

CFPS 的历史复现和 provenance 层已基本冻结，但 scientific release 仍开放；CHARLS
的 90 个引用虽已读回，formal adoption/scientific acceptance 仍未关闭；
`mplusautomation-guide` 已将本次 Windows 只读回读、变体分类、资源门控和禁止 p-hacking
经验加入开发副本，仍是 draft，未提交 GitHub release。8787/8789/8786 均在线；最新
只读 spot check 的物理可用内存约 1.616 GiB。当前唯一 Mplus 属于第四章
`scientific_audit_20261002/experiments/income_candidate_full_20261004/models/apimom_total_edu-child-op`
外部审计，明确不计入 CFPS/CHARLS，因此本次没有 CFPS/CHARLS 新 Mplus 运行。
