# PP-LGCM Round2B 复核资料

本次交付已完成分层MI工程批次及原队列逐插补父模型；无约束父模型未通过全部成员验收，七项问题没有全部解决。完整统计状态以报告和执行范围为准，不能从文件完整性推断模型有效。

1. [实际执行报告](REPORT.md)与[执行范围](DELIVERY_SCOPE.json)
2. [七项意见逐项状态](SEVEN_ISSUES.csv)
3. [请两家网页端复核的说明](FOR_WEB_REVIEWERS.md)
4. [证据索引](EVIDENCE_INDEX.md)、[执行索引](MODEL_INDEX.md)与[模型采用总表](audit/model_adoption_summary.csv)
5. [分层MI工程验收](audit/mi_engineering_acceptance.json)与[父模型门槛结果](audit/target_parent_gate.json)
6. [正文全文](readable/main/full.md)与[附录全文](readable/appendix/full.md)，亦可逐页读取对应目录

Word/PDF在manuscript目录，最新采用build03，是父模型批次完成前冻结的编辑候选；最终批次状态以REPORT和DELIVERY_SCOPE为准。旧版引文、历史系数和前轮NLM记录有明确来源，不作为当前有效主结果。模型目录提供完整INP/OUT及TXT镜像、高精度参数与估计协方差。

压缩包各自可完整解压，每包不超过25,000,000字节；[包清单](PACKAGE_MANIFEST.json)提供字节数、文件数和SHA-256，[逐文件清单](FILE_MANIFEST.csv)提供内部对应。两包是报告/文稿与模型/代码的分组；若超限会继续分包。浏览器可直接读取本目录文本，无需先下载ZIP。

代码用于记录本机实际执行流程；完整本机运行仍依赖未公开的合法数据、R包及Mplus。仓库没有微观分析数据或插补对象，不具备网页端全量重跑条件。小样本插补汇总的NA保护规则见audit/mi_release_policy.json。
