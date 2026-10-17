# PP-LGCM 原假设覆盖与零新增估计的补充对比

[统一报告](REPORT.md) · [56行覆盖表](EVIDENCE_COVERAGE_56.csv) · [12项补充结果](MEAN_CHANGE_RESOURCE_AT_Z0.csv) · [图](MEAN_CHANGE_RESOURCE_AT_Z0.pdf)

四项原CFPS调节完整推断、完整H4仍未完成。CHARLS登记的条件分析已完成，不等于原稿全部估计对象均已覆盖。

本包只含新汇总及复算所需320条模型参数记录，不含个人数据，不重打包旧原始输出。解压后用带scipy的Python执行 `python code/verify_and_summarize.py --public`，可独立核对12项对比；新Mplus/MI调用均为0。旧完整模型及TECH3公开链接见报告。

R脚本用于记录实际原生提取流程；重新执行其完整本机流程还需原批次汇总文件，不能将本包误称为包含全部微观资料的独立估计包。
