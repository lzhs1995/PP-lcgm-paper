# CHARLS四项动态调节：工作插补敏感性批次

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [条件结果](FOUR_MODERATIONS.csv) · [完整案例对照](CC_MI_COMPARISON.csv) · [区间图](FOUR_MODERATIONS.pdf) · [包清单](PACKAGE_MANIFEST.json)

本批为SX×观测Z0→SY动态调节的工作插补敏感性分析。完整20份不等于已证明实质模型精确相容，也不是原CFPS四项调节或完整H4完成。未原样重跑失败CFPS、未修改冻结论文、未重新开启NLM。

所有ZIP<25,000,000字节。合并解压后按PAYLOAD_MANIFEST.json校验，运行 `python verification/verify_results.py --public` 直接复算原始保存参数/TECH3和完整家族合并；需要numpy、pandas、scipy，不读取未公开个人数据、不重新拟合。

此前CHARLS条件H4.1十二家族：[固定交付](https://github.com/lzhs1995/PP-lcgm-paper/tree/87941423437c589809a2c95833c220e387fc0f5d/charls_son_income_resume_20261016)。四项完整案例：[固定交付](https://github.com/lzhs1995/PP-lcgm-paper/tree/04e97911e2008343aacc7ccc1c38e4c84cffbbc8/charls_observed_moderation_20261016)。旧证据不重复上传。
