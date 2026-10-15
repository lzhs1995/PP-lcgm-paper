# 网页复核说明

先读REPORT.md及BATCH_RECEIPT.json。本批是收尾稿之后经授权的新研究增量。请区分H4.1条件MI、四项动态调节、H4.2和CHARLS加法资源调整；这些不是同一估计对象。

请重点复核新H4.1规格与旧失败规格的差别、停止家族是否遵循冻结规则、CHARLS两组真实20链合并、原观测和原始供体保留、合并协方差与缺失假设。未形成完整家族不等于零效应。不要用一项合法模型的小FMI推断另一未运行模型。

包不含个人数据，云端可复算保存参数/TECH3及合并，不能声称重新拟合了微观CFPS或CHARLS。解压两包到同一目录后运行python code/verify_current_pooling.py；所需Python包为numpy、pandas、scipy。每个ZIP小于25MB，校验值和逐文件清单随包。
