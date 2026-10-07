# Round2B证据导航

| 要核对的事项 | 证据位置 |
|---|---|
| 两方意见裁定与主方案 | audit/REVIEW_DECISIONS.md |
| 计分、基期来源与家庭键 | audit/source_contract.json；baseline_source_comparison.csv；baseline_contract.json |
| 恢复的缺失、家庭数与人数 | audit/baseline_missing_restoration.csv；baseline_household_recovery.csv；household_missing_counts.csv |
| 实际控制变量与年龄边界 | audit/main_controls.csv；age_crosswalk.csv；complete_case_counts.csv |
| 同条件模型与失败记录 | MODEL_INDEX.md；audit/model_execution_index.csv；models/下逐次INP/OUT及receipt.json |
| K1与旧WITH模型的条件口径比较 | code/18_conditional_equivalence.R；audit/K1_conditional_likelihood_comparison.csv、K1_shared_structural_parameters.csv、K1_equivalence_binding.json |
| 高精度参数与TECH3 | models/下parameters_high_precision.csv、parameter_covariance.csv、parameter_binding.json |
| 3274人聚类增长形状比较 | code/07_cluster_shape_compare.R；audit/clustered_shape_comparison.csv；原Round2A对应完整输出 |
| 家庭—个人MI实现 | code/04_hierarchical_mi.R；mi_validation.R；audit/mi_protocol.json；mi_predictor_matrix_requested.csv |
| 旧辅助输入与当前行顺序绑定 | audit/auxiliary_identity_binding.json；auxiliary_row_binding.csv |
| 实际MI成员与链验收 | audit/mi_engineering_acceptance.json、mi_member_validation.csv、mi_member_manifest.json、mi_predictor_matrix_actual.csv、mi_chain_means.csv、mi_chain_variances.csv、mi_convergence.csv；本批loggedEvents=0 |
| 初步检查点 | audit/checkpoint_iteration_*_validation.csv/json；只代表对应迭代的数据检查 |
| 链图、方法与预测矩阵差异 | code/15_mi_chain_review.R；audit/mi_chain_review_iteration_*/；迭代号明确，不自动代表完整30轮 |
| 小样本汇总抑制规则 | audit/mi_release_policy.json；公开链CSV对应.redaction.json；完整对象仅本机 |
| 参数协方差检查 | models/下parameter_covariance_diagnostics.json；不定矩阵拒绝测试在pooling_synthetic_tests.csv |
| 目标父模型与是否允许后续分析 | audit/target_parent_contract.json、target_parent_receipts.json、target_parent_gate.json；10份均不可接受，未正式合并 |
| 最终输出与来源再核验 | code/25_verify_delivery_evidence.py；audit/final_evidence_verification.json；核对10份INP/OUT哈希、原始警告和高精度值与打印值对应 |
| 参数合并实现及验收 | code/08_pool_parent.R；audit/pooling_synthetic_tests.csv；仅在允许合并时产生parent_MI_*结果 |
| 稿件版本与表头修订 | manuscript/下revision_receipt、appendix_header_corrections、appendix_table_status及同版Word/PDF |
| 网页直接读取全文 | readable/main/full.md；readable/appendix/full.md及逐页Markdown |
| 文件完整性 | FILE_MANIFEST.csv；PACKAGE_MANIFEST.json |
| 公开标识符检查 | runtime/public_privacy_scan.json及document_privacy_scan.json；仅对应所绑定哈希 |

以实际文件、REPORT和DELIVERY_SCOPE中的状态为准；未执行的合并及后续检验不得解释为结果不显著。历史依赖输出仍在前轮已发布资料中，新旧来源分开记录。
