# CHARLS 潜在 SX×IZ 调节：本批结果与边界

**四项调节完整推断、完整 H4 仍未完成。** 这句话指原CFPS研究的完整时间路径与H4覆盖。本批推进的是CHARLS四个指标的一个明确潜在交互路径：SX×IZ→SY；不能用它替代全部原时间路径或H4.2三重交互。

此前已完成的12个潜H4.1工作家族320主MI复用，不重复估计。本批改变的是有实测依据的求积规则，保留模型结构、控制变量、自由残差方差和收敛标准。完整案例分别核验7/15点及独立父起点。之后另做包含25个观测X×Z辅助项的ADL-only工作MI；每指标20份，仅填补缺失ADL，原XYZ和已观测控制保持。辅助项并不证明严格潜交互相容性或MAR。

20主成员全部可采用且首份双起点通过，才合并全部127参数和完整robust协方差；使用Rubin合并，附社区自由度敏感性与MCSE/SE。主交互按计划四指标Holm校正，无p值筛选。CC的7→15点检查不能冒充全部MI成员均做过积分阶数敏感性。

| Indicator | N | delta | 95% conditional MI interval | p | Holm, planned four |
|---|---:|---:|---|---:|---:|
| sd | 2689 | 0.041955 | [-0.122427, 0.206337] | 0.616903 | 0.616903 |
| gender | 2085 | -0.099349 | [-0.221080, 0.022382] | 0.109688 | 0.438754 |
| oldest | 2397 | 0.094699 | [-0.048754, 0.238152] | 0.195717 | 0.587152 |
| son | 2263 | -0.075832 | [-0.215289, 0.063625] | 0.286531 | 0.587152 |

每个指标终态：
{
  "sd": {
    "terminal": true,
    "indicator": "sd",
    "queue": "q1",
    "completed_A": 20,
    "status": "COMPLETE_20_MI_WORKING_MODEL",
    "original_CFPS_four_complete": false,
    "full_H4_complete": false
  },
  "gender": {
    "terminal": true,
    "indicator": "gender",
    "queue": "q2",
    "completed_A": 20,
    "status": "COMPLETE_20_MI_WORKING_MODEL",
    "original_CFPS_four_complete": false,
    "full_H4_complete": false
  },
  "oldest": {
    "terminal": true,
    "indicator": "oldest",
    "queue": "q1",
    "completed_A": 20,
    "status": "COMPLETE_20_MI_WORKING_MODEL",
    "original_CFPS_four_complete": false,
    "full_H4_complete": false
  },
  "son": {
    "terminal": true,
    "indicator": "son",
    "queue": "q2",
    "completed_A": 20,
    "status": "COMPLETE_20_MI_WORKING_MODEL",
    "original_CFPS_four_complete": false,
    "full_H4_complete": false
  }
}

打包只含聚合估计、原始参数保存文件、代码和核验凭证，不含个人DAT、RDS、MIDS或逐人因子得分。完整家族已经在真实解压目录重新执行独立原始参数与Rubin读回；这不是重新拟合。文件白名单和内容检查不以CSV行数代替数据分类。

本批没有改动原始数据、历史CFPS输出或封存稿，没有新增NLM或改写论文。CHARLS的见面频率与CFPS亲近度、绝对SD与相对SD、各资源定义不能混称；本批保留sd/gender/oldest/son的既有输入定义。

后续以原假设覆盖表确定尚缺的时间交互和H4.2，先复用本批父模型、准入结果及失败记录；不原样重跑已经失败的CFPS规格，也不把不显著当作数值故障修复。
