# CHARLS 四类潜在家内差异轨迹：有限可行性批次

**四项调节完整推断、完整 H4 仍未完成。** 本批是修正来源下的四条潜在差异轨迹诊断，不是已完成的观测基期差异×资源 H4.1 的重复估计，不是原CFPS结果复现，也没有修改已收尾稿。

## 结果与执行范围

实际调用 16 次 Mplus；引擎及启动清醒墙钟 1280.855 秒；原始自由参数独立核验 596 个。最多20次、总计3600秒的合同事前冻结；单过程/父模型120秒，交互240秒。没有新MI，也没有原样重跑失败CFPS。

|指标|诊断样本N|采用的Z形态|分支终态|
|---|---:|---|---|
|SD|2672|latent_basis|INTERACTION_NOT_ADMITTED|
|儿子与女儿差|2071|latent_basis|INTERACTION_NOT_ADMITTED|
|最年长子女与其余子女差|2380|latent_basis|INTERACTION_NOT_ADMITTED|
|长子与其余子女差（含女儿）|2246|latent_basis|INTERACTION_NOT_ADMITTED|

USABLE_CC_DIAGNOSTIC只指本次完整控制样本中可接受的诊断解。TWO_START_CC_FEASIBLE_NOT_MI即使出现，也不是完整插补推断。TIMEOUT仅说明在本次机器与预算下未完成，不能改写为不收敛、无效应或理论不可识别。PARENT_NOT_ADMITTED、INTERACTION_NOT_ADMITTED的具体原因必须看原始输出和validation。所有尝试保留，不挑选成功成员拼接家族。

## 设计与适用边界

从修正来源的同波完整子女名册计算绝对SD/差值，以冻结的基期均值和标准差统一标准化。限定基期差异已定义、至少两波Z可用、11项基期控制完整，并排除任何已观测的结构性未定义和排行并列。四样本不是同一人群，也不代表所有多子女老人；按后续名册筛选可能造成选择，不能将本批估计直接当作总体机制证据。

余下未链接名册或题目缺失保持缺失，未将结构性无对比补值。FIML是本批工作假设，不证明MAR。逐人ID、源数据、DAT和RDS均仅在本机隔离目录保留。

每条Z先比较线性与自由载荷两候选，在相同样本的合法解中按BIC选取，无p值选择。载荷时间为0、2、4、7、9；自由载荷模型中中间三载荷可变，末期固定9，所以SZ表示两端变化除以9，不保证每个相邻区间同向。X/Y保持年度线性；三个过程都有11控制，保留同波残差相关与低阶路径。父模型可采用后才尝试SX×IZ→SY的潜变量交互，两个起点从同一个无交互父模型分别构造，不从交互终点续跑。没有为取得合法解把负方差固定为零。

CHARLS这里测量联系频率，不能与CFPS情感亲近度混称。同波名册也不保证历年一直由同一组子女构成。

## 标签勘误

SON的实际公式在基期与追访一致：唯一长子减去其余所有子女的均值，其余子女包括女儿。既有部分报告“儿子内排行差”的标签不准确，应以上述含义为准。这里只更正说明，既有H4.1数据、MI与估计未改、不重跑；完整代码证据见SON_DEFINITION_CLARIFICATION.md。

## 逐次调用

|调用|状态|引擎及启动秒|
|---|---|---:|
|CHARLS_LATENT_SD_Z_LINEAR_A|USABLE_CC_DIAGNOSTIC|96.74|
|CHARLS_LATENT_SD_Z_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|14.628|
|CHARLS_LATENT_SD_E0_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|29.941|
|CHARLS_LATENT_SD_E1_LATENT_BASIS_A|TIMEOUT|240.482|
|CHARLS_LATENT_GENDER_Z_LINEAR_A|USABLE_CC_DIAGNOSTIC|15.296|
|CHARLS_LATENT_GENDER_Z_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|35.482|
|CHARLS_LATENT_GENDER_E0_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|31.978|
|CHARLS_LATENT_GENDER_E1_LATENT_BASIS_A|TIMEOUT|241.036|
|CHARLS_LATENT_OLDEST_Z_LINEAR_A|USABLE_CC_DIAGNOSTIC|14.529|
|CHARLS_LATENT_OLDEST_Z_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|11.398|
|CHARLS_LATENT_OLDEST_E0_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|22.703|
|CHARLS_LATENT_OLDEST_E1_LATENT_BASIS_A|TIMEOUT|241.524|
|CHARLS_LATENT_SON_Z_LINEAR_A|USABLE_CC_DIAGNOSTIC|10.549|
|CHARLS_LATENT_SON_Z_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|10.59|
|CHARLS_LATENT_SON_E0_LATENT_BASIS_A|USABLE_CC_DIAGNOSTIC|23.28|
|CHARLS_LATENT_SON_E1_LATENT_BASIS_A|TIMEOUT|240.701|

## 交互计算成本实测

|调用|状态|引擎及启动秒|抽样进程树CPU秒|峰值进程树RSS MiB|
|---|---|---:|---:|---:|
|CHARLS_LATENT_SD_E1_LATENT_BASIS_A|TIMEOUT|240.48|230.61|265.69|
|CHARLS_LATENT_GENDER_E1_LATENT_BASIS_A|TIMEOUT|241.04|166.02|245.46|
|CHARLS_LATENT_OLDEST_E1_LATENT_BASIS_A|TIMEOUT|241.52|237.14|256.21|
|CHARLS_LATENT_SON_E1_LATENT_BASIS_A|TIMEOUT|240.7|229.92|251.6|

CPU时间和RSS为实际进程树抽样，不能当作纯Mplus精确计费或完整物理内存账。本批固定PROCESSORS=1、单槽；接近一核的CPU持续消耗与较小的内存占用支持“本批交互主要在计算”的判断，不能将所有历史缓慢都归为内存不足。首个模型启动与后续缓存命中的时间不同，不能直接当作模型之间的算法速度比较。后续若考虑多线程、降低积分成本或等价模型，需有新的有限校准依据；本批不会因已超时就无限延长或事后改变合同。

## RStudio恢复经验与已完成资产

本批准备任务534d4c97和估计任务45e784d3都曾在提交时收到通信错误，但真实R日志和原生轮询证明已接单。均恢复原job，未重复提交。原错误、实际恢复响应与终态分别保存，不能把恢复轮询伪装成成功提交回执。8787主会话保留，其他项目8789未接管；CPU亲和只调整所属进程，单槽执行。

完整HTTP故障时间线已沉淀到mplusautomation-guide PR41（合并提交d3d6fc06269697a6d6988e59ff992c79d68012c3），包括2秒健康探测的通用误报、仅重启HTTP而保留R、显式绑定避免会话漂移、原job恢复和失败边界。原长期阻塞的底层原因未唯一确定，不能归结为内存不足，也不宣称已安装全局无人值守自动重启服务。

修正来源观测基期差异×教育/城乡/收入的12个条件H4.1家族已完成，320个MI成员已在固定提交5f426bd6b8532c1b79dcdcec2c841a07f369920b及所链接的教育/城乡包中交付；12项Holm均未达5%。这些资产不重算，也不能代替本批潜在IZ调节与H4.2。下一步只能根据本批实际分支结果决定可行分支的缺失控制处理与完整家族；失败分支没有自动重试授权含义。

公开包可独立复算保存参数与TECH3，但没有微观资料，不能声称云端重拟合。运行code/verify_saved_parameters.py；无需读取本机私有目录。此处是研究批次报告，不是新增的文稿或NLM审阅轮次。
