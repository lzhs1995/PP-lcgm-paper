请先读本报告的完成范围和失败记录，再复算原始参数/完整协方差。不要把MI成员数、合法输出或skill进展当成原完整H4完成。无个人级数据，无需重新拟合。

# CHARLS H4.2 完整家族工作插补敏感性

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [全部登记家族](H42_REGISTERED.csv) · [组间直接差异与组内调节](GROUP_CONTRASTS.csv) · [区间图](H42_GROUP_DIFFERENCES.pdf) · [包清单](PACKAGE_MANIFEST.json)

请将所有ZIP合并解压到同一目录，运行 `python verification/verify_pooled_h42.py ALL --public`，需要numpy、pandas、scipy；无需微观数据或Mplus。程序直接读原始保存参数与TECH3，复算完整家族。代码中的本机路径已脱敏；公开验证器使用相对路径，同时核对公开字节哈希和保存的本机来源哈希。脱敏文件不宣称与本机原件逐字节相同。

工作插补完整不等于潜交互精确相容性。失败/未放行家族保留，固定12项多重比较；未按显著性选模型。本文档不是冻结论文的新版本，不要求新NLM轮次。CHARLS见面频率/家庭净收入与CFPS情感亲近度/个人收入含义不同。

前批固定证据：[H4.1十二条件家族](https://github.com/lzhs1995/PP-lcgm-paper/tree/87941423437c589809a2c95833c220e387fc0f5d/charls_son_income_resume_20261016)、[四项动态调节工作MI](https://github.com/lzhs1995/PP-lcgm-paper/tree/6ea7d570be09492927eac64315f7655cad55d66d/charls_dynamic_mi_sensitivity_20261016)、[本批H4.2完整案例父模型](https://github.com/lzhs1995/PP-lcgm-paper/tree/030bdcd548892df1876161b7e4637a02415bad56/charls_h42_pilot_20261017)。这些是同一研究资料上的不同条件分析，不是独立样本的重复验证。
