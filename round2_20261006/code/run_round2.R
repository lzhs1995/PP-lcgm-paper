# 单worker逐项执行；来源断言、Windows准入和逐项完整输出均落盘。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2_20261006'
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup'
 .libPaths(readRDS(file.path(q,'foreground_library_paths.rds')))
 library(MplusAutomation);library(jsonlite);library(digest)
 mplus<-unname(Sys.which('Mplus'));stopifnot(nzchar(mplus),file.exists(mplus))
 manifest_name<-getOption('round2.manifest','manifest.json')
 manifest<-fromJSON(file.path(root,manifest_name),simplifyVector=FALSE)
 progress<-function(stage,message){
   write_json(list(stage=stage,message=message,updated_at=as.character(Sys.time()),worker_pid=Sys.getpid()),file.path(root,'runtime/progress.json'),auto_unbox=TRUE,pretty=TRUE)
   cat(format(Sys.time()),stage,message,'\n');flush.console();clauder_progress(stage,message)
 }
 check_resource<-function(id){
   path<-file.path(root,'runtime',paste0('host_',id,'.json'))
   profiler<-'C:/Users/LZHS/.agents/skills/mplusautomation-guide/scripts/windows_host_profile.py'
   python<-'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
   result<-system2(python,c('-X','utf8',shQuote(profiler),'--output',shQuote(path),'--samples','3','--interval','1','--include-processes'),stdout=TRUE,stderr=TRUE)
   stopifnot(is.null(attr(result,'status'))||attr(result,'status')==0L)
   p<-fromJSON(path,simplifyVector=FALSE)$profile
   vals<-unlist(p$system[c('free_phys_gib','free_virtual_gib','disk_free_gib')]);stopifnot(length(vals)==3L,all(is.finite(vals)))
   # 本轮限定单worker：沿用已发布首跑预算，保留至少1GiB系统物理余量。
   other<-Filter(function(x)grepl('^mplus',x$name,ignore.case=TRUE),p$processes)
   cpu<-unlist(p$system$cpu_percent_samples)
   ok<-vals[1]>=2.25&&vals[2]>=2.5&&vals[3]>=5&&length(other)==0L&&length(cpu)==3L&&mean(cpu)<90
   write_json(list(id=id,admitted=ok,physical_gib=vals[1],commit_headroom_gib=vals[2],disk_gib=vals[3],other_mplus=length(other)),file.path(root,'runtime',paste0('admission_',id,'.json')),auto_unbox=TRUE,pretty=TRUE)
   ok
 }
 # 合成模型仅验证本次执行链，不计入11个科学规格。
 smoke<-file.path(root,'runtime/synthetic_smoke');dir.create(smoke,showWarnings=FALSE)
 if(!file.exists(file.path(smoke,'model.out'))){
   stopifnot(check_resource('smoke'));set.seed(20261006);dd<-data.frame(x=rnorm(200));dd$y<-.5*dd$x+rnorm(200)
   obj<-mplusObject(TITLE='Round2 licensed chain smoke',VARIABLE='USEVARIABLES=x y;',ANALYSIS='ESTIMATOR=MLR; PROCESSORS=1;',MODEL='y ON x;',rdata=dd)
   wd<-getwd();setwd(smoke);tryCatch(mplusModeler(obj,dataout='synthetic.dat',modelout='model.inp',run=0L,hashfilename=FALSE,quiet=TRUE),finally=setwd(wd))
   runModels(file.path(smoke,'model.inp'),recursive=FALSE,showOutput=FALSE,Mplus_command=mplus,killOnFail=FALSE,logFile=file.path(smoke,'run.log'))
 }
 stopifnot(any(grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',readLines(file.path(smoke,'model.out')),fixed=TRUE)))
 for(row in manifest$models){
   inp<-row$input;out<-sub('\\.inp$','.out',inp);dest<-dirname(inp);receipt<-file.path(dest,'receipt.json')
   stopifnot(digest(file=inp,algo='sha256')==row$input_sha256,digest(file=row$data,algo='sha256')==row$data_sha256)
   if(file.exists(receipt)){progress(row$id,'已有本轮终态，验证来源后跳过');next}
   if(!file.exists(out)){
     progress(paste0(row$id,'_admission'),'Windows资源准入')
     if(!check_resource(row$id))stop('RESOURCE_ADMISSION_HOLD: ',row$id)
     progress(row$id,paste('开始估计，N=',row$N));start<-Sys.time()
     runModels(inp,recursive=FALSE,showOutput=FALSE,replaceOutfile='never',Mplus_command=mplus,killOnFail=FALSE,logFile=file.path(dest,'MplusAutomation.log'))
     elapsed<-as.numeric(difftime(Sys.time(),start,units='secs'))
   }else elapsed<-NA_real_
   stopifnot(file.exists(out));txt<-readLines(out,warn=FALSE);flat<-gsub('[[:space:]]+',' ',paste(txt,collapse=' '))
   parsed<-tryCatch(readModels(out,quiet=TRUE),error=function(e)list(read_error=conditionMessage(e)))
   saveRDS(parsed,file.path(dest,'readback.rds'));p<-parsed$parameters$unstandardized
   negative<-FALSE;se_ok<-FALSE
   if(is.data.frame(p)&&nrow(p)>0){
     write.csv(p,file.path(dest,'parameters.csv'),row.names=FALSE)
     v<-p[p$paramHeader%in%c('Variances','Residual.Variances'),]
     negative<-any(v$est<0,na.rm=TRUE)||any(v$se>0&v$est_se<0&v$est_se> -900,na.rm=TRUE)
     se_ok<-all(is.finite(p$est))&&all(is.finite(p$se))
   }
   if(is.data.frame(parsed$summaries))write.csv(parsed$summaries,file.path(dest,'fit.csv'),row.names=FALSE)
   normal<-grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',flat,fixed=TRUE)
   bad<-grepl('NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT|STANDARD ERRORS.*COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED',flat)
   result<-list(id=row$id,attempt_id=row$attempt_id,N=row$N,normal=normal,negative_variance=negative,matrix_warning=bad,finite_parameters_SE=se_ok,status=if(!normal)'ESTIMATION_FAILED' else if(negative||bad||!se_ok)'INADMISSIBLE' else 'REVIEWABLE',seconds=elapsed,input_sha256=row$input_sha256,data_sha256=row$data_sha256,output_sha256=digest(file=out,algo='sha256'),version_header=head(txt,3),diagnostics=txt[grepl('WARNING|ERROR|NOT POSITIVE|DID NOT CONVERGE|NO CONVERGENCE|ITERATIONS EXCEEDED|SADDLE POINT',txt)])
   write_json(result,receipt,pretty=TRUE,auto_unbox=TRUE,digits=NA)
   progress(paste0(row$id,'_done'),result$status);rm(parsed,p,txt);gc(verbose=FALSE)
 }
 progress('batch_complete',paste(length(manifest$models),'项获得执行终态；待独立矩阵与科学诊断'))
 writeLines('BATCH_COMPLETE',file.path(root,'runtime',paste0(manifest_name,'_complete.txt')))
})
