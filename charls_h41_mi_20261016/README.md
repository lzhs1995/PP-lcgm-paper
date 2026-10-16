# CHARLS H4.1：教育与城乡

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [网页端说明](FOR_WEB_REVIEWERS.md) · [实际回执](BATCH_RECEIPT.json) · [家族状态](FAMILY_OVERVIEW.csv) · [直接联合组差检验](JOINT_D1.csv)

本批为四个基期家内差异 × 教育／城乡的CHARLS H4.1。新插补包含观测资源乘积，但保留FCS工作近似边界；不是CFPS或潜变量动态交互的完整推断。

解压后运行`python code/verify_public_bundle.py`核验哈希，再运行`python code/verify_h41_results.py`独立复算原始保存参数/TECH3与合并。需要numpy/pandas/scipy，不调用Mplus。包内不含个人数据和实际MI。指南经验见[mplusautomation-guide PR25](https://github.com/lzhs1995/clauder-rstudio-workbench/pull/25)。
