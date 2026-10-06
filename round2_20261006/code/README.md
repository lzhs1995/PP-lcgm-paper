# 代码与复现边界

代码为本轮Windows实际使用脚本，保留路径便于本机追溯；其他环境须自行配置路径和合法数据。不要直接运行发布构建/推送脚本到其他仓库。

顺序：prepare_round2.R → run_round2.R；audit_lineage_scores.R与audit_pmm.R只读已有数据/输出；prepare_followups.py准备有限诊断，run_round2.R通过round2.manifest选取清单；summarize_round2.R导出矩阵；validate_and_collect.py独立复核原始参数。

初次准备曾遇到haven标签转换和矩阵列名断言错误，均在Mplus启动前修复。派生输入首版TITLE替换误吞DATA段，4次输入拒绝已归档。当前生成器按DATA段边界替换并检查FILE语句。现有目录实行不覆盖；复现应在新的输出根目录执行。

脚本快照包含执行后修复及报告工具；具体每次估计以对应INP/OUT及数据SHA为准，不能仅凭最新脚本推断历史输入。精确微观数据仅保存在作者本机，不在公开包中。
