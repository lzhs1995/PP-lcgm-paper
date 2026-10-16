# CHARLS基期控制缺失：来源与接口核验

**四项调节完整推断、完整 H4 仍未完成。**

[本批报告](REPORT.md) · [网页端说明](FOR_WEB_REVIEWERS.md) · [实际回执](BATCH_RECEIPT.json) · [ADL条目完整性](ADL_ITEM_COMPLETENESS.csv)

基期ADL来源已核清；七次合成调用保留正常、未收敛、不支持及超时结果。没有新增真实样本估计、插补或旧CFPS重跑。H4.1继续沿用3/12个完整条件家族。

解压后运行`python code/verify_public_bundle.py`核对清单哈希；`python code/verify_capability.py`独立复算保存参数与完整数据路径对照，需numpy/pandas，不调用Mplus。单包小于25MB；无个人数据或MI；DAT白名单仅为模型参数和协方差。经验见[mplusautomation-guide PR25](https://github.com/lzhs1995/clauder-rstudio-workbench/pull/25)。
