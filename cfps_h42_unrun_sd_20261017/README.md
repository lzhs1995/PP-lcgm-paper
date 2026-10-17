# CFPS 两项H4.2首次尝试的诊断包

[报告](REPORT.md) · [清单](PACKAGE_MANIFEST.json)

ZIP小于25MB；只含模型语法、原始输出、参数及协方差、代码和聚合回执。没有微观DAT。解压后可用numpy/pandas/scipy执行 `python code/verify_new_attempts.py --public` 独立复算保存参数和负方差裁定；不启动Mplus。

公开文件只作路径脱敏，清单分别保留原文件SHA-256和分发SHA-256。未形成完整MI推断，不能用失败输出支持或否定研究假设。既有CHARLS和CFPS历史成果不重打包。
