# 给 Astra 的 Round2E 执行任务书

日期：2026-10-10
依据：Round2D 固定提交 `cf5ab4fb9e1e59742462a7dadd85ff6fdbdb83b0` 的两个包（1005 个文件已逐个复核）、Astra 的阶段总结、ChatGPT 的复核意见与 Round2E 方案。
本包内容：本任务书；`code/`（本轮全部代码）；`cloud_tests/`（云端测试脚本与结果）；`正文v49审读报告.md`、`附录v41审读报告.md`（稿件修改的逐条依据）。

---

## 0. 本轮做什么

先在四个分支上估计"SW + 观测 2012 年 Z0"的调节模型 E0/E1，每个分支完整十份 MI，按事前规则判定能否合并。SD 的 E1 家族被采用后，自动接资源组 H4。潜 IZ 路线只做两次诊断，不再开长队列。

所有规则在第一次估计前冻结到合同 `contracts/RUN_CONTRACT_2E.json`，运行中不因任何结果（显著或不显著）改变顺序、加跑或停跑。

## 1. 已经定下的事项（不要改）

- 主插补：沿用 Round2D 的家庭—个人分层 MI 十份，不重做插补，不重新清洗。
- 控制变量：沿用 Round2D 已核实的 24 列；性别差、长子差的常数列移除由 Z_CONTRACT 记录自动处理。wave 不进控制；sat12 只作敏感性变量，本轮不用。
- CES-D：CESD8 为主。
- 范围：只做 SX×Z；IX 交互不在本轮。
- SW 父模型照旧采用，不重估。
- 估计对象的改变要如实写：E 路线问的是"实际 2012 年关系配置 Z0 是否调节亲近度变化与抑郁变化的关联"，不是潜截距 IZ 调节的无损替代。Z0 作为 IZ 的代理会使调节系数衰减（Round2D 的 D0 输出显示 Z1 对 IZ 的条件信度约 0.21—0.30，合同步骤会重新计算并写入 `contracts/Z0_RELIABILITY_FROM_ROUND2D_D0.csv`）。

## 2. 代码文件

| 文件 | 作用 | 何时运行 |
|---|---|---|
| `r2e_selftest.R` | 自检 47 项：用 Round2D 已保存的真实输出检查读回、合法性门槛、边界分类、SVALUES 拼接与结构核对、输入生成、判定表、合并公式。不调用 Mplus，不读个人数据，不写 Round2D 目录 | 第 1 步 |
| `r2e_smoke_mplus.R` | 本机 Mplus 冒烟测试：只用合成数据，13 次调用 | 第 2 步 |
| `r2e_00_contract.R` | 核对来源并冻结合同；计算支持点、缩尾数据、Z0 信度。不调用 Mplus | 第 3 步 |
| `r2e_run.R` | 主程序：依次执行 B1 批次（A→B→B2→D→C）和 H4 批次，最后自动合并制表。可中断后用同一命令续跑 | 第 4 步 |
| `r2e_queue.R` | 各阶段的调度逻辑（被主程序调用） | — |
| `r2e_engine.R` | 执行引擎：每次调用独立目录、输入与数据哈希、回执、调用登记、耗时台账、资源检查、单次时限、中断恢复 | — |
| `r2e_tools.R` | 规格生成、输出读回、合法性门槛、边界分类、SVALUES 拼接与结构核对、数值比较、合并公式 | — |
| `r2e_upstream_math.R` | 与 Round2D `code/00_upstream_math.R` 逐字节相同（合同会核对） | — |
| `r2e_05_pool.R` | 合并与制表（主程序结束时自动运行；也可单独重跑） | — |
| `r2e_06_export.py` | 导出回传包：只收白名单文件，不收 `private/`、`data.dat` 或任何个人级数据。只用 Python 标准库 | 第 5 步 |
| `r2e_resource_gate.py` | 只读资源检查：其他 Mplus 进程、可用内存、CPU、PAUSE 文件。不修改或结束任何进程 | 每次调用前自动 |

合同冻结后不得修改任何代码文件；主程序启动时会核对代码哈希，不一致即拒绝运行。

## 3. 模型规格

