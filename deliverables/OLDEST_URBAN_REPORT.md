# CHARLS oldest × urban：20-MI 潜变量 H4.2 工作家族

## 状态

- 终态：`COMPLETE_20_MI_WORKING_H42_OLDEST_URBAN`。
- 主家族：20 个 A 插补成员全部 `USABLE`，按 Rubin 规则合并；另运行 MI01 的 B 起点敏感性，结果 `USABLE`。
- 样本：N=2,397，社区/聚类数=433，complete-data df=432；每个成员 134 个自由参数。
- 估计：Mplus 9 + 原生 RStudio/ClaudeR 异步提交；最大并发 1，实际 21 次 Mplus 引擎调用。

## 主要对比

目标路径为 `SY:SXIZ`（抑郁变化 × 亲近度变化 × 基期相对 SD 的三重交互）；主对比为城镇组 1 减组 0。

- 估计值：0.0306772557
- 95% Rubin 区间（常规 df）：[-0.2619070489, 0.3232615603]
- p=0.8371808527；planned-12 Bonferroni p=1
- cluster-df 区间：[-0.2627328809, 0.3240873923]，p=0.8372781002
- MI Monte Carlo SE / pooled SE = 0.0006878

完整七条研究路径及 group0/group1/difference 均保存在 `results/POOLED_RESEARCH_CONTRASTS.csv`；主结果在 `results/PRIMARY_H42.csv`。

## 独立核验

`results/INDEPENDENT_VERIFICATION.json` 为 `PASS_FULL_TRANSFORM_AND_RUBIN_OLDEST_URBAN`：独立读取 21 个原始回读参数/协方差，复算 2,814 个参数、21 个对比和 Rubin 合并；几何正定、样本/聚类数、输入哈希与输出哈希均通过。MI01 A/B 仅作为起点敏感性，不替代 MI 合并成员。

## 可复现边界

本家族使用条件工作型 FCS 与观测产品辅助变量，不能据此宣称 MAR 或精确潜变量插补相容性；公开包排除逐人 DAT、MI 对象和辅助输入，不能单独重跑 Mplus。`original_CFPS_four_complete=false`，`full_H4_complete=false`；因此本批只关闭老年×城镇这一家族，**四项调节完整推断、完整 H4 仍未完成**。

## 恢复记录

首次全量提交在 MI04 启动前因全量根目录漏放已通过的 `GH07_STARTS.json` 而被适配器预检拦截；MI01–03 没有重复运行。随后复制试跑阶段的已通过起点证据，归档 MI04 半成品，恢复脚本复用前三份 `USABLE` 输出，自 MI04 继续至终端。相关证据见 `audit/GH07_STARTS_PROVENANCE.json`、`audit/FAILED_MI04_ADAPTER_PRE_GH07/`、`audit/BOOT_STDERR.log` 和 `runtime/PROGRESS.jsonl`。
