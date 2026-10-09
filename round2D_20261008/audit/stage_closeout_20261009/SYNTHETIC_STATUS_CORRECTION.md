# 合成接口与实际家族状态的分类纠正

最终页面放大审阅发现：原 `07_pool.R` 判断“缺少家族文件但已有尝试”时，只匹配Z、规格和尝试名称，没有排除合成接口调用。因此，尚未启动实际CFPS估计的SD/E1和SD/H4_EDU被误标为 `INCOMPLETE_BUDGET`。

本次将该计数限定为非 `SYNTHETIC` 调用，并在原RStudio会话重新执行汇总。八个观测路线家族及三个H4家族共11项，现均正确标为 `NOT_RUN_BUDGET`。四个D0家族、四个D1家族、0项可合并交互，以及全部24次原始调用记录不变；未启动新的模型。

独立阶段核验程序 `37_verify_stage_release.py` 已补充逐家族状态检查，防止把合成测试误计为实际研究尝试。该修订只影响执行状态汇总，不改变估计核心、数据、输入、输出或MI参数合并公式。

错误的首版最终候选、原汇总脚本及当时核验结果已保存在本地 `runtime/stage_archives/final_before_synthetic_status_correction_20261009T145826/`。公开版本采用纠正后重新生成、重新核验的文稿；对应原生执行回执为 `runtime/stage_closeout_20261009/native_summary_execution_corrected.json`。
