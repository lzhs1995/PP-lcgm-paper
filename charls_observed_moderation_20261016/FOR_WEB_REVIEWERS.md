# 给网页端审阅者

请先读REPORT、BATCH_RECEIPT和RUN_CONTRACT。本包是四个CHARLS观测基期调节完整案例可行性分支，不是四项完整MI推断，也不是CFPS稿件定稿。H4.1仍3/12个条件家族；完整H4未完成。请勿要求重复既有CFPS失败规格或重新审阅旧范围收缩稿。

包内保留各父模型、两个起点、原始输出、高精度参数、全TECH3、独立数值回读及条件曲线。可运行`python code/verify_public_bundle.py`核验哈希，再运行`python code/verify_pilots.py`复算保存结果；后者需要numpy、pandas、scipy，不调用Mplus，也不意味着重新拟合微观数据。

值得评估的是：见面频率的数值编码与研究解释、完整案例的选择性、下一步交互相容缺失处理，以及H4.1/H4.2的估计对象。不能以单份不显著、加法MI的低FMI或另一数据集的结果预测尚未执行的完整家族。

公开包没有个人级数据。estimates.dat和tech3.dat只是参数与其协方差；个人data.dat、MI及RDS均未上传。源码路径已脱敏，本机微观复现需另行绑定合法数据。
