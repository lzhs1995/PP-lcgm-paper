# CHARLS 收入 H4.1 完整家族核验

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [结果讨论与边界](RESULTS_DISCUSSION.md) · [注册12家族状态](H41_REGISTERED_12.csv) · [组内路径及直接组差](GROUP_CONTRASTS.csv) · [区间图](H41_GROUP_DIFFERENCES.pdf) · [未完成范围及原因](INCOMPLETE_SCOPES.md) · [包清单](PACKAGE_MANIFEST.json)

本批检验观测基期家内差异与家庭收入组的条件关联异质性，不是SX×Z0动态调节或H4.2。只有完整40成员及起点检查通过才合并。不得把未形成可采用估计写成零效应。

将所有ZIP解压到同一目录，先按PAYLOAD_MANIFEST.json核对每项SHA256，再执行：

`python verification/verify_h41_results.py --public --root . --output PUBLIC_RECOMPUTATION.json`

需要numpy、pandas、scipy；不调用Mplus。公共复算核对保存参数、TECH3、样本数与合并计算，不复算被扣留的个体data.dat，也不重新拟合CFPS/CHARLS。本机原观测与插补检查只以聚合回执公开。

组合12项中的教育/城乡8家族复用[先前固定提交](https://github.com/lzhs1995/PP-lcgm-paper/tree/950a01ea8599e0782cc3685563c98265c4fc924f/charls_h41_mi_20261016)，不重复上传完整旧包。本批为新增收入4项及组合敏感性，不把相同资料解释为独立复制。方法仍是FCS工作近似，混合通过不证明MAR或精确相容性。

这是一批实证扩展的报告，不修改已冻结正文/附录，不新增NLM审稿。效率和恢复经验见[mplusautomation-guide PR25](https://github.com/lzhs1995/clauder-rstudio-workbench/pull/25)。