所有模型：`TYPE = COMPLEX; CLUSTER = fid; ESTIMATOR = MLR`。数据为 Round2D 本机私有成员文件 `R2D/private/<分支>/Z0_member_XX.dat`（合同逐份核对其哈希与 Z_CONTRACT 一致）。

| 代号 | 在 SW 之上增加的语句 | 用途 |
|---|---|---|
| E0 | `ix sx ON z0;` `iy ON z0 (gi0);` `sy ON z0 (gs0);` `x1 y1 ON z0;` | 无交互基线；gi0、gs0 为 Z0 主效应 |
| E1 | E0 + `sxz \| sx XWITH z0;` `sy ON sxz (dc);` | 主检验 dc；1 维数值积分 |
| E0B / E1B | E0 / E1 + `sy@0;` | 只在边界规则触发时，整族十份使用 |
| H4_G | E1 + `DEFINE: zg = z0*G;`；G 不在控制列时加 `ix sx iy sy ON G;`；`ix sx ON zg;` `iy ON zg (gizg);` `sy ON zg (gszg);` `sxg \| sx XWITH G;` `sxzg \| sx XWITH zg;` `sy ON sxg (bxg);` `sy ON sxzg (dcg);` | δ0 = dc（G = 0 组），δG = dcg，δ1 = δ0 + δG |
| H4B_G | H4_G + `sy@0;` | SD 采用的是 E1B 时使用 |
| D0B | Round2D 的 D0 + `sy@0;` | 诊断：D0 的负残差是否只是边界问题 |
| D1L | Round2D 的 D1，起点取 Round2D 合法的老大差 D0 MI01 | 潜路线诊断 1 |
| D1B | D1 + `sy@0;`，起点取本轮老大差 D0B | 潜路线诊断 2 |

H4 的三个资源组：EDU = c2（初中及以上）；URBAN = c3（城镇，NBS2012）；INC = ginc（个人收入金额大于 0，不是高收入）。各组各份人数写入 `contracts/H4_GROUP_SIZES_BY_MEMBER.csv`。

### 3.1 起点

- 从另一个模型取起点时，直接使用源输出中 Mplus 自己写的 SVALUES 段（"MODEL COMMAND WITH FINAL ESTIMATES USED AS STARTING VALUES"），按名称对应，用 `*` 不用 `@`；新增语句一律从 0 起（如 `sy ON sxz*0`）。
- 源模型若含负方差，这些起点被清洗，不作为合法拟合来源宣称。
- 拼接后做结构核对：目标规格的每个 ON/WITH 对都必须出现在拼接结果中，且拼接结果不得出现规格外的变量。不通过即改用 Mplus 默认起点，并在 `start_mapping.csv` 记录原因。
- 每次调用目录下都有 `start_mapping.csv`，记录起点来源和处理。

## 4. 顺序、调用数与预算

### 4.1 批次 B1

| 阶段 | 内容 | 正常路径调用 | 类别 |
|---|---|---:|---|
| 0 合同 | 核对来源、计算支持点、生成缩尾数据、计算 Z0 信度、冻结合同 | 0 | — |
| A | 四分支 E0 MI01 | 4 | PILOT |
| A | 四分支 E1 MI01，15 点，起点取同份 E0 + 乘积项 | 4 | PILOT |
| A | SD E1 MI01，15 点，4 核（与上一行的单核配对） | 1 | CHECK |
| A | 四分支 E1 MI01，20 点，起点取 15 点结果；这一份即采用的 MI01 | 4 | CHECK |
| A | 四分支默认起点核查（Mplus 默认起点，同积分点） | 4 | CHECK |
| A | 四分支 D0B，起点取 Round2D 的 D0 MI01 | 4 | PROBE |
| A 结束 | 按 MI01 实测耗时分配剩余预算，写出 `runtime/phase_A.json` | 0 | — |
| B | E0 MI02—10 × 4 分支（全部先跑） | 36 | MEMBER |
| B | E1 MI02—10 × 4 分支（只对数值核查通过且在预算内的分支），起点取本分支采用的 MI01 | 36 | MEMBER |
| B2 | 边界家族（仅触发时）：E0B 每族 10 次；E1B 每族 12 次（采用点数、15 点、默认起点核查各 1 次，加 9 份成员） | 0 | BOUNDARY |
| D | 缩尾敏感性：每个已采用的 E1 家族在 MI01 上用 P1/P99 缩尾的 z0 再估一次；SD 完整个案 E0、E1 各一次 | 6 | SENS |
| C | 潜路线 L1（D1L）、L2（D1B）；剩余引擎预算不足 2 小时则跳过 | 2 | PROBE |
| 修复 | 只在触发时：20 点失败换起点重试；15→20 点不一致时加跑 30 点；成员失败时一次修复 | 0 | REPAIR |
| **合计** | | **101** | |

