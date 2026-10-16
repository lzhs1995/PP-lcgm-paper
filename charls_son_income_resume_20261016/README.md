# CHARLS SON×收入续算交付

**四项调节完整推断、完整 H4 仍未完成。**

[报告](REPORT.md) · [结果讨论](RESULTS_DISCUSSION.md) · [12家族表](H41_REGISTERED_12.csv) · [组内路径及直接组差](GROUP_CONTRASTS.csv) · [区间图](H41_GROUP_DIFFERENCES.pdf) · [包清单](PACKAGE_MANIFEST.json)

本批只新增SON收入完整40份家族及首成员第二起点；旧SON完整案例和其他11家族均复用。旧超时保留，诊断与独立续算证据在包内，未修改原数据或冻结论文，未重跑失败CFPS规格。

所有ZIP小于25,000,000字节。合并解压后按PAYLOAD_MANIFEST.json逐项检查SHA-256，执行：

`python verification/verify_h41_results.py --public --root . --output PUBLIC_RECOMPUTATION.json`

需要numpy、pandas、scipy；直接复算保存参数、TECH3及完整40份合并，不重新拟合，不读取未公开微观数据。其余11家族汇总沿用下列固定提交，不重复上传原模型包：

- [教育/城乡8家族](https://github.com/lzhs1995/PP-lcgm-paper/tree/950a01ea8599e0782cc3685563c98265c4fc924f/charls_h41_mi_20261016)
- [收入3家族及旧SON失败](https://github.com/lzhs1995/PP-lcgm-paper/tree/d43c9cca8d77f077e824ff09ebfc36d5b0324b26/charls_income_h41_mi_20261016)

本批H4.1为基期Z₀×资源组条件异质性，不能代替SX×Z₀动态调节或H4.2三重交互。CHARLS测量见面频率和家庭净收入，与CFPS情感亲近度/个人收入不同。FCS仍为工作近似；区间为逐参数区间；先看联合检验和固定多重比较，不挑选有星号结果。
