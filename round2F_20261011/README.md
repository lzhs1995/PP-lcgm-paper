# PP-LGCM Round2F：SD数值核查与敏感性（2026-10-11）

本轮没有形成通过预定验收的SD调节十份MI；SW和SD E0继续保留。 决定C；15次真实Mplus调用；正文v51、附录v43。此目录是完整的本批阶段交付，论文七项问题尚未全部解决。

建议先读[给网页端的说明](FOR_WEB_REVIEWERS.md)、[执行报告](REPORT.md)、[三方建议裁定](CONSENSUS.md)，再核对[全部调用](MODEL_INDEX.md)与[七项状态](SEVEN_ISSUES.csv)。当前稿件提供[正文Markdown](manuscripts/main_readable.md)、[附录Markdown](manuscripts/appendix_readable.md)、同版Word与PDF。

下载[PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json)列出的全部ZIP，解压到同一目录；每包≤25,000,000字节，都是独立有效ZIP。先校验每包大小、SHA-256和CRC，再按[FILE_MANIFEST.csv](FILE_MANIFEST.csv)核验内部文件。`.inp.txt/.out.txt`是原始输入输出的逐字节镜像，便于网页端读取。sources目录是原建议材料，实际执行版本仅为code目录及其冻结合同。

可在安装numpy、pandas、scipy的Python中运行：

```text
python reporting/verify_round2f.py --root . --output ../round2f_independent_check --terminal
```

该程序只复算公开聚合证据，不调用Mplus、不读取微观数据。精确观测似然回执由本机使用私有原数据产生，网页端不能仅凭本包重算它。生产估计和排版脚本保留本机路径与布局供审查；公开复核器使用上述相对根目录即可运行。

前轮基线：[Round2E固定提交](https://github.com/lzhs1995/PP-lcgm-paper/tree/a323b0eace23bb471a5b4b7e66fff5361de5d874/round2E_20261010)。本轮固定标签为`review-round2F-20261011`；上传后交付消息提供完整提交SHA和匿名下载复算结果。未公开任何参与者记录或插补对象。
