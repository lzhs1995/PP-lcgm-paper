# CHARLS四项基期调节小试

**四项调节完整推断、完整 H4 仍未完成。**

[本批报告](REPORT.md) · [网页端说明](FOR_WEB_REVIEWERS.md) · [实际调用回执](BATCH_RECEIPT.json) · [结果表](MODERATION_SUMMARY.csv) · [条件曲线](CONDITIONAL_SLOPES.pdf)

本批仅为已核实名册和原始核心控制完整的四个范围估计父模型与单个交互，两套起点不算多重插补。H4.1已有三个十份条件家族、CHARLS核心20份与资源40份MI，均复用既有固定证据。未重跑旧CFPS失败输入，未修改收尾稿。

ZIP小于25MB；解压后`python code/verify_public_bundle.py`检查哈希，`python code/verify_pilots.py`直接解析保存参数、TECH1与TECH3复算区间。后者需numpy/pandas/scipy，不拟合微观数据。个人data.dat及MI不公开；estimates.dat、tech3.dat只是模型统计参数。源码本机路径已脱敏。

经验沉淀见[mplusautomation-guide PR25](https://github.com/lzhs1995/clauder-rstudio-workbench/pull/25)。
