# 逐波与基期聚合描述；不堆叠插补成员、不做原始样本和其副本的独立样本检验。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006';b<-readRDS(file.path(root,'private/baseline_preMI.rds'));d<-b$data
 rows<-list()
 for(year in c(12,16,18,20,22))for(prefix in c('ces8','wfd_m','wfd_s','wfd_d','wfd_d1','wfd_d4')){
  v<-paste0(prefix,year);if(!v%in%names(d))next;x<-d[[v]];obs<-x[is.finite(x)]
  rows[[length(rows)+1L]]<-data.frame(year=2000+year,variable=v,N=length(obs),missing=sum(is.na(x)),mean=mean(obs),sd=sd(obs),median=median(obs),minimum=min(obs),maximum=max(obs))
 }
 write.csv(do.call(rbind,rows),file.path(root,'audit/observed_longitudinal_descriptives.csv'),row.names=FALSE)
 rows<-lapply(c(b$covariates,'sat12','pinc412'),function(v){x<-d[[v]];data.frame(variable=v,N=sum(is.finite(x)),missing=sum(is.na(x)),mean=mean(x,na.rm=TRUE),sd=sd(x,na.rm=TRUE),median=median(x,na.rm=TRUE),minimum=min(x,na.rm=TRUE),maximum=max(x,na.rm=TRUE))})
 write.csv(do.call(rbind,rows),file.path(root,'audit/baseline_descriptives.csv'),row.names=FALSE)
 cat('DESCRIPTIVES_SAVED\n')
})
