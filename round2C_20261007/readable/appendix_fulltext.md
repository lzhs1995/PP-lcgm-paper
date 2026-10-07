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

# 第2页

 模型列                  源变量

 c22                                        hukou12
 c23                                             adl12

 c24                                               finc12

B. 完整模型采用表

 模型       状态                       SY 残差     可采用

 C1_MI01         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI02         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI03         CONDITIONAL_FIXED_ZERO       0.000000       TRUE
 C1_MI04         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI05         CONDITIONAL_FIXED_ZERO       0.000000       TRUE
 C1_MI06         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI07         CONDITIONAL_FIXED_ZERO       0.000000       TRUE
 C1_MI08         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI09         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 C1_MI10         CONDITIONAL_FIXED_ZERO       0.000000       TRUE

 SW_MI01        CONDITIONAL_REVIEWABLE      0.032750       TRUE
 SW_MI02        CONDITIONAL_REVIEWABLE      0.032126       TRUE
 SW_MI03        CONDITIONAL_REVIEWABLE      0.033684       TRUE

 SW_MI04        CONDITIONAL_REVIEWABLE      0.033343       TRUE
 SW_MI05        CONDITIONAL_REVIEWABLE      0.033463       TRUE

 SW_MI06        CONDITIONAL_REVIEWABLE      0.029551       TRUE

 SW_MI07        CONDITIONAL_REVIEWABLE      0.033711       TRUE

 SW_MI08        CONDITIONAL_REVIEWABLE      0.032605       TRUE
 SW_MI09        CONDITIONAL_REVIEWABLE      0.035928       TRUE

 SW_MI10        CONDITIONAL_REVIEWABLE      0.032037       TRUE
 XLIN_MI01       INADMISSIBLE                      -0.087631       FALSE
 XLIN_MI02       INADMISSIBLE                      -0.087805       FALSE

# 第3页

 模型       状态                       SY 残差     可采用

 XLIN_MI03       INADMISSIBLE                      -0.083419       FALSE
 XLIN_MI04       INADMISSIBLE                      -0.084954       FALSE

 XLIN_MI05       INADMISSIBLE                      -0.085347       FALSE
 XLIN_MI06       INADMISSIBLE                      -0.091246       FALSE

 XLIN_MI07       INADMISSIBLE                      -0.086237       FALSE
 XLIN_MI08       INADMISSIBLE                      -0.087903       FALSE
 XLIN_MI09       INADMISSIBLE                      -0.082590       FALSE

 XLIN_MI10       INADMISSIBLE                      -0.088437       FALSE
 P002_MI01       CONDITIONAL_REVIEWABLE      0.020000       TRUE

 P008_MI01       CONDITIONAL_REVIEWABLE      0.080000       TRUE
 P020_MI01       CONDITIONAL_REVIEWABLE      0.200000       TRUE

 P040_MI01       CONDITIONAL_REVIEWABLE      0.400000       TRUE

C. 拟合指标

 模型             CFI             TLI          RMSEA       SRMR

 C1_MI01          0.978              0.965              0.013              0.023

 C1_MI02          0.977              0.964              0.013              0.023
 C1_MI03          0.978              0.965              0.013              0.023
 C1_MI04          0.977              0.964              0.013              0.023

 C1_MI05          0.977              0.964              0.013              0.023
 C1_MI06          0.978              0.965              0.013              0.023

 C1_MI07          0.977              0.964              0.013              0.023

 C1_MI08          0.976              0.963              0.013              0.023

 C1_MI09          0.977              0.964              0.013              0.023
 C1_MI10          0.977              0.964              0.013              0.023

 SW_MI01          0.984              0.974              0.011              0.022
 SW_MI02          0.983              0.973              0.012              0.023
 SW_MI03          0.984              0.974              0.011              0.023

# 第4页

 模型             CFI             TLI          RMSEA       SRMR

 SW_MI04          0.983              0.972              0.012              0.023
 SW_MI05          0.983              0.972              0.012              0.023

 SW_MI06          0.983              0.973              0.011              0.023
 SW_MI07          0.983              0.972              0.012              0.023

 SW_MI08          0.982              0.971              0.012              0.023
 SW_MI09          0.983              0.972              0.012              0.023
 SW_MI10          0.983              0.972              0.012              0.023

 XLIN_MI01        0.972              0.957              0.015              0.024
 XLIN_MI02        0.971              0.956              0.015              0.024

 XLIN_MI03        0.972              0.957              0.015              0.024
 XLIN_MI04        0.971              0.955              0.015              0.024

 XLIN_MI05        0.971              0.955              0.015              0.024
 XLIN_MI06        0.972              0.956              0.015              0.024

 XLIN_MI07        0.971              0.955              0.015              0.024

 XLIN_MI08        0.97               0.954              0.015              0.024
 XLIN_MI09        0.971              0.955              0.015              0.024

 XLIN_MI10        0.971              0.955              0.015              0.024
 P002_MI01        0.978              0.965              0.013              0.023

 P008_MI01        0.978              0.965              0.013              0.023
 P020_MI01        0.977              0.964              0.013              0.023

 P040_MI01        0.973              0.958              0.014              0.024

