# 独立交付审计：CONDITIONAL_PASS

审计时间（UTC）：2026-10-13T05:57:25.731869+00:00。P0：0；P1：2。

当前文稿的 DOI、文件哈希、引用修复保真和最终同版 NLM 证据通过本次有边界的独立核对。发布控制仍有两处可复现缺口，需要在公开放行前补齐，或以固定文件清单和明确的独立复核作等效约束。本结论不表示文稿失败，也不表示 GitHub 公开交付已经完成。

## 授权、身份与边界

依据 `runtime/EXECUTOR_DELIVERY_AUDIT_TASK.md`（SHA-256 `816070ec5a749239e46ddcfb6aef54b6b716cf524d5092acd87b35e1f2a1a845`）执行。实际 executor 为 tmux `%6`、Codex PID `2174927`、会话 `01a133ae-2511-7662-a802-f7f0620d3192`；进程祖先包含 pane 根 PID `2160992`，与本次实时 tmux 查询相符。身份记录见 `runtime/executor_delivery_audit/executor_identity.json`。

**正式 V2 尚未建立；本报告是用户直接授权的单次独立审计，不是 V2 回调、三轮共识或协同协议通过证明。** 未创建 V2 task/run/nonce、inbox/callback，也未替其他 agent 作出判断。

所有写入仅位于本任务允许的辅助目录及两个固定报告文件。项目、Word/PDF、全局配置和其他工作目录均未修改；未调用 NLM/R/Mplus、启动估计、发布、删除文件、关闭进程或注入 supervisor 输入框。没有重跑 282 项测试。

## 实际检查与正面结果

1. 完整阅读任务指定的 README、REPORT、CLOSED_AND_UNTESTED、EVIDENCE_VERIFICATION、manuscript_validation、visual_review、FINAL_CITATION_REPAIR、PDF_PAGE_COMPARISON；审计期间主控更新的 REPORT、引文修复状态及最终 NLM 回执也已重新读取。范围收缩、SW/SD E0 条件关联、完整调节 MI 缺失、H4 未执行、CHARLS 暂停及零新增估计表述相容。本轮没有把“完成意见处理”误称为“完成原假设检验”。
2. 四份现行 DOCX/PDF 的实际 SHA-256 全部匹配 manuscript_validation。主文 PDF 为 `a60b19efa42debb2d77dd430000e41533453ecf172a6b64deafeec6aa07e97f0`；补充 PDF 为 `80ae7784706c436ebc528cabb426b8bf66e6cbc203d5aab018a4c114a7065ef1`。
3. 用原生 Windows Python/PyMuPDF 重新计算修复前后全部 42 页的像素哈希，全部匹配原回执。变化页确为主文 2、补充 31/32/33，其余 38 页像素一致；前后 PDF 文件哈希也与视觉回执一致。独立看图仅对补充第 31 页进行，不冒称重新肉眼审查全部 42 页。
4. 直接解析前后 DOCX：主文 5 张、补充 30 张表的规范化 XML 顺序逐一相同；全部 `instrText` 节点序列相同；脚注 XML 哈希相同。201/779 是 instrText 节点数，不冒充 Word 复杂域数。
5. 检查实际待打包选择规则下的初始 187 个文件（14,181,306 字节，未计后续主控新增 NLM 回执、报告与 ZIP 派生文件）。63 个 CSV 的表头/行数对应参数、协方差、样本汇总、模型台账或证据映射；199 条数字映射和 10 条结果路径的行数与回执一致。四个 PDF 均是现稿或冻结历史稿，四个 DOCX 亦然；PDF 嵌入文件数为零，DOCX 无 embeddings/vba 且 CRC 正常。未据此宣称完成真实队列标识/凭据的完整内容重扫。
6. 逐行审查四个指定脚本，并追到 `record_nlm_acceptance.py` / `record_closeout_receipt.py` 以确认依赖。打包脚本最终检查 ZIP 实际大小 ≤25,000,000 字节，验证 CRC、跨包成员唯一性、完整覆盖及逐载荷 SHA-256；文件清单和包清单分开避免循环哈希。publish 的 stage preflight、固定 commit、禁止强推、路径穿越拦截、匿名 requests Session（trust_env=False）、ZIP 回读、载荷验证、随包核验器和独立 public proof 的逻辑均存在。没有执行有副作用的打包/发布入口。
7. 原先排查的“原始 NLM 回复未进入 stage”不是缺陷：验收脚本将其复制到 `reports/nlm/`，当前最终回执也确实引用这一可打包路径。

