# 本次复核的证据表

全部从 Round2E 固定提交 `a323b0eace23bb471a5b4b7e66fff5361de5d874` 的公开包重新读取或计算，不含微观数据。

| 文件 | 内容 |
|---|---|
| `FILE_READ_LOG_877.csv` | 两个包 877 个文件逐个的路径、字节、SHA-256 与读取方式 |
| `RECOMPUTE_34_CALLS_round2E.csv` | 自写代码从 34 个调用的 model.out、estimates.dat、tech3.dat 重读的 LL、关键路径与 SE、方差、尺度因子、耗时 |
| `verify_release_rerun/` | 读完 Astra 的 `reporting/verify_release.py` 后在独立目录重新运行的结果：34 次调用、3761 个自由参数、4015 个起点槽，通过 |
| `CONVERGENCE_round2E_LMS.csv` | 观测 LMS 调用的打印收敛准则、EM 迭代次数、最后一次对数似然变化、算法、病态标记 |
| `LR_SB2001_cd_round2E.csv` | δ 与 ψSY 的嵌套比较：朴素 LR、Satorra–Bentler（2001）cd 与尺度化差异、稳健 Wald z² |
| `TIMELINE_POWER_round2E.csv` | 每次调用的起止时间、墙钟、CPU、与系统待机重叠的秒数 |
| `STANDBY_WINDOWS_round2E.csv` | 从 Astra 的电源事件记录整理出的待机区间 |
| `exact_ll_synthetic/` | 精确对数似然核对器在 Round2E 6 个合成数据输出上的结果（与 Mplus 打印值之差 ≤ 0.0004） |

## 文献核对

| 正文位置 | 内容 | 出处 | 结论 |
|---|---|---|---|
| 第 37 行 | 41.64% | Li & Zhang（2023），J Gerontol B 78(5), p.925（摘要）与 p.930 | 一致 |
| 第 37 行 | 44.546%；最疏远关系 14.774%、9.736%、56.072%；最亲密关系 37.427%、33.397%、19.482% | Zhang et al.（2025a），Ageing & Society 45, pp.2099—2100 | 一致 |
| 第 39 行 | 最亲近关系为紧密型者抑郁较低、最疏远关系为疏离型者较高；有无疏离关系 × 最近关系类型的交互 | Li & Zhang（2023） | 一致 |
| 第 39 行 | "疏远类型越疏远，认知功能越低、下降越快" | Zhang et al.（2025a）摘要 p.2089：按最远关系类型比较，疏离型最低最快、紧密型最高最慢；最近关系不显著 | 表述需收紧（见正文审读报告二、7） |
| 第 89 行 | 最远关系为疏离型（紧密型）者认知功能最低（最高）、下降最快（最慢） | 同上 | 一致 |
| 第 125 行 | 基期标准化（Zhang & Liu, 2024, p.3871） | 没有取得全文或该页 | 待补；Astra 本机已核对 |
