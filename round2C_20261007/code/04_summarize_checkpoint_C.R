# 检查点C：只读取已完成结果，禁止在本脚本触发任何Mplus估计。
library(jsonlite)
root <- 'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
stopifnot(!isTRUE(getOption('round2B.pool_run',FALSE)))
source(file.path(root,'vendor/08_pool_parent.R'),local=TRUE)
stopifnot(fromJSON(file.path(root,'audit/batch_complete.json'))$status=='MODEL_BATCH_COMPLETE')
gate <- read.csv(file.path(root,'audit/family_gates.csv'))
stopifnot(nrow(gate)==3L,all(gate$members==10L))
dir.create(file.path(root,'results'),showWarnings=FALSE)
calls<-read.csv(file.path(root,'audit/CALL_REGISTER.csv'))
execution<-lapply(seq_len(nrow(calls)),function(i){
 d<-file.path(root,'models',calls$id[i],calls$attempt[i]);r<-fromJSON(file.path(d,'receipt_round2C.json'))
 p<-file.path(d,'parameters_high_precision.csv')
 data.frame(calls[i,],status=r$status,usable=isTRUE(r$usable),normal=isTRUE(r$normal),
  input_sha256=r$input_sha256,output_sha256=r$output_sha256,data_sha256=r$data_sha256,
  parameter_rows=if(file.exists(p))nrow(read.csv(p))else 0L,
  output_path=paste('models',calls$id[i],calls$attempt[i],'model.out.txt',sep='/'))
})
write.csv(do.call(rbind,execution),file.path(root,'audit/MODEL_REGISTER.csv'),row.names=FALSE)
write.csv(test_pool(),file.path(root,'evidence/pooling_tests.csv'),row.names=FALSE)
keys <- data.frame(label=c('bii','bis','bss','bsyiy'),row=c('IY','SY','SY','SY'),column=c('IX','IX','SX','IY'))
select_keys <- function(p){
 out <- keys
 for(i in 1:4){z<-p[p$matrix=='beta'&p$row==keys$row[i]&p$column==keys$column[i],];stopifnot(nrow(z)==1L);out$parameter[i]<-z$parameter;out$estimate[i]<-z$estimate;out$se[i]<-z$se}
 out
}
receipts <- fromJSON(file.path(root,'audit/current_receipts.json'),simplifyVector=FALSE)
get_dir <- function(r)file.path(root,'models',r$id,r$attempt)
members<-list();fits<-list();paths<-list();geometry<-list()
for(r in receipts){
 d<-get_dir(r)
 members[[r$id]]<-data.frame(id=r$id,spec=r$spec,member=r$member,attempt=r$attempt,status=r$status,usable=isTRUE(r$usable),SY_residual=if(is.null(r$SY_residual))NA_real_ else r$SY_residual)
 if(file.exists(file.path(d,'fit.csv'))){
  fit<-read.csv(file.path(d,'fit.csv'));stopifnot(nrow(fit)==1L,fit$Observations==3274L)
  fits[[r$id]]<-cbind(id=r$id,fit)
 }
 if(file.exists(file.path(d,'parameters_high_precision.csv'))){
  k<-select_keys(read.csv(file.path(d,'parameters_high_precision.csv')))
  k$id<-r$id;k$spec<-r$spec;k$member<-r$member;k$usable<-isTRUE(r$usable)
  # 单份区间仅为条件渐近Wald诊断，不是MI区间或边界检验。
  k$lower<-k$estimate-qnorm(.975)*k$se;k$upper<-k$estimate+qnorm(.975)*k$se
  paths[[r$id]]<-k
 }
 if(file.exists(file.path(d,'geometry.json'))){
  g<-fromJSON(file.path(d,'geometry.json'));geometry[[r$id]]<-cbind(id=r$id,as.data.frame(g$diagnostic),passed=g$passed)
 }
}
write.csv(do.call(rbind,members),file.path(root,'results/member_dispositions.csv'),row.names=FALSE)
write.csv(do.call(rbind,fits),file.path(root,'results/model_fit.csv'),row.names=FALSE)
write.csv(do.call(rbind,paths),file.path(root,'results/key_paths_all_members_DIAGNOSTIC.csv'),row.names=FALSE)
write.csv(do.call(rbind,geometry),file.path(root,'results/geometry_all_members.csv'),row.names=FALSE)
pooled<-list()
for(spec in gate$spec[gate$eligible_for_conditional_pooling]){
 rr<-receipts[paste0(spec,'_MI',sprintf('%02d',1:10))]
 stopifnot(length(rr)==10L,all(vapply(rr,function(r)isTRUE(r$usable),logical(1))))
 tabs<-lapply(rr,function(r)read.csv(file.path(get_dir(r),'parameters_high_precision.csv')))
 for(t in tabs)stopifnot(identical(t[c('parameter','matrix','row','column')],tabs[[1]][c('parameter','matrix','row','column')]))
 kt<-lapply(tabs,select_keys);Q<-do.call(rbind,lapply(kt,function(t)t$estimate));colnames(Q)<-keys$label
 U<-lapply(seq_along(rr),function(i){
  u<-as.matrix(read.csv(file.path(get_dir(rr[[i]]),'parameter_covariance.csv'),row.names=1,check.names=FALSE))
  stopifnot(identical(colnames(u),as.character(tabs[[i]]$parameter)))
  stopifnot(max(abs(diag(u)-tabs[[i]]$se^2))<max(1e-5,max(tabs[[i]]$se^2)*1e-4))
  idx<-kt[[i]]$parameter;u[idx,idx,drop=FALSE]
 })
 a<-rubin_matrix(Q,U)
 pooled[[spec]]<-cbind(spec=spec,keys,a$table,MCSE_flag=a$table$MCSE_over_SE>.05)
 write.csv(data.frame(member=1:10,id=names(rr),Q),file.path(root,'results',paste0(spec,'_member_estimates.csv')),row.names=FALSE)
 for(n in c('within','between','total'))write.csv(a[[n]],file.path(root,'results',paste0(spec,'_',n,'_covariance.csv')))
}
if(length(pooled)){
 pp<-do.call(rbind,pooled)
 write.csv(pp,file.path(root,'results/conditional_MI_paths.csv'),row.names=FALSE)
 family_sensitivity<-lapply(keys$label,function(label){
  z<-pp[pp$label==label,]
  data.frame(label=label,families=nrow(z),direction_consistent=if(nrow(z)>1)length(unique(sign(z$estimate)))==1L else NA,
   estimate_min=min(z$estimate),estimate_max=max(z$estimate),absolute_range=diff(range(z$estimate)),
   interval_width_min=min(z$upper-z$lower),interval_width_max=max(z$upper-z$lower),
   interpretation='Descriptive structural sensitivity; XLIN changes the definition of X change; not a pooled or simultaneous confidence interval')
 })
 write.csv(do.call(rbind,family_sensitivity),file.path(root,'results/family_sensitivity.csv'),row.names=FALSE)
}
profile_ids<-c('C1_MI01','P002_MI01','P008_MI01','P020_MI01','P040_MI01')
profile<-do.call(rbind,lapply(seq_along(profile_ids),function(i){
 id<-profile_ids[i];k<-paths[[id]];if(is.null(k))return(NULL)
 k$tau<-c(0,.02,.08,.20,.40)[i];k$LL<-fits[[id]]$LL;k
}))
write.csv(profile,file.path(root,'results/profile_MI01.csv'),row.names=FALSE)
# 方向、点估计幅度和区间宽度分开汇总，不以是否全显著定义稳健。
sensitivity<-lapply(keys$label,function(label){
 p<-profile[profile$label==label & profile$usable,]
 data.frame(label=label,legal_profile_points=nrow(p),direction_consistent=if(nrow(p))length(unique(sign(p$estimate)))==1L else NA,
 estimate_min=if(nrow(p))min(p$estimate)else NA,estimate_max=if(nrow(p))max(p$estimate)else NA,
 interval_width_min=if(nrow(p))min(p$upper-p$lower)else NA,interval_width_max=if(nrow(p))max(p$upper-p$lower)else NA)
})
write.csv(do.call(rbind,sensitivity),file.path(root,'results/profile_sensitivity.csv'),row.names=FALSE)
write_json(list(status='CHECKPOINT_C_SUMMARIZED',eligible_families=gate$spec[gate$eligible_for_conditional_pooling],m=10,
 inference='Fixed specification conditional Rubin inference, large complete-sample df approximation; no model selection uncertainty or boundary variance test',
 profile='MI01 only; fixed variance grid, not confidence region; no LRT selection',
 mcse='sqrt(B/m) divided by pooled SE; .05 flag only; no automatic additional MI',
 moderation_authorized=FALSE,stop_at='Checkpoint C'),file.path(root,'results/SUMMARY_CONTRACT.json'),pretty=TRUE,auto_unbox=TRUE)
message('Checkpoint C summary saved; no models estimated by this script.')
