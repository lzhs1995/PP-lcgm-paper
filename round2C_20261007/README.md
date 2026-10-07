# PP-LGCM Round2C：检查点C

请先读[报告](REPORT.md)、[给网页评审者的说明](FOR_WEB_REVIEWERS.md)、[采用门槛](audit/family_gates.csv)与[交付范围](DELIVERY_SCOPE.json)。本批数据来源固定于前批提交`a666e0ea8a610159709bb504d3d275f6f582efb9`。

本批包含三类模型各十份、MI01固定残差剖面及必要起点核查。正文v48/附录v40是当前审阅候选；`manuscript/historical_audit/`内v47/v39仅供追溯。所有模型输入输出均有TXT镜像，当前PDF亦附逐页Markdown与全文，便于网页端直接读取。

下载包和SHA-256见[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)；逐文件清单见[FILE_MANIFEST.csv](FILE_MANIFEST.csv)。每包≤25,000,000字节。GitHub目录提供与ZIP同版的可读文件。未公开CFPS微观数据、真实PID/FID或插补对象。

本轮停止在检查点C；没有新调节、H4.2b、窗口模型、新MI或bootstrap。不要将未执行当作无效应，也不要将C1的固定零方差当作边界检验结果。
