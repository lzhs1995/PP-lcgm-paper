# 单槽位执行预登记8模型；只从RStudio原生异步入口调用。
local({
 library(MplusAutomation);library(jsonlite);library(digest)
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'
 batch_dir<-getOption('cfps.review.batch_dir','analysis/sensitivity')
 manifest<-fromJSON(file.path(dest,batch_dir,'manifest.json'),simplifyVector=FALSE)
 check_resource<-function(model_id){
   path<-file.path(dest,'native',paste0('host_profile_',model_id,'.json'))
   python<-'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
   profiler<-'C:/Users/LZHS/.agents/skills/mplusautomation-guide/scripts/windows_host_profile.py'
   rc<-system2(python,c('-X','utf8',shQuote(profiler),'--output',shQuote(path),'--samples','3','--interval','1','--include-processes'),stdout=TRUE,stderr=TRUE)
   writeLines(rc,file.path(dest,'native',paste0('host_profile_',model_id,'_command.log')))
   stopifnot(is.null(attr(rc,'status'))||attr(rc,'status')==0L)
 profile_record<-fromJSON(path,simplifyVector=FALSE)
 profile<-profile_record$profile
 # 新敏感性试跑合同：一个估计进程，先运行5指标模型。已有204MiB基准不外推无限并发。
 metrics<-unlist(profile$system[c('free_phys_gib','free_virtual_gib','disk_free_gib')]);stopifnot(length(metrics)==3L,all(is.finite(metrics)),metrics[1]>=.75,metrics[2]>=1,metrics[3]>=1)
 observed_time<-as.POSIXct(profile_record$generated_at,format='%Y-%m-%dT%H:%M:%S',tz='UTC');stopifnot(!is.na(observed_time),as.numeric(difftime(Sys.time(),observed_time,units='secs'))<300)
 external<-Filter(function(x)grepl('mplus',x$name,ignore.case=TRUE),profile$processes);stopifnot(length(external)==0L)
 write_json(list(model_id=model_id,scope='new_single_slot_sensitivity_pilot_only',available=as.list(metrics),worker_slots=1,assumption='Existing 204MiB model measurement is a reference; no concurrency expansion. Fresh Windows profile and per-model diagnostics required.',source_profile_generated=profile_record$generated_at),file.path(dest,'native',paste0('sensitivity_admission_',model_id,'.json')),auto_unbox=TRUE,pretty=TRUE)
 }
 mplus_command<-unname(Sys.which('Mplus'));stopifnot(nzchar(mplus_command),file.exists(mplus_command))
 receipt<-list();logpath<-file.path(dest,batch_dir,'execution.log')
 log<-file(logpath,'wt',encoding='UTF-8');sink(log,split=TRUE);on.exit({sink();close(log)},add=TRUE)
 for(row in manifest$models){
   inp<-row$input;out<-sub('\\.inp$','.out',inp)
   stopifnot(!file.exists(out),digest(inp,algo='sha256',file=TRUE)==row$input_sha256,digest(row$data,algo='sha256',file=TRUE)==row$data_sha256)
   clauder_progress(paste0(row$id,'_resource_check'),'新鲜Windows准入检查，单槽位，不复制分析数据')
   check_resource(row$id)
   clauder_progress(row$id,paste('单槽位估计，N=',row$N));cat(format(Sys.time()),'START',row$id,'\n');flush.console()
   start<-Sys.time();runModels(target=inp,recursive=FALSE,showOutput=FALSE,replaceOutfile='never',Mplus_command=mplus_command,killOnFail=FALSE,logFile=file.path(dirname(inp),'MplusAutomation.log'))
   stopifnot(file.exists(out));parsed<-readModels(out,quiet=TRUE);saveRDS(parsed,file.path(dirname(inp),'readback.rds'))
   txt<-readLines(out,warn=FALSE);normal<-any(grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',txt,fixed=TRUE));negative<-FALSE
   p<-parsed$parameters$unstandardized
   if(is.data.frame(p)){
     v<-p[p$paramHeader %in% c('Variances','Residual.Variances'),]
     negative<-any(v$est<0,na.rm=TRUE)
     if('est_se'%in%names(v))negative<-negative||any(v$se>0&v$est_se<0&v$est_se> -900,na.rm=TRUE)
     p$model_id<-row$id;write.csv(p,file.path(dirname(inp),'parameters.csv'),row.names=FALSE)
   }
   flat<-gsub('[[:space:]]+',' ',paste(txt,collapse=' '))
   badmatrix<-grepl('NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT',flat)
   warnings<-txt[grepl('WARNING|ERROR|NOT POSITIVE|DID NOT CONVERGE|NO CONVERGENCE|SADDLE POINT',txt)]
   result<-list(id=row$id,N=row$N,normal_termination=normal,negative_variance=negative,matrix_diagnostic=badmatrix,warnings=warnings,status=if(!normal)'ESTIMATION_FAILED' else if(negative||badmatrix)'ESTIMATED_INADMISSIBLE_FOR_INFERENCE' else 'ESTIMATED_REVIEWABLE',seconds=as.numeric(difftime(Sys.time(),start,units='secs')),input_sha256=row$input_sha256,output_sha256=digest(out,algo='sha256',file=TRUE))
   receipt[[length(receipt)+1L]]<-result;write_json(receipt,file.path(dest,batch_dir,'execution_receipt.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA)
   cat(format(Sys.time()),result$status,result$seconds,'seconds\n');flush.console()
   clauder_progress(paste0(row$id,'_done'),result$status)
   rm(parsed,p,txt);gc(verbose=FALSE)
 }
 cat('SENSITIVITY_BATCH_COMPLETE\n');clauder_progress('sensitivity_complete',paste(length(receipt),'个模型已终态并保存诊断；待科学解释与文稿整合'))
})
