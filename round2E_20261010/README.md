# PP-LGCM Round2E（2026-10-10）

本轮改为SW＋观测2012年连续Z₀，四种差异均有真实试验。只有SD E0完成十份可采用估计；四项E1调节均未形成可报告MI。H4本批不自动执行。全部尝试及失败保留，不继续潜IZ长队列。

建议网页端依次读取：

1. [阶段结论](STAGE_SUMMARY.md)
2. [完整报告：建议裁定、真实结果、待机与未竟问题](REPORT.md)
3. [可直接转发给ChatGPT/Claude的任务书](FOR_WEB_REVIEWERS.md)
4. [模型索引及全部INP/OUT](MODEL_INDEX.md)
5. [正文v50可读版](manuscripts/main_readable.md)、[附录v42可读版](manuscripts/appendix_readable.md)
6. [正文PDF](manuscripts/PP_LGCM_review_v50_round2E.pdf)、[附录PDF](manuscripts/PP_LGCM_appendix_review_v42_round2E.pdf)
7. [七项问题状态](SEVEN_ISSUES.csv)、[80目标处置](TARGET_DISPOSITIONS.csv)、[家族状态](results/FAMILY_STATUS.csv)
8. [独立验证](audit/independent/independent_verification.json)、[完整合同](contracts/RUN_CONTRACT.json)、[公开范围](DELIVERY_SCOPE.json)

资料包：[报告与稿件包第1部分](packages/01_reports_manuscripts_01.zip)、[模型与代码包第1部分](packages/02_models_code_01.zip)。若发生分拆，**以[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)列出的全部包为准**。每个ZIP≤25,000,000字节，文件级大小及SHA-256见[FILE_MANIFEST.csv](FILE_MANIFEST.csv)。

从包解压到同一目录后，可执行不接触微观数据的复核：

```text
python reporting/verify_release.py --root . --output independent_recheck --terminal
```

需Python及numpy、pandas、scipy；该命令只复算保存的模型参数、矩阵和MI，不运行Mplus。公开包不含CFPS微观DAT、真实PID/FID、逐人得分、收入记录或MI对象。estimates.dat与tech3.dat仅为模型参数/参数协方差，不能据其重拟合CFPS。

上轮固定证据：[Round2D提交cf5ab4fb](https://github.com/lzhs1995/PP-lcgm-paper/tree/cf5ab4fb9e1e59742462a7dadd85ff6fdbdb83b0/round2D_20261008)。当前是外部评议阶段交付，不是全文科学终稿；无效、未执行与未获明确支持分开报告。