类别硬上限：PILOT 8、CHECK 9、PROBE 6、MEMBER 72、BOUNDARY 88、SENS 6、REPAIR 12，总计 201。超出正常路径的部分只给边界家族和修复使用。
时间预算：引擎 8 小时、墙钟 10 小时，任一先到即停止新准入。

阶段 A 的预算分配：九份 E0 的预计耗时（MI01 实测 × 9）先扣除；各分支九份 E1 的预计耗时（MI01 实测 × 9 × 1.25）从小到大依次纳入，累计不超过剩余引擎预算；放不下的家族记为 `NOT_ESTIMATED_WITHIN_BUDGET`，不先跑一半再停。只用耗时，不看估计值。

### 4.2 H4 批次

- 进入条件：SD 的 E1 家族（或 E1B 家族）被采用。与 dc 是否显著无关。冻结合同时 `R2E_RUN_H4=0` 则不接。
- 每个资源组：15 点首份（起点取 SD 采用的 E1 MI01 + H4 新增语句）→ 20 点（起点取 15 点结果）→ 默认起点核查 → 数值核查通过才补 MI02—10（20 点，起点取 20 点首份；失败时一次修复，起点取 SD E1 同份 + H4 新增语句）。
- 每组 12 次，三组 36 次；类别上限 PILOT 3、CHECK 6、MEMBER 27、REPAIR 3，总计 39。
- 时间预算独立于 B1：引擎 5 小时，墙钟 6 小时。
- 批次中途停止时，已完成的资源组照常合并，未完成的标为 `NOT_ESTIMATED_WITHIN_BUDGET`。

### 4.3 单次时限

线性模型 10 分钟、观测 LMS（E1、H4）30 分钟、潜 LMS（D1L、D1B）60 分钟。实际时限取"单次时限、剩余引擎时间、剩余墙钟时间"三者最小。超时照实记 TIMEOUT 和实际秒数。

### 4.4 处理器

只做一次完整配对：SD E1 MI01 在 15 点下单核与 4 核，同输入、同起点。路径、SE、LL 在起点容差内一致，且 4 核至少快 20%，才在之后的 LMS 调用中采用 4 核；否则全部单核。线性模型始终单核。同一时间只运行一个 Mplus。

## 5. 判定规则

### 5.1 成员状态

- `USABLE`：正常结束；没有鞍点、不可求逆、非正定等警告；全部方差合法；参数协方差可用；在各支持点上的条件矩阵合法；关键路径读回与打印值一致。
- `BOUNDARY_SY`：唯一的违规是 SY 条件残差方差为负，且 est/SE > −1.96，把 SY 方差置 0 后其余全部合法。
- 其余一律不可用：`INADMISSIBLE`、`TIMEOUT`、`NOT_CONVERGED`、`ESTIMATION_FAILED`、`INPUT_REJECTED`、`EXTRACTION_FAILED`、`KEY_PATH_ERROR`、`PRINTED_MISMATCH`、`INTERRUPTED`。

### 5.2 家族类别（只有 ADOPT 才合并）

| 类别 | 条件 |
|---|---|
| ADOPT | 十份全部 USABLE；LMS 规格另需 MI01 的积分核查和起点核查都通过 |
| NEED_BOUNDARY | 十份都是 USABLE 或 BOUNDARY_SY，且至少一份是边界 → 进入 B2，整族十份改用 B 规格重估 |
| NUMERIC_CHECK_FAILED | 十份 USABLE，但 MI01 数值核查不通过 |
| NOT_POOLABLE | 有成员不可用（修复后仍不可用） |
| INCOMPLETE | 有成员未运行 |
| NOT_ESTIMATED_WITHIN_BUDGET | 预算内放不下或批次已停止 |

