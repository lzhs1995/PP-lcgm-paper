# D2225_U0_four_linear / attempt01

状态：**REVIEWABLE**。数值仅在合法模型和对应研究范围内解释。

[完整输出](model.out.txt) · [输入](model.inp.txt)

```text
000024 INPUT READING TERMINATED NORMALLY
000141 THE MODEL ESTIMATION TERMINATED NORMALLY
000145 MODEL FIT INFORMATION
000146 
000147 Number of Free Parameters                        9
000148 
000149 Loglikelihood
000150 
000151           H0 Value                      -17600.343
000152           H0 Scaling Correction Factor      1.4291
000153             for MLR
000154           H1 Value                      -17589.752
000155           H1 Scaling Correction Factor      1.3590
000156             for MLR
000157 
000158 Information Criteria
000159 
000160           Akaike (AIC)                   35218.687
000161           Bayesian (BIC)                 35270.054
000162           Sample-Size Adjusted BIC       35241.460
000163             (n* = (n + 2) / 24)
000164 
000165 Chi-Square Test of Model Fit
000166 
000167           Value                             17.181*
000168           Degrees of Freedom                     5
000169           P-Value                           0.0042
000170           Scaling Correction Factor         1.2329
000171             for MLR
000172 
000173 *   The chi-square value for MLM, MLMV, MLR, ULSMV, WLSM and WLSMV cannot be used
000174     for chi-square difference testing in the regular way.  MLM, MLR and WLSM
000175     chi-square difference testing is described on the Mplus website.  MLMV, WLSMV,
000176     and ULSMV difference testing is done using the DIFFTEST option.
000177 
000178 RMSEA (Root Mean Square Error Of Approximation)
000179 
000180           Estimate                           0.033
000181           90 Percent C.I.                    0.017  0.051
000182           Probability RMSEA <= .05           0.941
000183 
000184 CFI/TLI
000185 
000186           CFI                                0.986
000187           TLI                                0.983
000188 
000189 Chi-Square Test of Model Fit for the Baseline Model
000190 
000191           Value                            857.067
000192           Degrees of Freedom                     6
000193           P-Value                           0.0000
000194 
000195 SRMR (Standardized Root Mean Square Residual)
000196 
000197           Value                              0.034
000198 
000199 
000200 
000201 MODEL RESULTS
000202 
000203                                                     Two-Tailed
000204                     Estimate       S.E.  Est./S.E.    P-Value
000205 
000206  IY       |
000207     Y1                 1.000      0.000    999.000    999.000
000208     Y2                 1.000      0.000    999.000    999.000
000209     Y3                 1.000      0.000    999.000    999.000
000210     Y4                 1.000      0.000    999.000    999.000
000211 
000212  SY       |
000213     Y1                 0.000      0.000    999.000    999.000
000214     Y2                 2.000      0.000    999.000    999.000
000215     Y3                 4.000      0.000    999.000    999.000
000216     Y4                 6.000      0.000    999.000    999.000
000217 
000218  SY       WITH
000219     IY                -0.356      0.176     -2.023      0.043
000220 
000221  Means
000222     IY                13.307      0.096    138.237      0.000
000223     SY                 0.108      0.024      4.416      0.000
000224 
000225  Intercepts
000226     Y1                 0.000      0.000    999.000    999.000
000227     Y2                 0.000      0.000    999.000    999.000
000228     Y3                 0.000      0.000    999.000    999.000
000229     Y4                 0.000      0.000    999.000    999.000
000230 
000231  Variances
000232     IY                10.790      0.756     14.282      0.000
000233     SY                 0.117      0.055      2.118      0.034
000234 
000235  Residual Variances
000236     Y1                 8.406      0.694     12.121      0.000
000237     Y2                10.422      0.561     18.586      0.000
000238     Y3                10.981      0.769     14.273      0.000
000239     Y4                10.222      1.165      8.777      0.000
000240 
000241 
000242 QUALITY OF NUMERICAL RESULTS
000243 
000244      Condition Number for the Information Matrix              0.240E-02
000245        (ratio of smallest to largest eigenvalue)
000246 
000247 
```
