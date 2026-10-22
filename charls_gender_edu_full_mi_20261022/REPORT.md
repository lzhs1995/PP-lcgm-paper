# CHARLS gender × education：完整 20-MI 潜变量工作家族（2026-10-22）

## 交付状态

本包对应一个隔离的 CHARLS 分支：sons-minus-daughters contact（gender）× baseline education（C3），三过程潜在增长模型含 `SX XWITH IZ`。20 个 A 插补成员全部完成 Mplus、TECH 读回和 Rubin 合并；MI01 的 B 起点敏感性也完成。实际引擎调用 21 次，单次只运行一个 Mplus。

该批次不是 CFPS 失败规格的重跑，也不代表四项调节完整推断或完整 H4 已完成。正式科学边界为：**四项调节完整推断、完整 H4 仍未完成。**

## 独立核验

- N=2085，社区=432，20 个 working-MI 成员；原 X/Y/Z、掩码和 50 个产品/缺失指示辅助变量保持不变。
- 独立 Python 读回并重建 2,814 个参数、21 个研究对比、134×134 变换和完整 Rubin 协方差。
- 主对比 `SY:SXIZ`（教育组1−组0）：估计 −0.0147998，95% 区间 [−0.2379550, 0.2083554]，p=.89658；规划 12 项 Bonferroni 校正值为 1。
- MI01 A/B 起点敏感性通过；B 仅是同一 MI 成员的起点检查，不计入 20 份 MI。
- 这是“条件工作 MI + 潜变量 XWITH”结果；不证明 MAR 或精确潜变量相容性。

## 恢复记录

1. 首次启动因 WSL `/mnt/c/...` 路径被写进 Windows 合同而在预检阶段停止，Mplus 调用为 0；错误日志保留在 `audit/BOOT_STDERR.retry0.log`。
2. 修正为原生 `C:/...` 路径后，MI01 A 的 Mplus 正常退出并生成完整输出；读回因 `job.json` 漏写 `parent` 字段报 `KeyError('parent')`。保留输出和哈希，只补元数据并重做读回，没有重复该 Mplus。
3. 恢复 runner 识别已有 `engine_receipt + USABLE`，复用 MI01 A，继续 MI02—MI20 A 和 MI01 B；最终 guard 已闭合。

## 公开包边界

包内含模型语法、Mplus 文本输出、参数/协方差、独立验证代码、合同和 guard/恢复日志。为保护个人数据，排除了全部 `data.dat`、MI_INPUTS/RDS/MIDS、逐人得分和其他个人级文件；公开包不能单独重跑 Mplus，但可复核参数变换、输出和合并。

## 后续

该分支可作为 CHARLS 覆盖矩阵的一个已完成单元。继续其他指标/资源家族时，沿用同一准入：新隔离目录、完整 MI、逐成员读回、独立合并、显著性不作选择规则。