不删成员，不混合自由与边界成员，不按 P 值在 E1 与 E1B 之间选择。B 家族同样要求十份全部 USABLE 才采用。

### 5.3 数值核查（只在 MI01 做，报告中如实写明）

- 积分：15 点与 20 点之间，核心路径变化 ≤ 20 点 SE 的 5%，SE 相对变化 ≤ 5%。不满足时加跑一次 30 点，比较 20 点与 30 点，采用 30 点。
- 起点：采用解与 Mplus 默认起点解比较，结果类别事前写定：

| 结果 | 含义 | 是否通过 |
|---|---|---|
| AGREE | LL 差 ≤ 0.01，路径差 ≤ max(0.001, 0.01×SE)，SE 相对差 ≤ 5% | 通过 |
| ALT_LOWER | 默认起点收敛到 LL 更低（差 > 0.01）的解；保留采用解并标注 | 通过 |
| ALT_FAILED | 默认起点未得到可用解；标注"起点未复现" | 通过 |
| BEATEN | 默认起点得到 LL 更高（差 > 0.01）的解 | 不通过 |
| RIDGE | LL 差 ≤ 0.01 但路径超出容差（似然脊或弱识别） | 不通过 |
| STRUCTURE_MISMATCH | 两者自由参数个数不同 | 不通过 |

### 5.4 合并与报告

- Rubin 规则，完整数据自由度取无穷；Barnard–Rubin 自由度作敏感性。
- 报告系数、稳健 SE、95% 区间、P、FMI、MCSE/SE（大于 0.05 标记）、80% 检验力下的最小可检测效应、实际 N 与户数。
- 推断以"现有家庭—个人 MI 和工作模型"为条件；乘积项没有进入插补模型，写明这一点。
- 多重性：E1 的 dc、E0 的 gi0、E0 的 gs0 各为固定 4 项的 Holm 族；H4 的 δG 为固定 3 项的 Holm 族。未得到合法家族的检验保持缺失，不缩小族，不填 P = 1。

### 5.5 条件斜率与支持点

- 支持点由合同步骤从本机数据计算（`contracts/SUPPORT_POINTS.csv`）：原始零点（SD 为 Z0 = −0.4759262086）；零点一侧非零值占比 ≥ 5% 时，该侧的中位数；与零点不重合的 P10、P90；以及观测最小值和最大值。只用于呈现，不改变连续交互。
- 条件斜率 b(z) = bss + dc·z，两点差 dc·(zH − zL)，都逐份用完整参数协方差计算后再合并，不只相加 SE。
- Johnson–Neyman 区域只报告观测范围内的边界。

### 5.6 H4 方向判定（按成分）

在 SX×Z 下（Z 越大越不和谐，预期 SX→SY 斜率为负）：δ > 0 是弱化成分（差异削弱亲近度的负向关联），δ < 0 是缓解成分（亲近度缓冲差异的关联）。同一系数只会落入一个成分。

用 δ0、δ1、δG 的九个 Bonferroni 同时 95% 区间（三个资源组 × 三个对比）判定：

| 判定 | 条件 |
|---|---|
| H4.2b（弱化） | δ1 区间在 0 以上，δG 区间在 0 以上，δ0 不显著为负 |
| H4.2b（缓解） | δ1 区间在 0 以下，δG 区间在 0 以下，δ0 不显著为正 |
| H4.2a | 镜像：δ0 已确立，δG 与之反向，δ1 不显著反向 |
| 交叉 | 两组都确立且方向相反，单独报告 |
| 不判定 | δG 区间含 0 |

只看 δG 的符号永不映射到 H4.2a/b。δG 的 Holm 检验（统计上是否有组间差异）与方向判定（是否符合原理论）分两栏报告。例：δ0 = −0.2、δ1 = −0.6 时，"绝对幅度更大"成立，但它属于缓解成分在资源较好组更强，不是"弱化更强"。

