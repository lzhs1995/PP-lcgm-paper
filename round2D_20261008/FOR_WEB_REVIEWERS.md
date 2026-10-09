# 给ChatGPT网页端与Claude网页端的Round2D阶段评议说明

这是上一轮SW父模型之后的阶段交付。潜调节长耗时且未形成完整可采用MI估计，已按用户批准的预算停止追加。观测基期替代、H4和六次短测速均延期，尚未执行。请先读[STAGE_SUMMARY](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/STAGE_SUMMARY.md)、[完整报告](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/REPORT.md)、[外部建议裁定](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/reports/REVIEW_SYNTHESIS.md)、[采用状态](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/results/family_status.csv)和[模型索引](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/MODEL_INDEX.md)，再对照正文v49和附录v41阶段稿。

请直接核对实际文件，不把任务书、程序测试或“正常结束”替代真实模型验收。包清单见[PACKAGE_MANIFEST](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/PACKAGE_MANIFEST.json)，全部ZIP解压至同一目录后，`code/09_independent_verify.py --root <目录> --require-terminal --evidence-output <另一个输出目录>`可重算公开聚合证据并保持解压包不变；需要numpy、pandas与scipy，这不会重新拟合微观数据。

请重点回应：

1. 当前停止追加的决定是否合理？请结合[FAMILY_EXECUTION_DETAILS](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/FAMILY_EXECUTION_DETAILS.csv)及[逐目标延期台账](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/TARGET_DISPOSITIONS.csv)，区分信息矩阵求逆失败、负方差、超时和未执行；不要将其转写成四种调节均不存在。
2. 六个增长因子、同源比值指标、零值集中及连续高斯近似，哪些可能影响识别和条件数？请提出能区分这些解释的最小诊断，不能只猜一个唯一原因，也不要按P值删除控制或同期残差。
3. [性能复核](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/audit/PERFORMANCE_REVIEW_20261009.md)与[最终耗时表](https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/review-round2D-20261008/round2D_20261008/PERFORMANCE_FINAL.csv)显示主要耗时在引擎。PROCESSORS=1有改进空间，但两维15点积分是225节点，Monte Carlo5000不保证更快，纯EM修复也未获得合法解。六个短探针尚未运行；是否应先做有限1/2/4核校准或合法起点映射？请给出次数、时限、数值精度标准和停止条件，不直接建议再运行数十小时。
4. 是否优先采用SW加观测2012年Z₀的备用设计？该设计改变估计对象；请给出理论得失、最小SD试运行与验收要求。H4尚未执行，若将来恢复，须直接检验三阶差异，有个人收入须区别于高收入。
5. 当前MI预测矩阵与潜交互的具体相容性缺口应如何处理？请区分数据层已修复、条件工作推断和新插补敏感性，不重复宣布家庭共同值未修复；使用因子得分或Bayes也需说明估计对象与不确定性变化。
6. 正文v49/附录v41与本批实际结果是否同步？引文保留及明确删除记录、CES-D共同八题、原始分与标准化时间尺度、MI链诊断、所有原假设状态有无遗漏？Brown/Friedman错置引文已明确移除，请勿以机械保留原72域为验收要求。
7. 哪些问题可关闭，哪些只达到工作模型层面，哪些延期？请将建议按“无需新估计即可确认／有界小试／暂不值得继续”排序，注明改变什么、最多几次／多久、成功与停止标准，并引用本包具体文件。

本包不含真实PID/FID、微观收入、个人DAT、逐人因子得分或插补对象。可复核保存统计量、代码与聚合证据；不能宣称已在云端独立重估全部CFPS个人记录。两位网页端此前审阅过的资料不等于已经审阅本轮新增结果。

关于建议分歧：本轮保留四项SX×IZ主线，不扩IX交互；C1结构嵌套于SW，但不使用普通缩放df=6卡方直接作边界显著性判断；不根据父模型SE预判交互毫无信息，不用临时SESOI或任意家庭数减参数数的自由度。具体理由和已核实的文献疑点见外部建议裁定。
