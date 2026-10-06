# PP-LGCM论文：七项意见核验与独立复核资料

**当前审阅版本：正文v45、附录v38（NOT_RELEASED）。** CFPS全量历史复现与论文图表来源对应已完成；七项意见的核查、有限补验和文稿修订已交付，**统计科学问题尚未全部解决**。CESD8为主分析，CESD20sc为敏感性，CHARLS继续暂停。

本仓库由作者授权公开用于ChatGPT‑Pro、Claude网页端复核。只提供稿件、代码、Mplus输入输出与汇总，未提供个体分析数据、逐人得分、插补对象、ID映射或软件许可证。历史语法保留本机路径，不能将此仓库描述为无需受限数据和许可Mplus即可一键重估的工程。

## 请从这里开始

1. [七项核验结果与逐条答复](REVIEW_BRIEF.md)
2. [19项问题—证据—当前稿件位置](EVIDENCE_INDEX.md)
3. [正文v45逐页文本](readable/main/README.md) / [全文检索文本](readable/main_full.md)
4. [附录v38逐页文本](readable/appendix/README.md) / [全文检索文本](readable/appendix_full.md)
5. [本轮8规格敏感性及完整输出](SENSITIVITY.md) / [T1—T7与参数汇总](readable/summaries/README.md)
6. [全部245组Mplus完整输入输出](MODEL_OUTPUTS.md)
7. [给网页审阅者的说明（可直接转发）](FOR_WEB_REVIEWERS.md)

[正文PDF](01_current_review/current_manuscript/PP_LGCM_review_v45_NOT_RELEASED.pdf) · [附录PDF](01_current_review/current_manuscript/PP_LGCM_appendix_review_v38_NOT_RELEASED.pdf) · [当前及原稿材料](01_current_review) · [完整证据目录](02_evidence)

PDF提取文本只是浏览辅助；表格、公式和图形请以PDF/DOCX为准。网页工具可能只读取部分内容，请审阅者列出实际读到的文件，按需打开逐页材料与原输出，不把打开首页等同于读完整个仓库。

## 两个资料包

| 包 | 大小 | SHA256 |
|---|---:|---|
| [01：当前稿与七项答复](packages/01_current_manuscript_and_responses.zip) | 8,532,994字节（8.53 MB） | ca25cf9ccfcc92ae81f5463f46c65c261de5c2767cf06cddefbccf164858e638 |
| [02：完整输出与代码](packages/02_full_outputs_and_code.zip) | 12,732,700字节（12.73 MB） | 53927cd4a573d7686d7cfa7e551d3f101c27404d3b02f8c2ccd2309ddee2890e |

两个包均不超过25,000,000字节，独立可解压；为网址兼容性更换为英文下载名，内容与本地交付逐字节一致。无需解压也可通过上面的Markdown与TXT链接查看主要材料。需要下载原文件时可使用GitHub的Raw或Download按钮。

## 复核时必须保留的边界

- 当前原3274人CESD8自由形状变化均值为0.037（SE=.035，p=.284），不能继续引用旧−0.218作为当前结论。
- 本轮8规格：3个可审阅但拟合有分歧、3个不可接受、2个未收敛；四核心交互未新增。
- 计分恒差核验不等于纵向测量不变性；2016版本分类是非官方推断。
- 得分误差未完整传播；25项MI比较的精确配对与正式合并仍开放，不平均P值，不用两组星号差异替代组间检验。
- H4.2b保留原假设，当前未获一致支持。既有NLM回执仅供独立判断之后参考。
- 稿件保留历史、修正测量及本轮补验三层结果，不能将整篇视为所有模型已通过修正数据验收。

## 版本、来源与核验

[本地交付核验](verification/DELIVERY_VALIDATION.json) · [独立核验](verification/INDEPENDENT_VALIDATION.json) · [公开文件清单](PUBLICATION_MANIFEST.csv) · [逐页文本来源](verification/PDF_TEXT_PROVENANCE.csv)

旧包historical_snapshot中的v43/v37说明保持其历史时点；本仓库入口以v45/v38为当前对象。原回执的uploaded=false记录的是本地打包时尚未上传，并非本次GitHub发布状态。公开文件清单排除其自身以避免自引用。没有授予任何第三方材料额外的再分发许可。