## 6. 本机 Windows 执行步骤

在同一个 PowerShell 窗口里依次执行；Rscript 用 Round2D 时的同一个。任何一步没有达到验收标准，就停在这一步，把该步的输出回传，不要继续。

### 6.1 准备与自检（不调用 Mplus）

```powershell
Expand-Archive round2E_for_astra.zip -DestinationPath C:\Users\LZHS\pp_lgcm_review\round2E_code
$code = 'C:\Users\LZHS\pp_lgcm_review\round2E_code\code'
$env:R2D_ROOT   = 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
$env:R2E_MPLUS  = 'C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Mplus.exe'
$env:R2E_PYTHON = 'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
Rscript -e "for (p in c('jsonlite','digest','processx','ps','MplusAutomation')) if (!requireNamespace(p, quietly = TRUE)) install.packages(p, repos = 'https://cloud.r-project.org')"
& $env:R2E_PYTHON -m pip install psutil
Rscript "$code\r2e_selftest.R" $env:R2D_ROOT C:\Users\LZHS\pp_lgcm_review\r2e_selftest_20261010
```

验收：最后一行为 `SELFTEST PASSED: 47 / 47`。结果在 `r2e_selftest_20261010\r2e_selftest.csv`。

### 6.2 Mplus 冒烟测试（只用合成数据）

```powershell
Rscript "$code\r2e_smoke_mplus.R" C:\Users\LZHS\pp_lgcm_review\r2e_smoke_20261010
```

- 共 13 次 Mplus 调用：E0、E1（15 点；4 核；默认起点）、E0B、E1B、H4_EDU、H4_INC、H4B_EDU，以及潜路线接口 D0、D0B、D1L、D1B。不想等潜路线时，先设 `$env:R2E_SMOKE_SKIP_LATENT='1'` 跳过最后 4 次。
- 验收：`r2e_smoke_20261010\R2E\results\SMOKE_RESULTS.csv` 中没有 FAIL；D1 超时只记 WARN。
- 它检查：新输入被 Mplus 9 接受并能读回；各条 SVALUES 拼接链完整（E0→E1、E1→E1B、E1→H4、E1B→H4B、D0→D0B、D0→D1L、D0B→D1B）；`sy@0` 在输出中确为固定值；4 核与单核数值一致并记录耗时；默认起点与拼接起点一致；合成数据中的已知交互（dc、dcg）被大致恢复、ginc 的 δG 接近 0；E1/H4 为 1 维积分、D1 为 2 维。
- 合成数据的耗时只说明相对成本，不代表 CFPS 的运行时间。

### 6.3 可选：只生成输入的演练

```powershell
New-Item -ItemType Directory C:\Users\LZHS\pp_lgcm_review\r2e_dryrun_20261010
$env:R2E_ROOT = 'C:/Users/LZHS/pp_lgcm_review/r2e_dryrun_20261010'; $env:R2E_DRYRUN = '1'
Rscript "$code\r2e_00_contract.R"; Rscript "$code\r2e_run.R"
Remove-Item Env:R2E_DRYRUN
```

演练目录只用于查看将要生成的输入，不得作为正式目录使用。

### 6.4 正式运行

开始前：关闭电脑睡眠；确认没有其他 Mplus 在运行；预留连续时间（B1 最多 10 小时墙钟，接着 H4 最多 6 小时）。墙钟从批次开始连续计时，暂停和睡眠也计入。

```powershell
New-Item -ItemType Directory C:\Users\LZHS\pp_lgcm_review\round2E_20261010
$env:R2E_ROOT = 'C:/Users/LZHS/pp_lgcm_review/round2E_20261010'
$env:R2E_RUN_H4 = '1'      # 设为 '0' 则不自动接 H4（以合同冻结时的值为准）
Rscript "$code\r2e_00_contract.R"
Rscript "$code\r2e_run.R"
```

