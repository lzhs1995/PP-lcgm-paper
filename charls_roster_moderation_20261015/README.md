# CHARLS基期名册与缺失处理接续

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [网页说明](FOR_WEB_REVIEWERS.md) · [回执](BATCH_RECEIPT.json) · [包清单](PACKAGE_MANIFEST.json)

本包完成基期名册交叉核验及四份后续小试数据入口，新增Mplus为0。既有H4.1、CHARLS核心20MI和资源40MI继续引用前批437518b，不重复估计。

解压后执行 `python code/verify_public_bundle.py` 可核验公开哈希与汇总一致性。独立原始数据复算在本机已完成，微观资料不公开；请勿声称云端重新拟合。代码中的个人路径已脱敏，实际本机重现需绑定自己的授权数据。初始原始槽位拼接代码保留为有记录的探索来源，不将其缺失计数用于推断；最终采用CONSTRUCTED前缀结果。

技能经验见 [mplusautomation-guide PR25](https://github.com/lzhs1995/clauder-rstudio-workbench/pull/25)。
