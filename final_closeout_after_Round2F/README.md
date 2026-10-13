# PP-LGCM：Round2F之后的范围收缩收尾稿

本次完成文稿收束，**新增Mplus调用为0**。保留SW和SD E0的有效纵向关联结果，撤回未获证据支持的机制结论，完整保留原假设与失败记录。交付后停止常规追加估计和自动网页复审。

这是一份**范围收缩的最终候选稿**，不宣称原机制题目下全部检验完成，也不保证期刊接受。范围选择不是最初预设或预注册。

## 建议阅读顺序

1. [详细交付报告](REPORT.md)和[给两位网页审阅者的说明](FOR_WEB_REVIEWERS.md)。
2. [正文可读版](manuscript/delivery/main_readable.md)与[补充材料可读版](manuscript/delivery/appendix_readable.md)。
3. [正文Word](manuscript/delivery/PP_LGCM_scoped_final_candidate.docx)、[正文PDF](manuscript/delivery/PP_LGCM_scoped_final_candidate.pdf)、[补充材料Word](manuscript/delivery/PP_LGCM_scoped_supplement.docx)、[补充材料PDF](manuscript/delivery/PP_LGCM_scoped_supplement.pdf)。
4. [正文数字证据表](FINAL_EVIDENCE_MAP.csv)、[关闭／撤回／未检验表](CLOSED_AND_UNTESTED.md)、[收尾回执](CLOSEOUT_RECEIPT.json)。
5. [修改清单](CHANGELOG.md)、[表号迁移表](TABLE_NUMBER_MAP.csv)、[历史证据索引](HISTORICAL_AUDIT_INDEX.md)。

## 资料包与复核

下载本目录`PACKAGE_MANIFEST.json`列出的全部ZIP，解压到同一目录。每个ZIP严格小于等于25,000,000字节；`FILE_MANIFEST.csv`记录每项载荷的SHA-256。清单本身也在ZIP中，ZIP的哈希记录在外部包清单，避免循环哈希。

在具备Python、NumPy、SciPy、lxml和PyMuPDF的环境中运行：

```text
python -B reporting/verify_evidence.py
python -B reporting/validate_manuscripts.py
```

第一项复算保存的SW、SD E0聚合结果，核对数值映射、A19计数与TECH8轨迹；第二项核对已交付DOCX/PDF表格、字段迁移和关系完整性。它们不拟合CFPS。Windows本机原生Word导出记录和逐页视觉检查回执已交付；脚本重跑不等于重新完成视觉审查。

公开材料含稿件、聚合结果和核验代码，**不含参与者记录、真实PID/FID、原始DAT、逐人得分、MI对象或文献全文**。原题v51/v43是带明确历史标记的冻结依据，不是当前结论。原Round2F完整模型证据继续通过固定历史提交读取，无需重复补传微观数据。
