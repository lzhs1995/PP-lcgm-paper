# 原生 ClaudeR + MplusAutomation；A 20-MI 完整家族先全部可采用才合并，B 只作起点敏感性。
local({
 ROOT<-'C:/Users/LZHS/pp_lgcm_review/charls_latent_h42_gender_edu_full_20261022'; PY<-'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
 say0<-function(s,m){cat(format(Sys.time(),tz='UTC'),s,m,'\n');flush.console();if(exists('clauder_progress',mode='function',inherits=TRUE))clauder_progress(s,m)}
 nonce<-paste(sample(c(letters,0:9),32,replace=TRUE),collapse=''); writeLines(as.character(Sys.getpid()),file.path(ROOT,'runtime/BOOT_PID.txt'))
 say0('BOOTSTRAP_PREFLIGHT','gender education full family')
 bs<-processx::run(PY,c('-X','utf8',file.path(ROOT,'code/bootstrap.py'),as.character(Sys.getpid()),nonce),stdout=file.path(ROOT,'audit/BOOT_STDOUT.log'),stderr=file.path(ROOT,'audit/BOOT_STDERR.log'),timeout=90,error_on_status=FALSE); stopifnot(bs$status==0,file.exists(file.path(ROOT,'audit/PREFLIGHT.json')))
 .libPaths(c('C:/Users/LZHS/pp_lgcm_runs/20260908/library_mplusautomation_20260926',.libPaths())); Sys.setenv(OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1,OMP_NUM_THREADS=4)
 library(jsonlite);library(ps);library(processx);library(MplusAutomation)
 wj<-function(x,p)write_json(x,p,auto_unbox=TRUE,pretty=TRUE,digits=NA,null='null')
 say<-function(s,m){say0(s,m);cat(toJSON(list(at=format(Sys.time(),tz='UTC'),stage=s,message=m),auto_unbox=TRUE),'\n',file=file.path(ROOT,'runtime/PROGRESS.jsonl'),append=TRUE)}
 con<-fromJSON(file.path(ROOT,'contracts/RUN_CONTRACT.json')); owner<-list(pid=Sys.getpid(),created=as.numeric(ps_create_time(ps_handle()))); op<-file.path(ROOT,'runtime/AWAKE_OWNER.json');wj(list(owner=owner),op)
 ar<-file.path(ROOT,'runtime/awake'); awake<-processx::process$new(PY,c('-X','utf8','C:/Users/LZHS/.agents/skills/mplusautomation-guide/scripts/windows_awake_guard.py','--owner-file',op,'--output',ar,'--interval','2'),stdout=paste0(ar,'_stdout.log'),stderr=paste0(ar,'_stderr.log'),supervise=FALSE)
 release<-function(){if(dir.exists(ar))writeLines('family terminal',file.path(ar,'stop.request'));try(awake$wait(timeout=6000),silent=TRUE);wj(list(alive=awake$is_alive(),completion=if(file.exists(file.path(ar,'completion.json')))fromJSON(file.path(ar,'completion.json'))else NULL),file.path(ROOT,'audit/AWAKE_RELEASE.json'))}
 wj(list(owner=owner,R=R.version.string,MplusAutomation=as.character(packageVersion('MplusAutomation')),library=find.package('MplusAutomation')),file.path(ROOT,'audit/RUNTIME.json'))
 py<-function(script,args,label){ans<-processx::run(PY,c('-X','utf8',file.path(ROOT,'code',script),args),timeout=600,error_on_status=FALSE);wj(list(status=ans$status,stdout=ans$stdout,stderr=ans$stderr),file.path(ROOT,'audit',paste0(label,'.json')));if(ans$status!=0)stop(paste('Helper failed',label,ans$stderr))}
 key<-function(p)vapply(seq_len(nrow(p)),function(i){a<-toupper(p$row[i]);b<-toupper(p$column[i]);mat<-tolower(p$matrix[i]);if(mat%in%c('psi','theta')){s<-sort(c(a,b));a<-s[1];b<-s[2]};paste(mat,a,b,sep=':')},'')
 pool<-function(){
  source(file.path(ROOT,'code/mi_pool_math.R'),local=TRUE); ids<-con$primary_sequence;stopifnot(length(ids)==20)
  first<-read.csv(file.path(ROOT,'models',ids[1],'parameters_high_precision.csv'));keys<-key(first);stopifnot(length(keys)==134,!anyDuplicated(keys));Q<-matrix(NA_real_,20,134);U<-list();trace<-list()
  for(k in seq_along(ids)){d<-file.path(ROOT,'models',ids[k]);j<-fromJSON(file.path(d,'job.json'));a<-fromJSON(file.path(d,'receipt.json'));stopifnot(a$status=='USABLE',j$member==k,j$start=='A');p<-read.csv(file.path(d,'parameters_high_precision.csv'));order<-match(keys,key(p));stopifnot(!anyNA(order));Q[k,]<-p$estimate[order];U[[k]]<-as.matrix(read.csv(file.path(d,'parameter_covariance.csv'),header=FALSE))[order,order];trace[[k]]<-data.frame(member=k,id=ids[k],data_sha256=j$hashes[['data.dat']],output_sha256=a$output_sha256)}
  p<-rubin_pool(Q,U);s<-rubin_pool(Q,U,437);write.csv(cbind(first[,c('parameter','matrix','row','column')],key=keys,p$table),file.path(ROOT,'results/POOLED_ALL.csv'),row.names=FALSE);write.csv(cbind(first[,c('parameter','matrix','row','column')],key=keys,s$table),file.path(ROOT,'results/POOLED_CLUSTER_DF.csv'),row.names=FALSE)
  for(n in c('W','B','T'))write.table(p[[n]],file.path(ROOT,'results',paste0('POOLED_',n,'.csv')),sep=',',row.names=FALSE,col.names=FALSE)
  rows<-list();for(path in c('IY:IX','SY:IX','SY:SX','IY:IZ','SY:IZ','SY:SZ','SY:SXIZ')){base<-match(paste0('beta:',path),keys);diff<-match(paste0('beta:',path,'G'),keys);stopifnot(!is.na(base),!is.na(diff));for(g in c('group0','group1','difference')){a<-numeric(134);if(g!='difference')a[base]<-1;if(g!='group0')a[diff]<-1;po<-pool_contrast(Q,U,a);se<-pool_contrast(Q,U,a,437);rows[[paste(path,g)]]<-data.frame(path=path,contrast=g,po,cluster_df=se$df,cluster_lower=se$lower,cluster_upper=se$upper,cluster_p=se$p)}}
  tab<-do.call(rbind,rows);write.csv(tab,file.path(ROOT,'results/POOLED_RESEARCH_CONTRASTS.csv'),row.names=FALSE);primary<-tab[tab$path=='SY:SXIZ'&tab$contrast=='difference',];primary$bonferroni_p_planned12<-pmin(1,12*primary$p);write.csv(primary,file.path(ROOT,'results/PRIMARY_H42.csv'),row.names=FALSE);write.csv(do.call(rbind,trace),file.path(ROOT,'results/MEMBER_SOURCES.csv'),row.names=FALSE);wj(list(status='COMPLETE_20_MI_WORKING_H42_GENDER_EDU_A',m=20,N=2085,communities=432,parameters=134,full_covariance=TRUE,primary='SY:SXIZ group1 minus group0',planned_tests=12,conditional_working_MI=TRUE,exact_congeniality_proven=FALSE,original_CFPS_four_complete=FALSE,full_H4_complete=FALSE),file.path(ROOT,'results/FAMILY_RECEIPT.json'))
 }
 run_one<-function(id){
  d<-file.path(ROOT,'models',id)
  if(file.exists(file.path(d,'engine_receipt.json'))){
   stopifnot(file.exists(file.path(d,'job.json')))
   if(file.exists(file.path(d,'receipt.json'))){old<-fromJSON(file.path(d,'receipt.json'));if(isTRUE(old$status=='USABLE')){say('REUSE',id);return(old)}}
   say('READBACK_REUSE',id);py('normalize.py',c('normalize',id),paste0(id,'_READBACK_REUSE'));return(fromJSON(file.path(d,'receipt.json')))
  }
  say('COMPILE',id);py('models.py',c('compile',id),paste0(id,'_COMPILE'))
  writeLines(c('@echo off',paste0('"',PY,'" -X utf8 "',ROOT,'/code/adapter.py" "%~dp0job.json" "%~1"'),'exit /b %ERRORLEVEL%'),file.path(d,'launch.cmd'))
  say('RUNMODELS',id);warnings<-character();err<-NULL
  withCallingHandlers(tryCatch(MplusAutomation::runModels(target=file.path(d,'model.inp'),recursive=FALSE,showOutput=TRUE,replaceOutfile='never',Mplus_command=file.path(d,'launch.cmd'),killOnFail=FALSE,logFile=file.path(d,'MplusAutomation.log')),error=function(e)err<<-conditionMessage(e)),warning=function(w){warnings<<-c(warnings,conditionMessage(w));invokeRestart('muffleWarning')})
  wj(list(error=err,warnings=warnings),file.path(d,'R_WRAPPER_RETURN.json'));stopifnot(file.exists(file.path(d,'engine_receipt.json')))
  say('READBACK',id);py('normalize.py',c('normalize',id),paste0(id,'_READBACK'));fromJSON(file.path(d,'receipt.json'))
 }
 calls<-list();stop_reason<-NULL; B_status<-NULL
 tryCatch({
  for(id in con$primary_sequence){r<-run_one(id);calls[[id]]<-r;wj(calls,file.path(ROOT,'results/CALL_RESULTS.json'));say('MODEL_TERMINAL',paste(id,r$status));if(r$status!='USABLE'){stop_reason<-paste(id,r$status);break}}
  if(is.null(stop_reason)){say('POOL','all 20 A members');pool();
   id<-tail(con$sequence,1);r<-run_one(id);B_status<-r$status;calls[[id]]<-r;wj(calls,file.path(ROOT,'results/CALL_RESULTS.json'));say('SENSITIVITY_TERMINAL',paste(id,r$status));if(r$status!='USABLE')stop_reason<-paste(id,r$status)}
  status<-if(is.null(stop_reason))'COMPLETE_20_MI_WORKING_H42_GENDER_EDU' else if(file.exists(file.path(ROOT,'results/FAMILY_RECEIPT.json')))'COMPLETE_A_B_SENSITIVITY_FAILED' else 'STOPPED_NOT_POOLABLE';wj(list(status=status,stop_reason=stop_reason,attempted=length(calls),A_members=length(Filter(function(x)!is.null(x),calls)),B_status=B_status,terminal=TRUE,full_H4_complete=FALSE,original_CFPS_four_complete=FALSE),file.path(ROOT,'results/TERMINAL.json'));say('FAMILY_TERMINAL',status)
 },error=function(e){wj(list(error=conditionMessage(e),terminal=TRUE),file.path(ROOT,'results/ERROR.json'));stop(e)},finally={release()});cat('H42_GENDER_EDU_FULL_MI_DONE\n');flush.console()
})
