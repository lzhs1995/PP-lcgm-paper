# CHARLS H4.2 ALL阶段报告

**四项调节完整推断、完整 H4 仍未完成。**

本阶段有11/12个完整工作插补家族经原始参数、TECH3、双起点和独立Rubin复算核对。每个已完成家族保留全部预定插补成员；没有按显著性选择或替换成员。生成时间：2026-10-17T10:57:46.767021+00:00。

## 当前研究边界

CHARLS条件H4.1已完成12/12家族（教育/城乡各20份，收入各40份）；CFPS条件H4.1仍3/12。四项CHARLS动态调节各20份工作敏感性已另批完成；这些均不等于原CFPS四项调节或完整H4完成。本阶段检验的是观测基期Z与资源G对SX→SY关联的三重交互。

这里的H4.1完成数仅指已登记的基期观测差异条件家族。原稿H4.1还涉及差异轨迹变化及其他关联的资源差异，不能以12/12替代原假设的全部范围。CHARLS的Z采用绝对SD或有符号差，不等同CFPS的相对差异；四个Z也不能统一解释为数值越大越不和谐。H4.1a/b与H4.2a/b的竞争方向须结合组内效应、直接组差及指标含义判断。

CHARLS为子女见面频率，并非CFPS情感亲近度；收入为家庭净收入、固定观察队列中位数8730元分组，不是CFPS个人收入。原稿、已冻结收缩稿、原始数据均未覆盖；未原样重跑失败CFPS规格。

指标对应为SD＝绝对标准差，GENDER＝儿子减女儿，OLDEST＝最年长子女减其他子女，SON＝长子减所有其他子女；均沿用已冻结的见面频率编码、子女来源规则与量尺。收入G=1为基期家庭净收入严格大于8730元，G=0为不超过8730元。不同指标的有效样本不同，不能直接比较系数大小判断相对重要性。

## 完整家族结果

| 家族 | 完整成员 | 状态 | 直接组差 | 95% MI区间 | P | Holm（固定12项） |
|---|---:|---|---:|---|---:|---:|
| sd_EDU | 20/20 | FULL_CONDITIONAL_MI_POOLED | 0.0811298 | [-0.105926, 0.268186] | 0.395283 | 1 |
| sd_URBAN | 20/20 | FULL_CONDITIONAL_MI_POOLED | -0.0218481 | [-0.225297, 0.181601] | 0.833295 | 1 |
| sd_INC | 0/40 | IMPUTATION_NOT_ADMITTED | — | [—, —] | — | — |
| gender_EDU | 20/20 | FULL_CONDITIONAL_MI_POOLED | 0.00854695 | [-0.187055, 0.204149] | 0.931751 | 1 |
| gender_URBAN | 20/20 | FULL_CONDITIONAL_MI_POOLED | 0.0520298 | [-0.153131, 0.25719] | 0.619148 | 1 |
| gender_INC | 40/40 | FULL_CONDITIONAL_MI_POOLED | 0.0610435 | [-0.195173, 0.31726] | 0.64036 | 1 |
| oldest_EDU | 20/20 | FULL_CONDITIONAL_MI_POOLED | -0.178902 | [-0.402598, 0.0447935] | 0.116999 | 1 |
| oldest_URBAN | 20/20 | FULL_CONDITIONAL_MI_POOLED | -0.0211058 | [-0.298047, 0.255836] | 0.881262 | 1 |
| oldest_INC | 40/40 | FULL_CONDITIONAL_MI_POOLED | -0.168819 | [-0.423072, 0.0854342] | 0.192958 | 1 |
| son_EDU | 20/20 | FULL_CONDITIONAL_MI_POOLED | -0.059988 | [-0.294644, 0.174668] | 0.616336 | 1 |
| son_URBAN | 20/20 | FULL_CONDITIONAL_MI_POOLED | 0.0939044 | [-0.164069, 0.351878] | 0.475572 | 1 |
| son_INC | 40/40 | FULL_CONDITIONAL_MI_POOLED | -0.048532 | [-0.348864, 0.2518] | 0.751283 | 1 |

直接组差对应dcg；组内调节分别为dc和dc+dcg，不能通过比较两组星号推断组差。条件斜率使用bss+dc*z+bxg*g+dcg*z*g及完整协方差；只展示共同支持点。MCSE和社区自由度敏感性随各家族结果保存。区间跨零不是无效应证明。

## 缺失处理

基期核心控制为年龄、性别、教育、城乡、伴侣、有效子女报告数、ADL及自评健康四个虚拟变量，共11列。收入范围另加入家庭净收入高低G及相关低阶项。沿用已核验的ADL来源和跨期性别恢复记录；ADL总分非缺失不等于六项原始条目均完整。教育高组为初中及以上，城乡高组为城市。

教育/城乡部分仅ADL未完整；以社区随机截距PMM5生成每范围20份独立条件抽样，保留观察值与X/Y FIML掩码。辅助矩阵纳入Z、资源与各波次的乘积；满秩及全预测行重建已核验。仅缓存确定性拟合，随机抽样未复用。

收入同时存在G与ADL缺失，新条件设计加入动态代理辅助量和被动乘积，并保留独立小试、完整MIDS/RNG和限时规则。仅完成40链及混合、实际DAT验收的家族进入后续估计；小试不计作正式MI。本次读取的入口状态：sd: 尚无正式完整家族放行记录；gender: COMPLETE40_WORKING_MI_ADMITTED（完整放行=True）；oldest: COMPLETE40_WORKING_MI_ADMITTED（完整放行=True）；son: COMPLETE40_WORKING_MI_ADMITTED（完整放行=True）。以上均为工作插补近似，不证明潜交互精确实质模型相容性或MAR。

收入二项条件拟合使用本批代码中的glmmTMB Laplace后端，ADL使用miceadds随机截距PMM5；软件版本与抽样器适配记录随包保留。缓存只复用数据和规格完全相同的确定性拟合，后续随机抽样仍逐次重新生成；条件调用次数不等于独立拟合优化次数。

## 恢复与效率

Windows重启后复用了37个合法输出和80份ADL数据；后续协调连接错误时另一个正常完成的输出也直接回读。错误、陈旧锁、预算和调用记录保留；未因监控故障重新拟合成功模型。内存/commit/CPU准入和总引擎预算继续执行，只有按实测记录修订的外部进程数门槛。

## 可追溯结果

- results/pool_ALL/H42_REGISTERED.csv
- 各家族MEMBER_SOURCES、MEMBER_ESTIMATES、MEMBER_COVARIANCES、POOLED_PATHS、GROUP_MODERATION_CONTRASTS、CONDITIONAL_SLOPES和CLUSTER_DF_SENSITIVITY
- audit/POOL_INDEPENDENT_ALL.json
- audit/reboot_20261017、audit/connection_error_20261017、audit/awake_stale_receipt_20261017、audit/title_length_failure_20261017

本报告是阶段研究结果，不是冻结论文的新版本，不触发新NLM审阅或已经成功模型的重复估计。