## 第 7 轮 DOI：独立判定为误报

`runtime/nlm/round_07/query/attempt-01.raw.txt` 的 SHA-256 为 `0f861b2abe881f613499acac4a5a938213ffe610e7a12eccd0c1de3c67903294`。answer 声称 Raudenbush/Chan 条目串用了 `10.1177/02654075241283974`，但同一 JSON 的 `references` 第 15 项实际给出 `Growth Curve Analysis in Accelerated Longitudinal Designs`、29(4)、387–411 和 `10.1177/0022427892029004001`。它的来源 ID 为 `f0c95fb1-01ef-421b-a033-4696d5882a9c`，来源记录绑定当前补充 PDF 哈希。

我提取并渲染了当前补充 PDF 第 31 页；正文可见 DOI 与文本层均为 `10.1177/0022427892029004001`。另一 DOI 仅在补充第 33 页的 Zhang/Liu（2024）条目出现。第 31 页没有隐藏 PDF link 目标供此处发生另一种 DOI 串用。证据见辅助目录的 `supplement_page31.png`、`supplement_page31.txt` 和 `doi_occurrences.json`。

因此本条不要求改稿；应保留第 7 轮原始 `1 / NO` 及误报裁定，不把原始回复改成 `0 / YES`。本次判断来自原始来源摘录与实际 PDF，而不是复述 supervisor 的结论；没有重新查询 NLM，也没有重新核验外部出版商数据库。

## P1-01：A5 连续性与原始答复未在最终门禁完整绑定

位置：`reporting/publication_gate.py:21–35`，以及生产验收列表来源 `record_nlm_acceptance.py:12`。

门禁对 raw 做 SHA-256 检查，但末两轮的 `new_issues_count` / `a5_no_new_issues` 直接信任审计 JSON。它也只取传入列表的最后两项，不验证其中是否跳过中间轮次。隔离负例使用真实第 5–8 轮的只读副本：

| 检查 | 预期 | 实际 |
| --- | --- | --- |
| 保留 5/6/7/8，末两轮为 7 的 1/NO 和 8 的 0/YES | 拒绝 | 拒绝（负对照正常） |
| 仅从清单去掉第 7 轮，末两项变为 6/8 | 拒绝作为“连续无新问题” | PASS |
| 保留第 7 轮原始内容和哈希，仅将其元数据改成 0/YES | 拒绝原文/元数据矛盾 | PASS |

详见 `runtime/executor_delivery_audit/targeted_checks.json`。隔离目录明确标记为负例测试，不是生产验收、NLM 共识或 V2 证据；生产回执未被修改。

主控在审计期间生成的**实际**最终回执没有触发这项错误：保留 5/6/7/8/9，原始 7 仍为 1/NO，连续 8/9 均为 0/YES 且来源 ID 互不相同；全部源 PDF/原始答复哈希及原始计数均经独立核对。只读调用实际 `publication_gate.check(root)` 返回 PASS，见 `actual_final_nlm_check.json`。该事实缓解本版输入风险，但不消除代码可接受错误回执的缺口。

建议：把完整有序轮次台账绑定入验收，校验终止轮次的真实连续性；从已绑定原始答复解析并比对计数/结束标记。误报裁定应单列，不能覆盖原文。保留已通过的 8/9 轮；这项修复不要求重跑 NLM 或修改 PDF。

## P1-02：扩展名筛选和标识扫描不能落实“仅聚合资料”保证

位置：`reporting/package_closeout.py:20–26`；`reporting/privacy_scan.py:69–84`。

打包按目录与扩展名递归选择文件，不是逐文件认可的聚合资料清单。privacy_scan 只用四个特定 CSV 列名、已知真实标识 token、凭据特征及特定目录名来排除。这会漏掉使用其他索引列名、没有已知 PID/FID 的逐人得分。

