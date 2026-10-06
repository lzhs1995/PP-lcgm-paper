# D1981_P0_free / attempt01

状态：**REVIEWABLE**。数值仅在合法模型和对应研究范围内解释。

[完整输出](model.out.txt) · [输入](model.inp.txt)

```text
000029 INPUT READING TERMINATED NORMALLY
000213 THE MODEL ESTIMATION TERMINATED NORMALLY
000217 MODEL FIT INFORMATION
000218 
000219 Number of Free Parameters                       29
000220 
000221 Loglikelihood
000222 
000223           H0 Value                      -19834.858
000224           H0 Scaling Correction Factor      1.7412
000225             for MLR
000226           H1 Value                      -19781.775
000227           H1 Scaling Correction Factor      1.2631
000228             for MLR
000229 
000230 Information Criteria
000231 
000232           Akaike (AIC)                   39727.716
000233           Bayesian (BIC)                 39889.866
000234           Sample-Size Adjusted BIC       39797.731
000235             (n* = (n + 2) / 24)
000236 
000237 Chi-Square Test of Model Fit
000238 
000239           Value                            120.929*
000240           Degrees of Freedom                    36
000241           P-Value                           0.0000
000242           Scaling Correction Factor         0.8779
000243             for MLR
000244 
000245 *   The chi-square value for MLM, MLMV, MLR, ULSMV, WLSM and WLSMV cannot be used
000246     for chi-square difference testing in the regular way.  MLM, MLR and WLSM
000247     chi-square difference testing is described on the Mplus website.  MLMV, WLSMV,
000248     and ULSMV difference testing is done using the DIFFTEST option.
000249 
000250 RMSEA (Root Mean Square Error Of Approximation)
000251 
000252           Estimate                           0.035
000253           90 Percent C.I.                    0.028  0.041
000254           Probability RMSEA <= .05           1.000
000255 
000256 CFI/TLI
000257 
000258           CFI                                0.964
000259           TLI                                0.955
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
000287     X2                 7.234      1.153      6.274      0.000
000288     X3                 6.953      1.210      5.744      0.000
000289     X4                10.926      1.387      7.879      0.000
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
000301     Y2                 2.114      2.696      0.784      0.433
000302     Y3                 5.540      8.009      0.692      0.489
000303     Y4                 4.481      1.743      2.571      0.010
000304     Y5                10.000      0.000    999.000    999.000
000305 
000306  IY       ON
000307     IX                -0.609      0.076     -8.035      0.000
000308 
000309  SY       ON
000310     IX                 0.020      0.020      1.039      0.299
000311     SX                -0.812      0.974     -0.833      0.405
000312     IY                 0.022      0.055      0.402      0.687
000313 
000314  SX       WITH
000315     IX                -0.003      0.006     -0.431      0.667
000316 
000317  Means
000318     IX                 0.036      0.027      1.353      0.176
000319     SX                 0.026      0.003      7.773      0.000
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
000332     IY                -0.070      0.026     -2.712      0.007
000333     SY                 0.039      0.029      1.369      0.171
000334 
000335  Variances
000336     IX                 0.288      0.053      5.444      0.000
000337     SX                 0.001      0.001      1.276      0.202
000338 
000339  Residual Variances
000340     Y1                 0.543      0.117      4.629      0.000
000341     Y2                 0.559      0.031     17.828      0.000
000342     Y3                 0.542      0.055      9.834      0.000
000343     Y4                 0.583      0.041     14.076      0.000
000344     Y5                 0.604      0.361      1.671      0.095
000345     X1                 0.689      0.057     12.114      0.000
000346     X2                 0.670      0.027     24.839      0.000
000347     X3                 0.530      0.024     21.776      0.000
000348     X4                 0.553      0.053     10.411      0.000
000349     X5                 0.496      0.039     12.738      0.000
000350     IY                 0.340      0.100      3.410      0.001
000351     SY                 0.000      0.006      0.033      0.974
000352 
000353 
000354 QUALITY OF NUMERICAL RESULTS
000355 
000356      Condition Number for the Information Matrix              0.169E-07
000357        (ratio of smallest to largest eigenvalue)
000358 
000359 
```
