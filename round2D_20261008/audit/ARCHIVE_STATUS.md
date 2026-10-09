# 本轮公开文件中的历史与当前状态

正式正文v49、附录v41及其DOCX/PDF、可读文本与核验回执位于公开包的 `manuscripts/`。最终模型采用状态以 `results/family_status.csv`、`REPORT.md` 和 `evidence/independent_verification.json` 为准。

`audit/` 中名称含 `before_`、`initial_failure` 或 `original` 的文件，以及代码修复前保存的脚本，是可追溯的历史证据。它们不替代当前生产代码、最后回执或最终文稿。较早的 `IN_PROGRESS` 回执也不作为最终状态。

正文修订过程中保存的 `audit/manuscript_before_*/preview_in_progress/` 全部旧预览，以及过时的 `preview_stale_page_*` 页面图片，保留在本机但不放入正式公开包。公开包保留这些目录第一层的修订脚本和实际审阅发现，另保留母版来源绑定和文稿部件，足以区分改动来源与最终交付。此筛选只涉及重复的文稿预览，不删除任何实际模型调用、失败输出或检验结果。

`audit/maintenance_prepared_*` 是维护暂停时尚未执行的输入副本，含本地数据，整组不公开。实际提交的全部输入输出另按 `MODEL_EXECUTION.csv` 收集；个人 `data.dat`、真实PID/FID、逐人得分和插补对象始终不公开。`estimates.dat` 和 `tech3.dat` 为聚合参数及其协方差保存文件，单独列入白名单。

旧预览的视觉通过仅证明当时排版；最终稿必须通过自己的原生Word导出、逐格核对和逐页视觉验收，不能继承旧预览的PASS。
