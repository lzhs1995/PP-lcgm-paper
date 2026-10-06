# v44 / v37 全文审阅裁定（已被后续标签修订取代）

最终候选改为v45/v38。v44/v37回执保留为历史过程证据，不跨版本计算最终三审通过。

| 请求 | 状态 | 裁定 |
|---|---|---|
| pass1_full | PASS；两项问题 | 两份来源有效。Process-4重复编号属同一排行差过程族的不同指标；在v45/v38表注补充解释，不重新编号全部过程。附录Table 4.3.1缺少Sibling_diff2/3语义映射是真实可改进项，已补入对应表注。 |
| pass2_full | NLM_ERROR；零新增 | sources_used与citations均为空。不得用看似完整的回答替代来源校验。 |
| pass3_full | NLM_ERROR；零新增 | 同上，保留失败。 |
| pass2_full_concise | PASS；零新增 | 两份来源真实有效，完成对应方法审阅。回答“全部错误均修正”等概括不作为事实采纳；仅记录未发现新增问题。后续版本须重审。 |
| pass3_full_concise | NLM_ERROR；零新增 | 再次空来源，保留失败，不计为通过，不重复原指纹。 |

## v45/v38的具体处置与依据

- R44-1（Process-4）：保留历史过程族编号和模型数值，正文及附录表4.2.1增加“Sibling diff与Sibling4 diff分别对应老大与长子两种指标，不表示同一模型”的明确说明。
- R44-2（Sibling_diff2/3）：附录表4.3.1表注明确Sibling_diff2＝排行差（老小），Sibling_diff3＝排行差（幼子）。原始`20251003 closeness&depression_absolutive.R:8729–8743`将老小模型绑定`wfdds2*`，`8874–8888`将幼子模型绑定`wfdds3*`；`10443–10448`定义对应导出列名。没有更改模型估计。
- LOCAL-2（Sibling4残留“老小”）：核查时发现正文三处表注、附录相关表注及七个调节小标题仍含旧错误别名。原始`20251003 closeness&depression_relative.R:16,22`将`wfdds4*`和均值标准化`wfdds9*`定义为长子指标，`7477`将`wfd_d412`标记为长子；`relative2.R:52443,52501`继续使用该指标。已统一相应标签为长子，保留真正属于Sibling_diff2/3的老小/幼子分析文字。

本次直接编辑14个XML段落的21个文字节点，生成正文v45和附录v38。回退这些文字后，全XML与v44/v37完全一致；引文域、公式、媒体、估计数值及ZIP其他部件保持。验证详见`../manuscript/v45_v38_assembly_receipt.json`与`final_pdf_receipt.json`。

NLM所报“第13页”等位置仍须本地实际PDF定位，不能直接作为可靠页码。以上修订属于清晰度与语义纠错，不关闭MI/VCOV、负方差等科学推断事项。