- 合同步骤最后一行必须是 `CONTRACT FROZEN`。若为 `CONTRACT CHECK FAILED`，停止并回传 `contracts\` 目录。合同已存在时程序拒绝覆盖。
- 实时进度：`runtime\progress.json`；调用登记：`audit\CALL_REGISTER.csv`；耗时台账：`audit\ENGINE_LEDGER.csv`。
- 结束时自动合并，结果在 `results\`，控制台显示 `Round2E finished`。

### 6.5 运行中的情况处理

| 情况 | 做法 |
|---|---|
| 需要暂停 | 在 `runtime\` 新建名为 `PAUSE` 的空文件。当前调用结束后不再准入新调用，控制台显示 `resource_wait`。等待超过 2 小时会自动停止本批 |
| 需要关机或中止 | 先放 PAUSE，等出现 `resource_wait` 后再关闭窗口。**不要在 Mplus 估计中途按 Ctrl+C**：被打断的调用记为 INTERRUPTED、算作已用，该成员只能靠修复 |
| 中断后续跑 | 删除 PAUSE；新窗口重新设置 6.1 和 6.4 的环境变量；运行同一条 `Rscript "$code\r2e_run.R"`。已完成的调用直接读回执，不重跑；有输出无回执的调用照常读回 |
| 续跑时报 `Registered call still running` | 有 Mplus 仍在运行该调用；等它结束后再续跑，不要手动结束进程 |
| 某分支失败 | 不需要处理，程序按规则记录并继续其他分支 |
| 预算用尽 | 程序停止新准入并合并已完成部分，属于正常结局；不要延长预算或重开 |
| 程序报其他错误 | 停止，回传控制台输出和 `runtime\`、`audit\` 目录 |

### 6.6 导出与回传

```powershell
& $env:R2E_PYTHON -I "$code\r2e_06_export.py" $env:R2E_ROOT C:\Users\LZHS\pp_lgcm_review\round2E_return.zip $code
& $env:R2E_PYTHON -I "$code\r2e_06_export.py" C:\Users\LZHS\pp_lgcm_review\r2e_smoke_20261010\R2E C:\Users\LZHS\pp_lgcm_review\round2E_smoke_return.zip
```

回传清单：

1. `round2E_return.zip`（合同、审计、运行状态、结果，以及每次调用的输入、输出、回执、起点映射、高精度参数和参数协方差）和 `round2E_smoke_return.zip`。
2. `r2e_selftest.csv`，以及自检、冒烟、合同、主程序四个步骤的控制台输出（复制成文本即可）。
3. 按第 8 节修改后的正文与附录。
4. 一段说明：Round2D 包中 `code/15_build_manuscripts.py` 与 `code/19_build_reports.py` 的包内哈希（前 8 位 bf00f757、7752d215）为何与 `changed_bound_sources.json` 中的记录（07589d77、3b33a855）不同，附 diff。两者都是报告排版脚本，不影响估计。
5. 上传 GitHub 沿用 Round2D 的做法：新建 `round2E_20261010` 目录，分包各不超过 25 MB，给出固定提交链接；不含微观数据、真实 PID/FID、逐人得分或插补对象。

`results\` 中的主要文件：

| 文件 | 内容 |
|---|---|
| `MODEL_EXECUTION_2E.csv` | 每次调用的状态、耗时、起点来源、失败细节 |
| `BUDGET_2E.csv` | 两个批次的调用数和引擎、墙钟用量 |
| `FAMILY_STATUS_2E.csv` | 每个家族的类别和十份成员状态 |
| `NUMERIC_CHECKS_2E.csv` | 积分、起点、处理器核查结果 |
| `POOLED_KEY_PATHS_2E.csv` | 已采用家族的合并结果 |
| `MULTIPLICITY_2E.csv` | Holm 调整 |
| `CONDITIONAL_SLOPES_2E.csv`、`JOHNSON_NEYMAN_2E.csv` | 支持点上的条件斜率与观测范围内的 J–N 边界 |
| `H4_CONTRASTS_2E.csv`、`H4_DECISION_2E.csv`、`H4_CONDITIONAL_SLOPES_2E.csv` | δ0、δ1、δG 的同时区间与成分判定 |
| `DIAGNOSTICS_D0B_LATENT_2E.csv` | D0B 与两次潜路线诊断 |
| `SENSITIVITY_TAIL_CC_2E.csv` | 缩尾与完整个案敏感性 |
| `Z0_RELIABILITY_CONTEXT_2E.csv` | Z0 对 IZ 的信度背景 |
| `SUMMARY_2E.json` | 总览 |

## 7. 什么算完成

- 四个 E 分支都有真实处置：被采用的家族有完整十份合并结果、区间、支持范围内的条件斜率；未被采用的有具体原因和已耗预算。
- "合法但区间宽"或"未获支持"是完成的统计结果，不需要继续寻找显著性。
- 预算内估计不完的家族标为 `NOT_ESTIMATED_WITHIN_BUDGET`，不等于无效应，也不在本轮内延长。
- 潜路线两次诊断即使成功，也只是单份候选，不构成 MI 推断，不自动触发其余九份或其他三条潜路线。

## 8. 稿件修改

逐条依据见包内两份审读报告。

### 8.1 现在就改（不依赖新结果）

1. 正文 p6、p11、p14 表 7，附录 A12，HYPOTHESES.csv：H4.2a/b 改按成分判定（第 5.6 节）；表 7 的"原预测"改回原文措辞，分列弱化与缓解；另加一张"本轮操作化—符号—原预测"对应表；统计差异与理论方向分两栏。
2. 正文 p11、p13，附录 A11：参考点改为 `SUPPORT_POINTS.csv` 的实际支持点，不再用 z = −1, 0, 1。
3. 正文 p3 第 104—107 行：Li & Zhang（2023）方向写反且无引文。改为"最亲近一对关系越紧密，父母抑郁症状越低；最疏远一对关系越疏离，抑郁症状越高（Li & Zhang, 2023）"（原文摘要 p.925）。
4. 正文 p6 第 259—262 行：Zhang et al.（2025a）补"最远关系为疏离型（紧密型）者……"，与 p4 一致（原文 p.2089、p.2111）。
5. 正文 p3—p4：说明该文的"互动策略"是类型异质性，不是乘积交互。
6. 正文多处：同一篇两作者文献统一写法（Li & Zhang 2023；Zhang & Liu 2024），检查 Zotero 样式；Chen & Zhou、Chen & Chen 同理。
7. 附录 A9：按分支和规格逐行写实际情况（负残差及其 z、求逆失败所在迭代、鞍点、超时）；老大差 D0 前五份合法；"estimated covariance 不可求逆"不改写成 Hessian 奇异；加注"全部负方差的 est/SE 在 −0.7 以内，Round2E 以预登记边界家族处理"。
8. 附录 A10：标题改为"新增家内差异模型（D/E/H4）的可报告核心路径"，避免读成 SW 也撤回。
9. 正文 p14 第 693 行：零值比例写明是 2012 年基期、标准化前的原始零值。

### 8.2 结果出来后再改

- p9 第 363 行：说明观测基期 Z0 是本轮实际执行的主要调节设计，潜 IZ 路线转为诊断。
- p10 第 448—452 行：补 Z0 作为 IZ 代理的衰减说明，信度取合同步骤的结果；不称"潜在初始差异调节"。
- p12—p14 三张空白结果表：用 E 结果替换；潜路线失败集中到附录一张原因表。
- 表 7 的 H1.2—H1.4：按 E0 的 gi0、gs0 更新（Holm 族大小 4）。
- 摘要、p12、p14 三处重复的"未执行"句：只留一处，其余指向表 4—6。
- 附录 A14 第 3、6 行：补边界型负方差的新证据；说明 E 路线与插补模型的不相容只涉及 SX×Z0 乘积未进入插补（推断，不是证明）。

## 9. 不要做的事

- 不改 Round2D 目录中的任何文件；不重做插补或清洗。
- 合同冻结后不改代码、不改合同；不手动补跑、删除或替换任何调用目录。
- 不因 P 值改变顺序、加跑、停跑，或在自由与边界规格之间挑选。
- 不删除失败成员后合并其余成员；不混合不同积分精度或不同约束的成员。
- 不降低积分点、不放宽容差、不延长预算来"完成"家族。
- 不在 Mplus 估计中途按 Ctrl+C，不手动结束 Mplus 进程。
- 不把微观数据、真实 PID/FID、逐人得分或插补对象放进回传包或公共 GitHub。
