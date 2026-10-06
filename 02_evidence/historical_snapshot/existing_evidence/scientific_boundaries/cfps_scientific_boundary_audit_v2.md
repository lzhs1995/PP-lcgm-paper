# CFPS 科学边界审计 v2（增量）

v1 的表格、LRT、MI、rank 和 deferred 合同保持不变。本轮只增加 Figure 3.1 的源文件确认，不提交新的 Mplus，不修改原始 R、数据、DOCX 或结果目录。

- Figure 3.1 两个 OneDrive 原始 SVG 已找到；与 DOCX 嵌入 SVG 的文本序列分别 101/101 和 34/34 完全一致。
- `relative.R` 的样本处理和 PP-LGCM 结构语义已由 `7400-7458,7506-7544,10763-10799,11522-11529` 行段确认。
- Figure 3.1 状态由 `SOURCE_BOUNDARY_OPEN` 升级为 `SOURCE_FILE_CONFIRMED_SEMANTIC_SOURCE_CONFIRMED`；缺少一键生成 Office SVG 的 receipt 只作为可复现性说明，不再阻塞 provenance。
- CFPS scientific release 仍为 false，原因仍是 LRT 正式 p 值 0、MI v3 科学接受 false、rank/derived 合同开放和 669 个 limitation/deferred 单元格。

详细证据：`reports/cfps_figure_provenance_20261004/cfps_figure31_source_boundary_v3.{md,json}`。
