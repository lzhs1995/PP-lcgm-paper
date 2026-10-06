# CFPS 科学边界审计 v1

生成时间（UTC）：2026-10-04T15:50:45.494079+00:00

本报告仅汇总已有契约、`.out` 哈希、数据读回和来源审计，不提交新的 Mplus，也不修改原始数据、R、DOCX 或结果目录。

## 156 个版本差异单元格

- 156/156 行存在；历史显示匹配 156/156；运行时输出哈希一致 156/156。
- 技术结论：`historical_display_confirmed`；科学结论：`version_choice_open`。
- 输入差异分桶：`{"DIFFERENCE_WITH_INPUT_AUDIT_DOCUMENTED": 43, "DIFFERENCE_WITH_INPUT_AUDIT_DERIVED_FROM_RECEIPT": 113}`。
- 结论：历史显示值技术上已闭合，但历史/当前版本选择仍是作者科学裁决；不重复估计。

## 16 个历史舍入单元格

- 16 个 AIC/BIC 单元格已按观测到的 R `round()` 显示规则逐格复核；全部匹配：`True`。
- 该合同只关闭历史初稿复现的显示精度，不决定当前输入版本的科学采用，也未提交新 Mplus。

## 历史稿版本选择

- 历史复现合同：`HISTORICAL_DRAFT_VERSION_FROZEN_SENSITIVITY_RETAINED`；156 格的历史显示值已冻结，当前输入保留为敏感性说明；scientific release 仍为 false。

## 331 个历史审查单元格

- 历史复现合同：`HISTORICAL_REVIEW_CELLS_FROZEN_TECHNICAL_PRODUCERS_RETAINED`；fit 264 格、derived 67 格均保留既有 producer，历史显示值冻结；当前候选和语义 producer 作为敏感性/旁证，scientific release 仍为 false。

## 历史初稿复现总台账

- 10936 格中 10267 格已冻结历史显示值，669 格保留 limitation/deferred；台账状态为 `HISTORICAL_DRAFT_REPRODUCTION_RELEASE_LEDGER_COMPLETE_DEFERRED_669`，未提交新 Mplus。

## 25 个 LRT 候选

- 契约行数 25/25；已接受 LRT 计数 0。
- 技术分桶：`{"sensitivity_only": 6, "defer_source_followup": 12, "defer_nested_pooling_audit": 7}`。
- 来源诊断：`{"OBSERVED_COVARIATE_DISTRIBUTION_CHANGED": 6, "EXACT_PAIR_ABSENT_REQUIRES_NUMBERED_OUTPUT_AND_SOURCE_FOLLOWUP": 12, "REQUIRES_FULL_NESTING_AND_POOLING_AUDIT": 7}`。
- 结论：当前没有可发布的 LRT p 值；精确模型对、完整嵌套、相同估计/插补和 pooled likelihood 仍需闭合。

## MI v3 与秩/派生得分

- MI v3：`NOT_ACCEPTED_FOR_DOWNSTREAM`；数据读回 `True`；科学接受 `False`。收入派生审查为 `REVIEWED_HOLD`，收敛审查为 `ADDITIONAL_EVIDENCE_REQUIRED`。
- 秩/得分来源：16 个 source、384 个消费者引用，16 个 PID 集合一致，诊断标记 0 个；规则和采用仍开放。
- 不截零、不取绝对值、不无依据重编码；不把数据读回成功直接升级为正式模型采用。

## 状态

`CFPS_SCIENTIFIC_BOUNDARIES_INVENTORIED_NO_NEW_ESTIMATION_SCIENTIFIC_RELEASE_OPEN`

证据入口：`cfps_scientific_boundary_audit_v1.json`。
