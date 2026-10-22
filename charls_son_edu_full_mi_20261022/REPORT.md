# CHARLS son × education：H4.2 完整工作家族

日期：2026-10-22

## 范围

本隔离家族使用 CHARLS 的 son 指标与基期教育分组（C3），估计三过程潜在增长模型中的 `SX XWITH IZ` 交互。20 个条件工作多重插补成员（A 起点）全部完成 Mplus 输出、参数/协方差读回和 Rubin 合并；MI01 的 B 起点作为起点敏感性检查，不计入 20 份插补。

本批不重跑任何 CFPS 失败规格，也不以显著性筛选插补成员。工作 MI 保留了观测产品辅助变量和缺失指示变量，不能据此证明 MAR 或精确潜变量相容性。

## 执行与独立核验

- 样本 `N=2263`，社区数 `433`，教育组 C3 计数为 `1773/490`。
- 真实 Mplus 调用 `21` 次：20 个 A 成员加 1 个 MI01 B 起点；每次只运行一个 Mplus。
- 20 个 A 成员与 MI01 B 均为 `USABLE`；总引擎时间约 `2096.21` 秒。
- 独立 Python 核验通过：`2814` 个参数、完整变换协方差与 `21` 个研究对比，Rubin 合并和 B 起点敏感性均重算一致。
- 独立核验文件：`results/INDEPENDENT_VERIFICATION.json`、`results/MI01_B_STARTS_INDEPENDENT.json`、`results/PRIMARY_H42.csv`。

## 主要对比

教育组 1 − 组 0 的 `SY:SXIZ`：

- 估计：`-0.0406886792`
- 95% CI：`[-0.3110330142, 0.2296556558]`
- p：`0.7680030152`
- 规划 12 项 Bonferroni 后：`1.0000000000`

该结果是条件工作 MI 下的家族内对比，未形成“教育调节获得支持”的结论。

## 起点敏感性

MI01 A/B 使用同一插补成员、不同起点。最大参数差为参考 SE 的 `0.0034892`，最大 SE 相对差 `0.0026336`，标准化协方差最大差 `0.0052603`，均低于合同阈值 `0.05`。这只是起点敏感性检查，不是独立 MI 成员，也不替代完整 MI 推断。

## 恢复与工程经验

首次完整提交在 Mplus 启动前因 `run_family.R` 对预先存在的 MI01 目录重新编译而触发 `FileExistsError`，被记录为 `STOPPED_BEFORE_MPLUS`，没有把它误报成模型失败。随后将预编译目录移入审计区，以干净成员目录启动 retry01，并在同一原生 RStudio 会话中完成 21 次调用。

Windows 合同全程使用原生 `C:/...` 路径；若把 WSL `/mnt/c/...` 写入 Mplus 输入，Mplus 会在启动前失败。监控时以 `runtime/PROGRESS.jsonl`、逐成员 `engine_receipt.json`/`receipt.json` 和 `CALL_RESULTS.json` 为准；异步接口的通用回执可能长期显示 `started`，不应据此重复提交。MI 独立核验前必须先导出 `AUXILIARY_INPUTS.csv`，否则会出现验证器缺文件而非估计失败。

上述经验已并入 `mplusautomation-guide` 的 Windows 路径、运行器预编译冲突、持久化读回、MI 辅助文件和单槽资源控制章节。

## 科学边界

这是一个已完成的 CHARLS H4.2 单元，不能代表四项调节完整推断，也不能代表完整 H4 已完成。当前项目边界仍为：**四项调节完整推断、完整 H4 仍未完成。** 原 CFPS 失败规格不重跑。

## 公开包边界

公开包仅包含脱敏合同、Mplus 输入/输出文本、参数与协方差、独立核验代码、guard/恢复日志和结果表；排除全部 `data.dat`、MI_INPUTS/RDS/MIDS、AUXILIARY_INPUTS、逐人得分和个人级记录。因此公开包可复核参数变换、合并与证据链，但不能单独重跑 Mplus。
