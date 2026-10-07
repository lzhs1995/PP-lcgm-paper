# 基期调整集：恢复实际2012年缺失，不沿用后期补齐；保留修正测量对象。
local({
 library(jsonlite);library(digest)
 root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 a<-readRDS(file.path(root,'private/source_audit_objects.rds'));d<-a$current;r<-a$baseline_raw
 # 城乡-9是特殊缺失码；不作为真实农村或城市值。
 r$urban12[!r$urban12%in%c(0,1)]<-NA_real_
 original<-d
 # 已观测且与来源一致的值保留现有数值精度；缺失状态以2012年来源为准。
 for(v in names(r)){
   ok<-is.finite(r[[v]])&is.finite(d[[v]])
   stopifnot(all(abs(r[[v]][ok]-d[[v]][ok])<1e-5))
   d[[v]][!is.finite(r[[v]])]<-NA_real_
 }
 derive<-function(d){
   for(v in c('prov12','cdsc12','heal12','eco12','hwc12')){
     levels<-switch(v,prov12=c(2,3),cdsc12=c(1,2),heal12=c(1,3),eco12=c(2,3),hwc12=c(2,3))
     for(k in levels)d[[paste0(v,k)]]<-as.integer(d[[v]]==k)
   }
   d$pinc412<-as.integer(d$pinc212>0);d
 }
 d<-derive(d)
 oldcov<-read.csv('C:/Users/LZHS/pp_lgcm_review/round2_20261006/audit/covariates_26.csv')$variable
 cov<-setdiff(oldcov,c('wave','sat12'))
 hh<-split(seq_len(nrow(d)),d$fid)
 hh_audit<-do.call(rbind,lapply(c('finc12','urban12','prov12'),function(v){
  vals<-lapply(hh,function(i)unique(d[[v]][i][is.finite(d[[v]][i])]))
  conflict<-sum(lengths(vals)>1)
  restored<-0L
  if(conflict==0L)for(i in seq_along(hh))if(length(vals[[i]])==1L){idx<-hh[[i]][is.na(d[[v]][hh[[i]]])];restored<-restored+length(idx);d[[v]][idx]<-vals[[i]]}
  data.frame(variable=v,conflict_households=conflict,known_value_recovered=restored,remaining_missing_people=sum(is.na(d[[v]])),remaining_missing_households=sum(vapply(hh,function(i)all(is.na(d[[v]][i])),logical(1))))
 }))
 stopifnot(all(hh_audit$conflict_households==0));d<-derive(d)
 membership<-readRDS('C:/Users/LZHS/pp_lgcm_review/round2_20261006/private/sample_membership.rds')
 cc<-membership$complete_covariates
 write.csv(hh_audit,file.path(root,'audit/baseline_household_recovery.csv'),row.names=FALSE)
 write.csv(data.frame(variable=names(r),reset_to_baseline_missing=sapply(names(r),function(v)sum(is.finite(original[[v]])&is.na(r[[v]]))),after_recovery_missing=sapply(names(r),function(v)sum(is.na(d[[v]])))),file.path(root,'audit/baseline_missing_restoration.csv'),row.names=FALSE)
 write.csv(data.frame(variable=cov,missing=sapply(d[cov],function(v)sum(is.na(v)))),file.path(root,'audit/main_controls.csv'),row.names=FALSE)
 saveRDS(list(data=d,original=original,covariates=cov,oldcov=oldcov,diagnostic=cc,common=membership$common),file.path(root,'private/baseline_preMI.rds'))
 write_json(list(original_N=nrow(d),main_control_columns=length(cov),main_complete_N=sum(complete.cases(d[cov])),diagnostic_original_N=sum(cc),diagnostic_audited_complete_N=sum(cc&complete.cases(d[cov])),missing_method='hierarchical MI covariates; likelihood for longitudinal missing indicators',sat12='sensitivity_only',wave='not_baseline_control',status='PREPARED_NOT_IMPUTED'),file.path(root,'audit/baseline_contract.json'),pretty=TRUE,auto_unbox=TRUE)
 print(hh_audit);cat('MAIN COMPLETE=',sum(complete.cases(d[cov])),' K2=',sum(cc&complete.cases(d[cov])),'\n')
})
