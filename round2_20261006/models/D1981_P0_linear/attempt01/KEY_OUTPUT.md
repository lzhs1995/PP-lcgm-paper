# D1981_P0_linear / attempt01

状态：**REVIEWABLE**。数值仅在合法模型和对应研究范围内解释。

[完整输出](model.out.txt) · [输入](model.inp.txt)

```text
000029 INPUT READING TERMINATED NORMALLY
000213 THE MODEL ESTIMATION TERMINATED NORMALLY
000217 MODEL FIT INFORMATION
000218 
000219 Number of Free Parameters                       26
000220 
000221 Loglikelihood
000222 
000223           H0 Value                      -19838.105
000224           H0 Scaling Correction Factor      1.3484
000225             for MLR
000226           H1 Value                      -19781.775
000227           H1 Scaling Correction Factor      1.2631
000228             for MLR
000229 
000230 Information Criteria
000231 
000232           Akaike (AIC)                   39728.210
000233           Bayesian (BIC)                 39873.586
000234           Sample-Size Adjusted BIC       39790.982
000235             (n* = (n + 2) / 24)
000236 
000237 Chi-Square Test of Model Fit
000238 
000239           Value                             93.400*
000240           Degrees of Freedom                    39
000241           P-Value                           0.0000
000242           Scaling Correction Factor         1.2062
000243             for MLR
000244 
000245 *   The chi-square value for MLM, MLMV, MLR, ULSMV, WLSM and WLSMV cannot be used
000246     for chi-square difference testing in the regular way.  MLM, MLR and WLSM
000247     chi-square difference testing is described on the Mplus website.  MLMV, WLSMV,
000248     and ULSMV difference testing is done using the DIFFTEST option.
000249 
000250 RMSEA (Root Mean Square Error Of Approximation)
000251 
000252           Estimate                           0.027
000253           90 Percent C.I.                    0.020  0.033
000254           Probability RMSEA <= .05           1.000
000255 
000256 CFI/TLI
000257 
000258           CFI                                0.977
000259           TLI                                0.973
000260 
000261 Chi-Square Test of Model Fit for the Baseline Model
000262 
000263           Value                           2407.491
000264           Degrees of Freedom                    45
000265           P-Value                           0.0000
000266 
000267 SRMR (Standardized Root Mean Square Residual)
000268 
000269           Value                              0.030
000270 
000271 
000272 
000273 MODEL RESULTS
000274 
000275                                                     Two-Tailed
000276                     Estimate       S.E.  Est./S.E.    P-Value
000277 
000278  IX       |
000279     X1                 1.000      0.000    999.000    999.000
000280     X2                 1.000      0.000    999.000    999.000
000281     X3                 1.000      0.000    999.000    999.000
000282     X4                 1.000      0.000    999.000    999.000
000283     X5                 1.000      0.000    999.000    999.000
000284 
000285  SX       |
000286     X1                 0.000      0.000    999.000    999.000
000287     X2                 7.228      1.129      6.400      0.000
000288     X3                 6.994      1.152      6.073      0.000
000289     X4                11.123      1.374      8.098      0.000
000290     X5                10.000      0.000    999.000    999.000
000291 
000292  IY       |
000293     Y1                 1.000      0.000    999.000    999.000
000294     Y2                 1.000      0.000    999.000    999.000
000295     Y3                 1.000      0.000    999.000    999.000
000296     Y4                 1.000      0.000    999.000    999.000
000297     Y5                 1.000      0.000    999.000    999.000
000298 
000299  SY       |
000300     Y1                 0.000      0.000    999.000    999.000
000301     Y2                 4.000      0.000    999.000    999.000
000302     Y3                 6.000      0.000    999.000    999.000
000303     Y4                 8.000      0.000    999.000    999.000
000304     Y5                10.000      0.000    999.000    999.000
000305 
000306  IY       ON
000307     IX                -0.601      0.068     -8.897      0.000
000308 
000309  SY       ON
000310     IX                 0.012      0.016      0.714      0.475
000311     SX                -0.711      0.290     -2.455      0.014
000312     IY                 0.011      0.018      0.637      0.524
000313 
000314  SX       WITH
000315     IX                -0.004      0.004     -0.864      0.387
000316 
000317  Means
000318     IX                 0.037      0.027      1.379      0.168
000319     SX                 0.026      0.003      7.647      0.000
000320 
000321  Intercepts
000322     Y1                 0.000      0.000    999.000    999.000
000323     Y2                 0.000      0.000    999.000    999.000
000324     Y3                 0.000      0.000    999.000    999.000
000325     Y4                 0.000      0.000    999.000    999.000
000326     Y5                 0.000      0.000    999.000    999.000
000327     X1                 0.000      0.000    999.000    999.000
000328     X2                 0.000      0.000    999.000    999.000
000329     X3                 0.000      0.000    999.000    999.000
000330     X4                 0.000      0.000    999.000    999.000
000331     X5                 0.000      0.000    999.000    999.000
000332     IY                -0.070      0.025     -2.776      0.006
000333     SY                 0.032      0.009      3.520      0.000
000334 
000335  Variances
000336     IX                 0.298      0.044      6.709      0.000
000337     SX                 0.001      0.001      2.078      0.038
000338 
000339  Residual Variances
000340     Y1                 0.526      0.040     13.089      0.000
000341     Y2                 0.556      0.028     19.922      0.000
000342     Y3                 0.553      0.030     18.333      0.000
000343     Y4                 0.564      0.041     13.608      0.000
000344     Y5                 0.624      0.064      9.707      0.000
000345     X1                 0.679      0.048     14.125      0.000
000346     X2                 0.670      0.027     24.879      0.000
000347     X3                 0.530      0.024     21.996      0.000
000348     X4                 0.547      0.052     10.510      0.000
000349     X5                 0.495      0.039     12.789      0.000
000350     IY                 0.349      0.042      8.364      0.000
000351     SY                 0.001      0.001      0.482      0.630
000352 
000353 
000354 QUALITY OF NUMERICAL RESULTS
000355 
000356      Condition Number for the Information Matrix              0.186E-06
000357        (ratio of smallest to largest eigenvalue)
000358 
000359 
```
