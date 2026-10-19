# 线上复核说明

本包为INC家族。将所有ZIP解压至同一目录后，可运行 verification/verify_pooled_h42.py INC --public（numpy/pandas/scipy）。该脚本独立读取原始参数与TECH3，复算完整家族的Rubin合并、直接组间差与支持范围内条件斜率，不重新拟合，也不能代替逐人数据验算。PAYLOAD_MANIFEST.json同时记录公开字节及本机源文件哈希，路径脱敏不冒称原字节相同。正文和原CFPS数据未改。H4.1、观测Z0动态敏感性和完整原潜在调节是不同目标。

本机实际参数复算使用ClaudeR后台R：source("verification/verify_pooled_base.R"); verify_pooled_base(getwd(), phase="INC", public=TRUE)，依赖jsonlite、digest。固定12项总表可运行 python verification/verify_twelve_resources_stdlib.py --public，无需科学Python包。保留原Python科学实现供可用环境对照；本机依赖加载失败不记作验收成功。
