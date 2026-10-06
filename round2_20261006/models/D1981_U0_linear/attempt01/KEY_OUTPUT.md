# D1981_U0_linear / attempt01

状态：**REVIEWABLE**。数值仅在合法模型和对应研究范围内解释。

[完整输出](model.out.txt) · [输入](model.inp.txt)

```text
000024 INPUT READING TERMINATED NORMALLY
000146 THE MODEL ESTIMATION TERMINATED NORMALLY
000150 MODEL FIT INFORMATION
000151 
000152 Number of Free Parameters                       10
000153 
000154 Loglikelihood
000155 
000156           H0 Value                      -10083.663
000157           H0 Scaling Correction Factor      1.4723
000158             for MLR
000159           H1 Value                      -10064.479
000160           H1 Scaling Correction Factor      1.3783
000161             for MLR
000162 
000163 Information Criteria
000164 
000165           Akaike (AIC)                   20187.325
000166           Bayesian (BIC)                 20243.239
000167           Sample-Size Adjusted BIC       20211.468
000168             (n* = (n + 2) / 24)
000169 
000170 Chi-Square Test of Model Fit
000171 
000172           Value                             29.876*
000173           Degrees of Freedom                    10
000174           P-Value                           0.0009
000175           Scaling Correction Factor         1.2842
000176             for MLR
000177 
000178 *   The chi-square value for MLM, MLMV, MLR, ULSMV, WLSM and WLSMV cannot be used
000179     for chi-square difference testing in the regular way.  MLM, MLR and WLSM
000180     chi-square difference testing is described on the Mplus website.  MLMV, WLSMV,
000181     and ULSMV difference testing is done using the DIFFTEST option.
000182 
000183 RMSEA (Root Mean Square Error Of Approximation)
000184 
000185           Estimate                           0.032
000186           90 Percent C.I.                    0.019  0.045
000187           Probability RMSEA <= .05           0.989
000188 
000189 CFI/TLI
000190 
000191           CFI                                0.984
000192           TLI                                0.984
000193 
000194 Chi-Square Test of Model Fit for the Baseline Model
000195 
000196           Value                           1256.634
000197           Degrees of Freedom                    10
000198           P-Value                           0.0000
000199 
000200 SRMR (Standardized Root Mean Square Residual)
000201 
000202           Value                              0.031
000203 
000204 
000205 
000206 MODEL RESULTS
000207 
000208                                                     Two-Tailed
000209                     Estimate       S.E.  Est./S.E.    P-Value
000210 
000211  IY       |
000212     Y1                 1.000      0.000    999.000    999.000
000213     Y2                 1.000      0.000    999.000    999.000
000214     Y3                 1.000      0.000    999.000    999.000
000215     Y4                 1.000      0.000    999.000    999.000
000216     Y5                 1.000      0.000    999.000    999.000
000217 
000218  SY       |
000219     Y1                 0.000      0.000    999.000    999.000
000220     Y2                 4.000      0.000    999.000    999.000
000221     Y3                 6.000      0.000    999.000    999.000
000222     Y4                 8.000      0.000    999.000    999.000
000223     Y5                10.000      0.000    999.000    999.000
000224 
000225  SY       WITH
000226     IY                 0.002      0.005      0.360      0.719
000227 
000228  Means
000229     IY                -0.092      0.023     -4.073      0.000
000230     SY                 0.012      0.003      4.145      0.000
000231 
000232  Intercepts
000233     Y1                 0.000      0.000    999.000    999.000
000234     Y2                 0.000      0.000    999.000    999.000
000235     Y3                 0.000      0.000    999.000    999.000
000236     Y4                 0.000      0.000    999.000    999.000
000237     Y5                 0.000      0.000    999.000    999.000
000238 
000239  Variances
000240     IY                 0.453      0.041     11.112      0.000
000241     SY                 0.001      0.001      1.213      0.225
000242 
000243  Residual Variances
000244     Y1                 0.532      0.040     13.321      0.000
000245     Y2                 0.551      0.028     19.784      0.000
000246     Y3                 0.552      0.030     18.342      0.000
000247     Y4                 0.569      0.042     13.476      0.000
000248     Y5                 0.626      0.065      9.629      0.000
000249 
000250 
000251 QUALITY OF NUMERICAL RESULTS
000252 
000253      Condition Number for the Information Matrix              0.443E-04
000254        (ratio of smallest to largest eigenvalue)
000255 
000256 
```
