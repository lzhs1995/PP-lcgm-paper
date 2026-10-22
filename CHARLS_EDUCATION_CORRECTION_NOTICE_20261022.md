# 教育家族派生敏感性表更正（2026-10-22）

适用：gender、oldest、son 的 2026-10-22 完整潜变量教育家族公开包。

请读取 [修正说明与结果](charls_education_postprocess_correction_20261022/README.md)。此包替代原 `POOLED_CLUSTER_DF.csv` 与 `cluster_*` 敏感性列；按各家族实际社区数，完整数据自由度为431、432、432。原始主 Rubin 估计、主要区间与显著性均不变，不需要重新运行 Mplus 或 MI。

历史包和提交保留。son 的旧终态 `A_members=21` 是标签计数错误，实际20个A加1个B；旧 `local-1` 的 SMOKE/GUARD JSON 是任务摘要，不能当作真实可执行 harness 验收。

下载：`CHARLS_education_postprocess_correction_20261022.zip`，49,621字节，SHA-256 `31e686c2c66f5f5b397e836c6d725e2bdc4bac1a74933db661d9fce735510279`。16项载荷加清单，无逐人数据。独立复算3×134参数和3×21对比已通过。

**四项调节完整推断、完整 H4 仍未完成。**
