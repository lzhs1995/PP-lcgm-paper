# CHARLS 教育家族：有限社区数敏感性修正

2026-10-22。此包仅修正 gender、oldest、son 三个教育家族的派生敏感性表。

旧代码与独立验证器同时沿用了 `dfcom=437`，因此数值一致性检查没有发现来源语义错误。按本项目已使用的“社区数减一”敏感性约定，实际应分别使用 431、432、432。该约定是敏感性分析，不是聚类稳健推断的精确有限样本校准。

`recompute.R` 在原生 RStudio 中读取全部保存的参数/协方差和实际 DAT 社区数，写出新的修正表；原目录、原 Mplus 输出与主要结果均未覆盖。`verify.py` 独立复算 3×134 参数及 3×21 对比并核对主要结果哈希。

请用各指标子目录内的 `POOLED_CLUSTER_DF_CORRECTED.csv` 与 `CONTRASTS_CLUSTER_DF_CORRECTED.csv` 替代旧包的 `POOLED_CLUSTER_DF.csv` 和研究对比中的 `cluster_*` 敏感性列。原始主要 Rubin 推断和 `PRIMARY_H42.csv` 不变。

公开包不含个人记录、DAT 或 MI 对象。本地完整验证依赖已有隔离源目录；公开文件支持检查修正结果及来源哈希。

原 son `TERMINAL.json` 的 `A_members=21` 是计数标签错误：实际为20个A加1个B，不能按21份插补解释。以合同 `primary_sequence` 与 `MEMBER_SOURCES.csv` 的20个成员为准。

早前 `local-1` 的 SMOKE/GUARD JSON 是代理手工任务摘要，不能当作可执行 harness 的验收凭证；工具调用确已发生，但不应将该记录称为正式门禁通过。本批后续恢复已经使用真实 harness 的 `native-smoke`、`async-guard` 和原始工具回执。

新增 Mplus=0，新增 MI=0。**四项调节完整推断、完整 H4 仍未完成。**
