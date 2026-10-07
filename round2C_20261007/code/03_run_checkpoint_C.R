# 顺序执行预定34次及最多3次起点核查；恢复只读既有回执，不重复估计。
source('C:/Users/LZHS/pp_lgcm_review/round2C_20261007/code/01_model_engine.R',local=TRUE)
local({
 stopifnot(fromJSON(file.path(R2C,'evidence/preflight_tests.json'))$status=='PASS')
 stopifnot(fromJSON(file.path(R2C,'runtime/resource_admission.json'))$decision=='ADMIT_ONE_SERIAL_WORKER')
 receipts<-list();repair_count<-0L
 if(file.exists(file.path(R2C,'audit/repair_count.json')))repair_count<-fromJSON(file.path(R2C,'audit/repair_count.json'))$used
 save_all<-function(){write_json(receipts,file.path(R2C,'audit/current_receipts.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null')}
 perform<-function(spec,k,tau=NA_real_){
  row<-prepare3(spec,k,tau);r<-run3(row)
  if(r$status=='INPUT_REJECTED')stop('Input rejected: stop and repair generator before any resubmission')
  if(r$status=='ESTIMATION_FAILED'&&repair_count<3L){
   # 只针对实际达到迭代限制的失败；其他失败不得自动重跑。
   txt<-paste(readLines(file.path(dirname(row$input),'model.out'),warn=FALSE),collapse=' ')
   if(grepl('ITERATIONS EXCEEDED|ITERATION LIMIT|NO CONVERGENCE',txt)){
    repair_count<<-repair_count+1L
    write_json(list(used=repair_count),file.path(R2C,'audit/repair_count.json'),auto_unbox=TRUE)
    rr<-prepare3(spec,k,tau,attempt='numeric_retry01',iterations=5000);r<-run3(rr)
   }
  }
  receipts[[r$id]]<<-r;save_all();r
 }
 # 三类规格完整运行全部成员，不由MI01的显著性选择结构。
 for(spec in c('C1','SW','XLIN'))for(k in 1:10)perform(spec,k,if(spec=='C1')0 else NA_real_)
 for(tau in c(.02,.08,.20,.40))perform(sprintf('P%03d',round(tau*100)),1,tau)
 checks<-list()
 for(spec in c('C1','SW','XLIN')){
  r<-receipts[[paste0(spec,'_MI01')]]
  if(!isTRUE(r$usable)){checks[[spec]]<-data.frame(spec=spec,executed=FALSE,stable=FALSE,reason='MI01 not admissible',dLL=NA_real_,max_path_difference=NA_real_);next}
  tau<-if(spec=='C1')0 else NA_real_
  s<-run3(prepare3(spec,1,tau,attempt='start_check01',start=TRUE))
  d0<-file.path(R2C,'models',r$id,r$attempt);d1<-file.path(R2C,'models',s$id,s$attempt)
  dl<-dp<-NA_real_
  if(file.exists(file.path(d1,'fit.csv'))&&file.exists(file.path(d1,'parameters_high_precision.csv'))){
   dl<-abs(read.csv(file.path(d1,'fit.csv'))$LL-read.csv(file.path(d0,'fit.csv'))$LL)
   dp<-max(abs(key3(read.csv(file.path(d1,'parameters_high_precision.csv')))$estimate-key3(read.csv(file.path(d0,'parameters_high_precision.csv')))$estimate))
  }
  stable<-isTRUE(s$usable)&&is.finite(dl)&&is.finite(dp)&&dl<=.01&&dp<=.001
  checks[[spec]]<-data.frame(spec=spec,executed=TRUE,stable=stable,reason=if(stable)'No detected start sensitivity'else'Start discrepancy or unusable check',dLL=dl,max_path_difference=dp)
  write.csv(do.call(rbind,checks),file.path(R2C,'audit/start_checks.csv'),row.names=FALSE)
 }
 write.csv(do.call(rbind,checks),file.path(R2C,'audit/start_checks.csv'),row.names=FALSE)
 gates<-lapply(c('C1','SW','XLIN'),function(spec){
  rr<-receipts[paste0(spec,'_MI',sprintf('%02d',1:10))]
  data.frame(spec=spec,members=length(rr),admissible=sum(vapply(rr,function(r)isTRUE(r$usable),logical(1))),
   start_stable=checks[[spec]]$stable,eligible_for_conditional_pooling=all(vapply(rr,function(r)isTRUE(r$usable),logical(1)))&&checks[[spec]]$stable)
 })
 write.csv(do.call(rbind,gates),file.path(R2C,'audit/family_gates.csv'),row.names=FALSE)
 write_json(list(status='MODEL_BATCH_COMPLETE',receipts=length(receipts),calls=nrow(read.csv(file.path(R2C,'audit/CALL_REGISTER.csv'))),repairs=repair_count,moderation_authorized=FALSE),file.path(R2C,'audit/batch_complete.json'),pretty=TRUE,auto_unbox=TRUE)
 progress2('CHECKPOINT_C_MODELS_COMPLETE','All planned families and profile points assessed; pooling is separate')
})
