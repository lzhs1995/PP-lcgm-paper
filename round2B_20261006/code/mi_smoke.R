# 两层PMM的实际合成集成测试；不替代真实数据诊断。
mi_smoke<-function(root){
 set.seed(1407);hh<-rep(1:120,each=3);u<-rnorm(120);n<-length(hh)
 d<-data.frame(cluster=hh,x=rnorm(n),income=rep(exp(.3+u),each=3))
 d$personal<-.4*d$x+u[hh]+rnorm(n)
 d$income[hh%in%1:8]<-NA;d$personal[seq(2,n,by=7)]<-NA
 meth<-c(cluster='',x='',income='2lonly.pmm',personal='2l.pmm')
 pm<-matrix(0,4,4,dimnames=list(names(d),names(d)));pm['income',c('x','personal')]<-1;pm['personal',c('x','income')]<-1;pm[c('income','personal'),'cluster']<--2
 imp<-mice::mice(d,m=2,maxit=2,method=meth,predictorMatrix=pm,seed=91407,printFlag=FALSE)
 rows<-list()
 for(k in 1:2){a<-mice::complete(imp,k);rows[[k]]<-data.frame(imputation=k,complete=all(is.finite(as.matrix(a))),observed_unchanged=all(as.matrix(a)[!is.na(d)]==as.matrix(d)[!is.na(d)]),family_constant=all(vapply(split(a$income,a$cluster),function(x)length(unique(x))==1L,logical(1))))}
 out<-do.call(rbind,rows);write.csv(out,file.path(root,'audit/mi_synthetic_integration.csv'),row.names=FALSE)
 stopifnot(all(out$complete),all(out$observed_unchanged),all(out$family_constant));invisible(TRUE)
}
