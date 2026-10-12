# 云端测试（无 CFPS 数据、无 Mplus）

用 Round2E 公开输出、合成数据和假 Mplus（`fake_mplus.py`）测试 Round2F 代码。全部通过。

| 脚本 | 结果文件 | 项数 | 结果 |
|---|---|---:|---|
| `code/r2f_selftest.R`（随代码包） | `results/selftest_cloud.csv` | 30 | 29 通过；`exact_ll_CFPS_SD_E0_01` 需要 CFPS 数据，云端为 SKIPPED，本机应为 PASS |
| `r2f_engine_mock_test.py` | `results/engine_mock_results.json` | 11 | 通过 |
| `r2f_test_exact_ll.py` | `results/exact_ll_unit_results.json` | 13 | 通过 |
| `r2f_mockflow.R` | `results/mockflow_results.csv` | 25 | 通过（情景 A—G） |
| `r2f_chain_test.R` | `results/chain_results.csv` | 12 | 通过 |

`results/mock_outputs_A`、`results/mock_outputs_B` 是用假数据跑出的汇总表，**只用于检查表格结构，不是任何结果**。其中的估计值来自 Round2E 已有输出加人为平移，耗时与状态由测试情景指定。

用法（Linux/macOS，需 R 与 Python 3，numpy、psutil）：

```
export R2F_R2E=<Round2E 公开包解压目录> R2F_R2D=<含 audit/Z_CONTRACT.json 的目录> R2F_PY=$(which python3)
# 自检：新建根目录，放入 code/ 与 contracts/，运行 setup 与 selftest
R2F_ROOT=<根目录> Rscript <根目录>/code/r2f_setup.R && R2F_ROOT=<根目录> Rscript <根目录>/code/r2f_selftest.R
# 队列演练
Rscript r2f_mockflow.R <已 setup 的根目录> <工作目录>
# 链条演练（另建根目录；脚本只在该一次性根目录里把 SMOKE 上限改为 5）
R2F_ROOT=<另一根目录> R2F_MPLUS=<fake_mplus.py 路径> FAKE_R2E=$R2F_R2E Rscript r2f_chain_test.R
# 引擎与精确似然
python3 -I r2f_engine_mock_test.py <code 目录> <工作目录>
python3 -I r2f_test_exact_ll.py <code 目录>/r2f_exact_ll.py <工作目录>
```
