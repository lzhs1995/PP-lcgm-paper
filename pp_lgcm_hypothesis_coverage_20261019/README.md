# PP-LGCM 原假设与当前结果覆盖

先读 [REPORT.md](REPORT.md)，再看 [31个当前CHARLS家族](CHARLS_CURRENT_31_FAMILIES.csv) 与 [原稿五路径覆盖](ORIGINAL_FIVE_PATH_COVERAGE.csv)。

**四项调节完整推断、完整 H4 仍未完成。** 31个CHARLS条件工作MI家族、800个模型成员条目不等同原CFPS目标全部完成。本包新增估计/MI/NLM均为0，冻结稿不变。

复核包：[PP_LGCM_Hypothesis_Coverage_20261019.zip](PP_LGCM_Hypothesis_Coverage_20261019.zip)。大小与SHA见 [PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)。解压后运行 `python code/verify_packet.py`；只需Python标准库。它核对聚合来源、路径覆盖与四个预设集合的Holm值，不重新拟合或冒称重新独立验证800份原始参数。

完整模型证据沿用报告内固定提交。不需要重新上传原数据。本包不含逐人DAT/RDS/MIDS或账户信息。正文与附录均未修订，不开启新的网页端/NLM循环。
