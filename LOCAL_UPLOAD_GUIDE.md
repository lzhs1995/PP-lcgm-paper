# 阅读与上传说明

当前交付：正文v45、附录v38；第一批无个体数据复核材料。科研问题仍有开放项，详见“七项意见_逐条答复.md”。本次整理没有重估模型、修改稿件或上传到网页端。

## 推荐操作

1. 在本机解压两个ZIP，保持01_current_review与02_evidence目录同级。两个ZIP均可独立解压，每包不超过25,000,000字节。
2. 给ChatGPT-Pro、Claude各开一个新对话，粘贴对应“复核提示词.txt”；两端使用同一材料版本、同一判断标准。
3. 第一轮上传01_current_review内“七项意见_逐条答复.md”、current_manuscript下正文v45及附录v38两个PDF、“19项问题_证据与稿件对应.csv”。依据界面附件数量限制分批上传，不要求一次塞入全部材料。
4. 第二轮上传“八规格_状态与完整输出.csv”“优先证据_八规格与得分来源.txt”及审阅者需要的summaries文件。这里有全部12次本轮引擎尝试和6份得分来源的完整文本；不只呈现成功结果。
5. 深查既有交互/MI时，上传02_evidence中的ALL_OUTPUTS.csv、historical_snapshot/model_index.csv和相应web_txt文件。原始R较长，按原行号定位读取；单份TXT与原字节哈希一致。原始代码引用的本机数据路径不保证网页可运行。
6. 若需对照最初意见，上传review_requests下的两份原始附件，以及original_20260214下原稿；明确它们是历史版本。
7. 两端完成独立结论后，再按需提供02_evidence/prior_reviews_read_after_independent_review中的旧审阅回执。

如果网页不能解压ZIP，直接上传解压后的PDF、MD、CSV、TXT。current_manuscript中的DOCX用于精确核对Word表格/公式；searchable_text按PDF物理页提取，仅辅助搜索，不能替代原文版式。

## 材料定位

01_current_review：当前与原始稿件、19项答复、T1—T7/八规格汇总、稿件位置摘录、提示词和小型优先证据读本。
02_evidence：239份旧完整输出的冻结快照、补齐的6份得分输出、对应语法/代码、后续脚本与回执、全部输出/TXT索引。

旧包README中的v43/v37、旧意见表candidate字样属于历史时点；本次“七项意见_逐条答复.md”和当前v45/v38定位表说明最新处置。MANIFEST.csv覆盖各包内容，根目录DELIVERY_VALIDATION.json与SHA256SUMS.txt记录最终验证和压缩包哈希。

## 后续反馈格式

请将两端的七项判定、引用证据、替换文字与最小必要补验清单一并带回。结论冲突时先对齐版本/样本/量尺/模型，再判断方法差异。本地不预设全部问题必须判为解决。
