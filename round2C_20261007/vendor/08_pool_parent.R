# Rubin矩阵合并：只接受全部预定成员、同一参数顺序和完整TECH3。
rubin_matrix <- function(Q,U) {
  m<-nrow(Q); stopifnot(m>=2,length(U)==m,all(is.finite(Q)))
  p<-ncol(Q);stopifnot(all(vapply(U,function(u)all(dim(u)==c(p,p))&&all(is.finite(u))&&max(abs(u-t(u)))<1e-6&&all(diag(u)>0),logical(1))))
  stopifnot(all(vapply(U,function(u){c<-u/outer(sqrt(diag(u)),sqrt(diag(u)));min(eigen((c+t(c))/2,symmetric=TRUE,only.values=TRUE)$values)>= -1e-7},logical(1))))
  W<-Reduce('+',U)/m; B<-stats::cov(Q); T<-W+(1+1/m)*B
  r<-(1+1/m)*diag(B)/diag(W); df<-ifelse(r>0,(m-1)*(1+1/r)^2,Inf)
  est<-colMeans(Q);se<-sqrt(diag(T));crit<-stats::qt(.975,df)
  list(table=data.frame(estimate=est,se=se,df=df,lower=est-crit*se,upper=est+crit*se,p=2*stats::pt(-abs(est/se),df),relative_increase=r,lambda=(1+1/m)*diag(B)/diag(T),FMI=(r+2/(df+3))/(r+1),MCSE_mean=sqrt(diag(B)/m),MCSE_over_SE=sqrt(diag(B)/m)/se),within=W,between=B,total=T)
}
test_pool <- function() {
 q<-rbind(c(1,2),c(3,4));u<-diag(c(4,9));a<-rubin_matrix(q,list(u,u))
 stopifnot(max(abs(a$table$estimate-c(2,3)))<1e-12,max(abs(a$total-matrix(c(7,3,3,12),2)))<1e-12)
 q2<-rbind(c(1,2),c(1,2));a2<-rubin_matrix(q2,list(u,u));stopifnot(all(is.infinite(a2$table$df)),all(a2$table$MCSE_mean==0))
 bad<-matrix(c(1,2,2,1),2);rejected<-inherits(try(rubin_matrix(q,list(bad,bad)),silent=TRUE),'try-error');stopifnot(rejected)
 data.frame(test=c('correlated_between_variance','zero_between_limit','indefinite_covariance_rejected'),passed=TRUE)
}
if(isTRUE(getOption('round2B.pool_run',FALSE)))local({
 library(jsonlite);root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 gate<-fromJSON(file.path(root,'audit/target_parent_gate.json'));stopifnot(isTRUE(gate$all_members_admissible),gate$total==10,gate$passed==10)
 write.csv(test_pool(),file.path(root,'audit/pooling_synthetic_tests.csv'),row.names=FALSE)
 tabs<-lapply(1:10,function(k)read.csv(file.path(root,'models',sprintf('PARENT_MI%02d',k),'attempt01/parameters_high_precision.csv'),check.names=FALSE))
 ids<-c('parameter','matrix','row','column');for(tab in tabs)stopifnot(identical(tab[ids],tabs[[1]][ids]))
 U<-lapply(1:10,function(k)as.matrix(read.csv(file.path(root,'models',sprintf('PARENT_MI%02d',k),'attempt01/parameter_covariance.csv'),row.names=1,check.names=FALSE)))
 for(k in 1:10){stopifnot(identical(colnames(U[[k]]),as.character(tabs[[k]]$parameter)));stopifnot(max(abs(diag(U[[k]])-tabs[[k]]$se^2))<max(1e-5,max(tabs[[k]]$se^2)*1e-4))}
 Q<-do.call(rbind,lapply(tabs,function(t)t$estimate));a<-rubin_matrix(Q,U)
 write.csv(cbind(tabs[[1]][ids],a$table),file.path(root,'audit/parent_MI_pooled_parameters.csv'),row.names=FALSE)
 for(n in c('within','between','total'))write.csv(a[[n]],file.path(root,'audit',paste0('parent_MI_',n,'_covariance.csv')))
 write_json(list(m=10,df='Rubin large-complete-sample approximation; not Barnard-Rubin finite cluster df',method='parameter and TECH3 pooling; no p averaging',MCSE='sqrt(B/m), conditional on valid stable chains; inspect key-path ratios before formal adoption',status='POOLED_REQUIRES_PRECISION_AND_SCIENTIFIC_REVIEW'),file.path(root,'audit/parent_MI_pooling_contract.json'),pretty=TRUE,auto_unbox=TRUE)
})
