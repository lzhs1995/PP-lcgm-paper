# Round2E 云端测试说明（2026-10-10）

环境：Linux，R 4.3.3，Python 3.11。**没有 Mplus**，所以这些测试证明的是代码流程、判定规则、合并公式和导出正确；Mplus 是否接受新输入，要靠本机冒烟测试（code/r2e_smoke_mplus.R）确认。
输入：Round2D 固定提交 cf5ab4fb 的两个公开包（解压合并后的目录，含 models/、code/、audit/）。不含任何 CFPS 个人数据。
测试在代码冻结后一次性重跑，代码哈希见 ../CODE_SHA256.txt。

| 测试 | 命令 | 结果 |
|---|---|---|
| 自检 | `Rscript code/r2e_selftest.R <Round2D目录> <新目录>` | 47 / 47 通过 |
| 模拟流程：全部可用 | `Rscript cloud_tests/r2e_mockflow.R code <Round2D/models> <新目录> all_usable` | 16 / 16 通过，137 次模拟调用 |
| 模拟流程：边界混合 | 同上，情景 `boundary_mix` | 12 / 12 通过，122 次 |
| 模拟流程：预算停止 | 同上，情景 `budget_stop` | 11 / 11 通过，92 次 |
| 模拟流程：只生成输入 | 同上，情景 `dryrun` | 7 / 7 通过，53 次 |
| 冒烟脚本流程检查 | `Rscript cloud_tests/r2e_smoke_cloudcheck.R code <Round2D/models> <新目录>` | 38 项全部通过；导出包含 SMOKE_RESULTS.csv 且不含私有文件 |

模拟流程用 Round2D 的真实输出副本代替 Mplus 调用（SVALUES 段换成本次输入的模型语句，使起点拼接面对结构一致的源），关键路径取已知值；它检验调度顺序、调用上限、预算分配与停止、边界家族触发、家族判定、合并与制表、导出白名单。

results/ 中是各测试的逐项结果（CSV）和日志末尾。