隔离测试只造了三条虚拟记录：`case_number,cesd_score`，文件名 `anonymous_person_scores.csv`；测试标识集合也完全合成。实际 scanner 返回 `PASS` 且写 `public_microdata=false`。所有测试输入/输出（含模拟 private/runtime 子目录）均在本任务辅助目录内，没有读取真实参与者记录或修改生产扫描结果。若同类 CSV 意外进入 evidence/reports，现有打包器会自动纳入。普通文献 PDF 在非 `literature_private` 目录下也缺少逐文件角色判定，此项为静态观察。

本次没有发现当前载荷实际泄露私人数据或文献全文；这是一项可复现的排除门禁缺口，不能把“未检出已知标识”写成“保证不存在逐人记录”。

建议：公开前冻结经人工确认的相对路径、SHA-256、文件角色清单，禁止意外新增文件；CSV 要按聚合表模式认可，PDF/DOCX 要逐一确认是本项目可公开稿件。已有标识、凭据和嵌入对象扫描继续保留，作为第二层检查。实际最终 inventory 必须包含主控后续生成的 NLM/发布相关文件，不能直接把本次 187 文件快照当作最终包清单。

## guide 经验核对

已完整阅读指定 source（SHA-256 `113e2fd8cbcaef617846a9075e1973431598433e0ae553a94333e9737adeb69e`）。复用成果、冻结容差、区分单份合法与完整 MI、不得用 E0 FMI 预言 E1B、条件 SY 限制、诚实保留未检验、最小引文修复与同版重审的经验，均与本次保存证据一致。关于 NLM 错误题名/页码的例子，可在第 4 轮原始回复直接找到，修复后第 31 页符合其记录。

关于严格白名单、连续 A5、匿名回读的段落应当作为完成条件阅读；不能据指南文字认定这两处代码缺口已经解决或发布已经完成。Windows/WSL 经验没有被写成 macOS 原生授权 Mplus/Word 验证，边界适当。现存 GUIDE_UNITTEST 与日志均记录测试集合 282 项、跳过 15、失败/错误为 0；本次只读这些证据，没有重跑。旧 GUIDE_COLLECTION_TEST 的失败记录不是当前套件失败，属于保留历史；日志绑定与历史状态说明可进一步明确，但不列 P0/P1。

## 当前阶段与未检查范围

初读时最终 NLM 审计、closeout 和 publication receipts 尚未存在，这属于正常顺序。结稿时 NLM_FINAL_AUDIT 已 PASS、CLOSEOUT_RECEIPT 已 SCOPED_CLOSEOUT_COMPLETE；本次对真实第 8/9 轮的独立核对也通过。两份 PDF 在审计期间未变。

以下为报告落盘前的阶段快照；以后变化以主控新回执为准：

- `reports/NLM_FINAL_AUDIT.json`：PASS。
- `CLOSEOUT_RECEIPT.json`：SCOPED_CLOSEOUT_COMPLETE。
- `runtime/package_validation.json`：WAITING_NOT_GENERATED。
- `runtime/github_anonymous_readback.json`：WAITING_NOT_GENERATED。
- `runtime/github_publication_proof.json`：WAITING_NOT_GENERATED。

没有把等待中的 package/匿名回读/public proof 判为代码失败。本轮没有直接验证远端发布、执行下载后核验器、重新计算全部统计结果、重新检查全部表格单元格、肉眼重审全部页面、全面扫描实际队列标识/凭据、运行全部 282 测试或检验 macOS 授权运行时。

## 下一步与回传

主控先对上述两个 P1 作窄修或记录固定载荷下的等效独立约束，再按原计划完成打包、真实隐私扫描、固定提交匿名回读和 public proof。无需因本审计追加任何模型、估计、NLM 轮次或 DOI 修稿。验收条件保持原样。

本报告与 JSON 先落盘，然后通知用户指定的 `%0`。已知 `tmux-bridge 2.0.0` 不存在 notify，不重试、不改全局工具；使用 `tmux display-message -t %0` 和 `tmux wait-for -S pp-lgcm-direct-audit-20261013`。不发送文字到输入框、不发送 Enter。实际通知返回码另外保存在 `runtime/executor_delivery_audit/notification.json`，不伪装成 V2 回执。
