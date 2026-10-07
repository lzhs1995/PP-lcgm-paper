# 仅对同3274人、同家庭聚类、同测量输入的嵌套形状模型作校正比较。
local({
 r<-'C:/Users/LZHS/pp_lgcm_review/round2_20261006/models'
 a<-read.csv(file.path(r,'D3274_U0_linear/attempt01/fit.csv'));b<-read.csv(file.path(r,'D3274_U0_free/attempt01/fit.csv'))
 df<-b$Parameters-a$Parameters;cd<-(b$Parameters*b$LLCorrectionFactor-a$Parameters*a$LLCorrectionFactor)/df
 T<-2*(b$LL-a$LL)/cd;stopifnot(df==3,cd>0,T>0,a$Observations==b$Observations)
 v<-data.frame(comparison='clustered_free_vs_linear_CESD8_3274',df=df,cd=cd,statistic=T,p=pchisq(T,df,lower.tail=FALSE),precision='computed from printed LL and MLR correction factors')
 write.csv(v,'C:/Users/LZHS/pp_lgcm_review/round2B_20261006/audit/clustered_shape_comparison.csv',row.names=FALSE)
 print(v)
})
