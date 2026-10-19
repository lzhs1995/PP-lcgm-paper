# 线上复核说明

本包为EDU_URBAN家族。将所有ZIP解压至同一目录后，可运行 verification/verify_pooled_h42.py EDU_URBAN --public（numpy/pandas/scipy）。该脚本独立读取原始参数与TECH3，复算完整家族的Rubin合并、直接组间差与支持范围内条件斜率，不重新拟合，也不能代替逐人数据验算。PAYLOAD_MANIFEST.json同时记录公开字节及本机源文件哈希，路径脱敏不冒称原字节相同。正文和原CFPS数据未改。H4.1、观测Z0动态敏感性和完整原潜在调节是不同目标。

本机实际独立复算入口为 verification/verify_pooled_base.R，通过ClaudeR后台R执行。解压后在R中运行 source("verification/verify_pooled_base.R"); verify_pooled_base(getwd(), public=TRUE)，需要jsonlite和digest。它从原始参数与TECH3重算，不调用生产合并器。Python备用实现保留供环境合适的读者对照；本机Python科学依赖加载曾超时，没有把该失败记作通过。