D. 第一份插补的固定残差剖面

 固定残差   路径     估计         SE        95%条件   合法
                           区间

 0.00               bii              -0.424          0.104            [-0.628, -     TRUE
                                                               0.220]
 0.00              bis             0.195           0.188            [-0.174,      TRUE
                                                               0.563]

# 第5页

固定残差   路径     估计         SE        95%条件   合法
                          区间

0.00             bss              -0.716          0.473            [-1.642,      TRUE
                                                             0.211]
0.00            bsyiy           0.426           0.137            [0.158,       TRUE
                                                             0.694]
0.02               bii              -0.418          0.102            [-0.618, -     TRUE
                                                             0.218]
0.02              bis             0.166           0.175            [-0.177,      TRUE
                                                             0.510]
0.02             bss              -0.687          0.422            [-1.514,      TRUE
                                                             0.140]
0.02            bsyiy           0.386           0.132            [0.126,       TRUE
                                                             0.645]
0.08               bii              -0.404          0.097            [-0.594, -     TRUE
                                                             0.213]
0.08              bis             0.091           0.148            [-0.199,      TRUE
                                                             0.380]
0.08             bss              -0.621          0.313            [-1.233, -     TRUE
                                                             0.008]
0.08            bsyiy           0.267           0.122            [0.028,       TRUE
                                                             0.506]
0.20               bii              -0.385          0.095            [-0.571, -     TRUE
                                                             0.199]

0.20              bis              -0.032          0.116            [-0.259,      TRUE
                                                             0.196]
0.20             bss              -0.544          0.196            [-0.927, -     TRUE
                                                             0.160]
0.20            bsyiy           0.044           0.107            [-0.165,      TRUE
                                                             0.254]
0.40               bii              -0.380          0.103            [-0.582, -     TRUE
                                                             0.178]
0.40              bis              -0.167          0.086            [-0.336,      TRUE
                                                             0.001]

# 第6页

   固定残差   路径     估计         SE        95%条件   合法
                             区间

      0.40             bss              -0.479          0.117            [-0.708, -     TRUE
                                                                   0.250]
      0.40            bsyiy           -0.247          0.085            [-0.414, -     TRUE
                                                                   0.081]

  单份区间为固定规格下渐近Wald 诊断。非法点仅保留定位信息；本表不是MI 区间、置信集合或边界检验。

    E. 条件MI 合并与模拟精度

   规格     路径          p           FMI         MCSE/SE   精度标记

    C1                 bii             0.00005        0.00097        0.00941      FALSE
    C1               bis             0.30058        0.00048        0.00662      FALSE

    C1              bss             0.13361        0.00056        0.00712      FALSE
    C1              bsyiy           0.00194        0.00114        0.01020      FALSE

   SW                bii             0.01744        0.00079        0.00849      FALSE
   SW              bis             0.70564        0.00022        0.00451      FALSE
   SW             bss             0.68621        0.00035        0.00563      FALSE

   SW             bsyiy           0.15619        0.00064        0.00762      FALSE

   MCSE/SE 超过.05 仅作报告标记，不自动追加插补。使用大样本完整数据自由度近似下的Rubin 规则，协方差按同一参数顺序合并，不平均P 值。

     F. 参数几何与追溯

    PSI 为增长因子结构残差协方差，G 为给定协变量后的增长因子联合协方差，THETA 为测量残差协方差，SIGMA 为模型蕴含的条件观测协方差。
TECH3 为参数估计协方差，不能替代上述潜变量几何检查。预定SY=0 允许PSI/G 的零特征值，其他负方差或额外秩亏仍不通过。

  完整输入、输出、TECH1/TECH3/TECH4、参数顺序绑定、局部残差、数据哈希、起点核查与独立复算记录见配套公开数据包。微观数据、真实人员／
家庭标识和插补对象未公开。所有模型尝试与未采用结果均保留。