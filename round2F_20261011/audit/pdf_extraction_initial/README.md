# 首次PDF提取不一致的处置

这里保留首次逐格验证的失败回执。附表A20的 `E0_01_base` 被表格提取器读成 `E0 01 base` 加下一行的两个下划线。检查原始PDF字符坐标后，所有字符位于相同文字基线上，下划线的横向位置正确；不是Word文本或统计数据丢失。

`reporting/pdf_checks.py` 增加同一已检测单元格内的字符坐标复读：按字符中心确定所属单元格，按基线与横向位置排序。只有复读后整格、整行与预期完全相等才接受，并在最终回执的 `character_origin_fallbacks` 中记录。没有忽略下划线、数字、负号或跨单元格搜索。

后续视觉检查另发现附表A22负方差列太窄导致末位数字换行，已加宽该列，表内调用标签改为规格加q20a/q30b等简写，完整ID仍保留在CALLS.csv和原始输出。统计模型、估计值、冻结代码及验收门槛均未改变。

最终验收以 `manuscripts/manuscript_validation.json` 与 `manuscripts/visual_review.json` 为准；本目录的FAIL是修正前证据。
