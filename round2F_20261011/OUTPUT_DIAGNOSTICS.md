# 原始输出严重诊断与程序回执

本表保留原程序状态，另列原始Mplus诊断。没有重新估计、修改冻结代码或回写原始回执。

## CFPS_SD_E0_01_CC_F6

程序状态：`EXTRACTION_FAILED`；原始输出诊断：`STANDARD_ERRORS_UNAVAILABLE`。原始OUT第916—945行：

```text
THE STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE
     COMPUTED.  THE MODEL MAY NOT BE IDENTIFIED.  CHECK YOUR MODEL.
     PROBLEM INVOLVING THE FOLLOWING PARAMETER:
     Parameter 126, SX

     THE CONDITION NUMBER IS      -0.280D-06.
     THE FOLLOWING SET OF PARAMETERS IS INVOLVED IN THE NON-IDENTIFICATION
     Parameter 1, SX BY X2
     Parameter 2, SX BY X3
     Parameter 3, SX BY X4
     Parameter 4, X2
     Parameter 5, X3
     Parameter 6, X4
     Parameter 7, X5
     Parameter 8, Y2 WITH X2
     Parameter 9, Y2
     Parameter 10, Y3 WITH X3
     Parameter 11, Y3
     Parameter 12, Y4 WITH X4
     Parameter 13, Y4
     Parameter 14, Y5 WITH X5
     Parameter 15, Y5
     Parameter 16, [ SX ]
     Parameter 17, [ IX ]
     Parameter 18, [ IY ]
     Parameter 19, [ SY ]
     Parameter 20, SX ON Z0
```

输出未产生estimates.dat，TECH3为零字节；并非上传损坏。没有可报告的标准误或区间，不能视为完整控制敏感性通过。