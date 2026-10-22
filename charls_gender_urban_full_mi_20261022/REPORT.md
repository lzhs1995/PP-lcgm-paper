# CHARLS gender × urban：H4.2 潜变量交互完整工作家族

执行日期：2026-10-22（Windows，R 4.5.2，Mplus 9）。隔离根目录：
`C:/Users/LZHS/pp_lgcm_review/charls_latent_h42_gender_urban_full_20261022`。

## 执行与验收

- 真实原生 ClaudeR/RStudio async job：`b02e838f`；使用 `source(..., local=TRUE)`，阶段进度写入 `runtime/PROGRESS.jsonl`。
- 21 次真实 Mplus 调用：20 个 A 插补成员和同一 MI01 的 B 起点敏感性；全部 `USABLE`，没有成员替换。
- 每次只运行一个 Mplus；N=2085，社区=432，完整数据敏感性 `dfcom=431`。总引擎时间 1480.787 秒。
- Mplus 可执行文件 SHA-256：`0d48e39409a7a445bd5666017f7492df29607bf28448d3ea8e00bbb64dd66b51`。
- 独立验证：`results/INDEPENDENT_VERIFICATION.json`，2814 个参数、完整协方差变换、21 个研究对比和 Rubin 合并均通过；B 起点检查通过。

## 主对比

`SY:SXIZ` 的 urban 组1−组0：估计 `0.1598951744`，95% CI
`[-0.0853489565, 0.4051393053]`，p=`.2012971863`；按预先规划的12项
Bonferroni 调整后 p=1。该结果未提供城乡调节的常规显著证据，不能按研究假设支持解释。

本家族使用的是条件工作 MI（保留观测的 X/Y/Z 轨迹和交互辅助变量，仅对 ADL 缺失做条件插补），不证明 MAR 或精确潜变量相容性。B 是起点敏感性，不是第21份 MI。

## 科学边界

这是 CHARLS H4.2 的一个已完成指标×资源家族。它不等于四项调节完整推断，也不等于完整 H4；CFPS 已失败规格没有重跑。**四项调节完整推断、完整 H4 仍未完成。**
