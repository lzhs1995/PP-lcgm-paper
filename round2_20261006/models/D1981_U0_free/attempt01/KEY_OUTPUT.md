# D1981_U0_free / attempt01

状态：**INADMISSIBLE**。数值仅在合法模型和对应研究范围内解释。

[完整输出](model.out.txt) · [输入](model.inp.txt)

```text
000024 INPUT READING TERMINATED NORMALLY
000146 THE MODEL ESTIMATION TERMINATED NORMALLY
000148      WARNING:  THE LATENT VARIABLE COVARIANCE MATRIX (PSI) IS NOT POSITIVE
000149      DEFINITE.  THIS COULD INDICATE A NEGATIVE VARIANCE/RESIDUAL VARIANCE
000155      THE WARNING IS DUE TO A NEGATIVE VARIANCE/RESIDUAL VARIANCE.
000160 MODEL FIT INFORMATION
000161 
000162 Number of Free Parameters                       13
000163 
000164 Loglikelihood
000165 
000166           H0 Value                      -10078.428
000167           H0 Scaling Correction Factor      1.7735
000168             for MLR
000169           H1 Value                      -10064.479
000170           H1 Scaling Correction Factor      1.3783
000171             for MLR
000172 
000173 Information Criteria
000174 
000175           Akaike (AIC)                   20182.856
000176           Bayesian (BIC)                 20255.544
000177           Sample-Size Adjusted BIC       20214.242
000178             (n* = (n + 2) / 24)
000179 
000180 Chi-Square Test of Model Fit
000181 
000182           Value                             43.305*
000183           Degrees of Freedom                     7
000184           P-Value                           0.0000
000185           Scaling Correction Factor         0.6442
000186             for MLR
000187 
000188 *   The chi-square value for MLM, MLMV, MLR, ULSMV, WLSM and WLSMV cannot be used
000189     for chi-square difference testing in the regular way.  MLM, MLR and WLSM
000190     chi-square difference testing is described on the Mplus website.  MLMV, WLSMV,
000191     and ULSMV difference testing is done using the DIFFTEST option.
000192 
000193 RMSEA (Root Mean Square Error Of Approximation)
000194 
000195           Estimate                           0.051
000196           90 Percent C.I.                    0.037  0.066
000197           Probability RMSEA <= .05           0.417
000198 
000199 CFI/TLI
000200 
000201           CFI                                0.971
000202           TLI                                0.958
000203 
000204 Chi-Square Test of Model Fit for the Baseline Model
000205 
000206           Value                           1256.634
000207           Degrees of Freedom                    10
000208           P-Value                           0.0000
000209 
000210 SRMR (Standardized Root Mean Square Residual)
000211 
000212           Value                              0.030
000213 
000214 
000215 
000216 MODEL RESULTS
000217 
000218                                                     Two-Tailed
000219                     Estimate       S.E.  Est./S.E.    P-Value
000220 
000221  IY       |
000222     Y1                 1.000      0.000    999.000    999.000
000223     Y2                 1.000      0.000    999.000    999.000
000224     Y3                 1.000      0.000    999.000    999.000
000225     Y4                 1.000      0.000    999.000    999.000
000226     Y5                 1.000      0.000    999.000    999.000
000227 
000228  SY       |
000229     Y1                 0.000      0.000    999.000    999.000
000230     Y2                 1.150      4.005      0.287      0.774
000231     Y3                 8.072      4.094      1.972      0.049
000232     Y4                 4.648      2.572      1.807      0.071
000233     Y5                10.000      0.000    999.000    999.000
000234 
000235  SY       WITH
000236     IY                 0.008      0.003      2.423      0.015
000237 
000238  Means
000239     IY                -0.087      0.030     -2.925      0.003
000240     SY                 0.013      0.007      1.950      0.051
000241 
000242  Intercepts
000243     Y1                 0.000      0.000    999.000    999.000
000244     Y2                 0.000      0.000    999.000    999.000
000245     Y3                 0.000      0.000    999.000    999.000
000246     Y4                 0.000      0.000    999.000    999.000
000247     Y5                 0.000      0.000    999.000    999.000
000248 
000249  Variances
000250     IY                 0.432      0.050      8.577      0.000
000251     SY                 0.000      0.001     -0.053      0.958
000252 
000253  Residual Variances
000254     Y1                 0.565      0.036     15.922      0.000
000255     Y2                 0.561      0.031     17.861      0.000
000256     Y3                 0.538      0.050     10.833      0.000
000257     Y4                 0.590      0.041     14.492      0.000
000258     Y5                 0.663      0.085      7.844      0.000
000259 
000260 
000261 QUALITY OF NUMERICAL RESULTS
000262 
000263      Condition Number for the Information Matrix              0.210E-07
000264        (ratio of smallest to largest eigenvalue)
000265 
000266 
```
