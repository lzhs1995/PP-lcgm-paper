# SON 指标标签更正（2026-10-18）

CHARLS 本批的 SON 是“长子与其余所有子女的联系频率差”，其余子女包括女儿。它不是“长子与其他儿子的差”，因此部分中文报告中的“儿子内排行差”应作此更正。

基期证据：`charls_roster_moderation_20261015/code/audit_constructed_roster.R` 的 `rankgap()` 先在男性子女中选唯一最早出生者，再把该布尔组交给 `gap(v,g)`；后者返回 `mean(v[g])-mean(v[!g])`，没有把比较组限制为男性。

后续波次证据：`charls_latent_trajectory_readiness_20261018/code/derive_strict_coverage.R` 的 `value()` 使用相同的 `g <- a & birth == min(birth[a])`，其中 `a` 只约束被选定的长子，比较组仍为全部 `!g`。`source_inventory.R` 原合同也称 `oldest-son-minus-others`。

本次核对确认基期与后续公式一致。缺少儿子、出生年并列、子女信息缺失仍分开记录；不任意拆解并列。修正仅涉及报告标签，既有数值、输入、插补、模型和原始输出未改变。不能为修正中文标签而重跑已完成的 H4.1 家族。

公开的历史包应保留原样，并以此勘误链接说明；后续报告统一采用“长子与其余子女差”。该指标也不等同于 CFPS 情感亲近度指标。
