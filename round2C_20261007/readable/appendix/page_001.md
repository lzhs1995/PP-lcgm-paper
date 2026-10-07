# 第1页

附录v40：检查点C 模型证据与推断说明

  本附录与正文v48 使用同一检查点C 结果。旧附录v39 完整保留为历史审计附件；其中历史表不并入本批正式证据。

    A. 数据、尺度与控制

  每份模型使用3274 人、2410 家庭及24 项基期编码列。CESD8 使用2012 年修正均值13.5754428833、标准差4.2592386459 统一标准化；X 沿用已冻结
wfdms 系列，入口尺度核对见input_scale_check.json。线性载荷0、.4、.6、.8、1，以十年为单位。自由形状X 固定首末载荷0 和1。

                               控制变量映射

   模型列                  源变量

     c1                                            sex12

     c2                                          edu12
     c3                                            urban12

     c4                                           prov122
     c5                                           prov123
     c6                                          cdn12

     c7                                             cdar12

     c8                                            cdsc121

     c9                                            cdsc122
     c10                                         minor12

     c11                                         ageg12
     c12                                            pinc12

     c13                                           pinc212
     c14                                             cores12

     c15                                            heal121
     c16                                            heal123
     c17                                         marr12

     c18                                         eco122
     c19                                         eco123

     c20                                      hwc122
     c21                                      hwc123