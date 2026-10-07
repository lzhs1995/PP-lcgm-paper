# 利用TECH1参数编号绑定高精度RESULTS及TECH3，不将TECH4当作参数协方差。
collect2 <- function(dest){
 p<-readRDS(file.path(dest,'readback.rds'));n<-p$summaries$Parameters
 if(length(n)!=1L||!file.exists(file.path(dest,'estimates.dat')))return(NULL)
 vals<-scan(file.path(dest,'estimates.dat'),quiet=TRUE);stopifnot(length(vals)>=2*n+1,vals[2*n+1]==n)
 q<-vals[seq_len(n)];se<-vals[n+seq_len(n)]
 stopifnot(all(is.finite(q)),all(is.finite(se)),all(se>0))
 U<-p$tech3$paramCov.savedata;if(is.null(U))U<-p$tech3$paramCov
 stopifnot(is.matrix(U),all(dim(U)==n),all(is.finite(U)),max(abs(U-t(U)))<1e-6)
 # Mplus保存格式的有限精度容许误差；绝不将矩阵投影成正定来改变推断。
 discrepancy<-max(abs(diag(U)-se^2));stopifnot(discrepancy<max(1e-5,max(se^2)*1e-4))
 stopifnot(all(diag(U)>0))
 # 尺度标准化后检验协方差；不把明显不定矩阵用于Rubin合并。
 corr<-U/outer(sqrt(diag(U)),sqrt(diag(U)))
 ev<-eigen((corr+t(corr))/2,symmetric=TRUE,only.values=TRUE)$values
 covariance_review<-list(min_eigenvalue=min(ev),max_eigenvalue=max(ev),
   negative_tolerance=1e-7,positive_definite=min(ev)>0,
   materially_indefinite=min(ev)< -1e-7,
   note='Tolerance only screens saved numeric precision; no projection or eigenvalue replacement.')
 write_json(covariance_review,file.path(dest,'parameter_covariance_diagnostics.json'),pretty=TRUE,auto_unbox=TRUE)
 stopifnot(!covariance_review$materially_indefinite)
 specs<-p$tech1$parameterSpecification;rows<-list()
 for(m in names(specs)){
  z<-specs[[m]];ix<-which(is.finite(z)&z>0,arr.ind=TRUE)
  if(nrow(ix))rows[[m]]<-data.frame(parameter=as.integer(z[ix]),matrix=m,row=rownames(z)[ix[,1]],column=colnames(z)[ix[,2]])
 }
 map<-do.call(rbind,rows);map<-map[!duplicated(map$parameter),];map<-map[order(map$parameter),];stopifnot(identical(map$parameter,seq_len(n)))
 map$estimate<-q;map$se<-se;map$z<-ifelse(se>0,q/se,NA_real_);map$p_normal<-2*pnorm(-abs(map$z))
 write.csv(map,file.path(dest,'parameters_high_precision.csv'),row.names=FALSE)
 write.csv(U,file.path(dest,'parameter_covariance.csv'),row.names=TRUE)
 write_json(list(parameters=n,vcov_diagonal_max_difference=discrepancy,results_sha256=digest(file=file.path(dest,'estimates.dat'),algo='sha256'),tech3_sha256=digest(file=file.path(dest,'tech3.dat'),algo='sha256'),bound_to_TECH1=TRUE),file.path(dest,'parameter_binding.json'),pretty=TRUE,auto_unbox=TRUE)
 list(q=q,U=U,map=map)
}
