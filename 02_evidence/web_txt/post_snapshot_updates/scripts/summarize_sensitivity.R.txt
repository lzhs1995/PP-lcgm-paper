# 原生回读预登记敏感性；失败、不可接受解均保留；不以数值显著性筛选。
local({
 library(MplusAutomation);library(jsonlite);library(digest)
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'; allrows<-list();params<-list();fits<-list()
 for(batch in c('sensitivity','sensitivity_input_repair')){
  man<-fromJSON(file.path(dest,'analysis',batch,'manifest.json'),simplifyVector=FALSE)
  for(r in man$models){
   out<-sub('\\.inp$','.out',r$input);stopifnot(file.exists(out));txt<-readLines(out,warn=FALSE)
   flat<-gsub('[[:space:]]+',' ',paste(txt,collapse=' '));p<-readModels(out,quiet=TRUE)
   normal<-grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',flat,fixed=TRUE)
   inputerr<-grepl('*** ERROR',flat,fixed=TRUE);nonconv<-grepl('NO CONVERGENCE|DID NOT CONVERGE|DID NOT TERMINATE NORMALLY',flat)
   matrix<-grepl('NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT',flat)
   pp<-p$parameters$unstandardized;neg<-FALSE;vars<-character()
   if(is.data.frame(pp)&&nrow(pp)){
    for(nm in setdiff(c('est','se','est_se','pval'),names(pp)))pp[[nm]]<-NA_real_
    v<-pp[pp$paramHeader %in% c('Variances','Residual.Variances'),]
    bad<-v$est<0 | (v$se>0 & v$est_se<0 & v$est_se> -900);bad[is.na(bad)]<-FALSE
    neg<-any(bad);vars<-v$param[bad]
    pp$ci_low_diagnostic<-ifelse(pp$se>0&pp$se<900,pp$est-qnorm(.975)*pp$se,NA_real_)
    pp$ci_high_diagnostic<-ifelse(pp$se>0&pp$se<900,pp$est+qnorm(.975)*pp$se,NA_real_)
    pp$model_id<-r$id;pp$batch<-batch;params[[length(params)+1L]]<-pp
   }
   state<-if(inputerr)'INPUT_REJECTED' else if(!normal||nonconv)'NONCONVERGED' else if(neg||matrix)'INADMISSIBLE' else 'REVIEWABLE'
   blocks<-lapply(which(grepl('WARNING|ERROR|NO CONVERGENCE|DID NOT CONVERGE|SADDLE POINT',txt)),function(i)paste(txt[i:min(i+6,length(txt))],collapse=' '))
   row<-data.frame(model_id=r$id,batch=batch,N=r$N,family=r$family,scale=r$scale,window=r$window,status=state,normal=normal,negative_variance=neg,negative_variables=paste(vars,collapse=';'),matrix_diagnostic=matrix,diagnostics=paste(unlist(blocks),collapse=' | '),output=out,sha256=digest(out,algo='sha256',file=TRUE),stringsAsFactors=FALSE)
   allrows[[length(allrows)+1L]]<-row
   if(is.data.frame(p$summaries)&&nrow(p$summaries)){f<-p$summaries;f$model_id<-r$id;f$batch<-batch;fits[[length(fits)+1L]]<-f}
  }
 }
 bind<-function(xs){nn<-unique(unlist(lapply(xs,names)));do.call(rbind,lapply(xs,function(x){x[setdiff(nn,names(x))]<-NA;x[,nn,drop=FALSE]}))}
 all<-bind(allrows);current<-all[all$family=='univariate'|all$batch=='sensitivity_input_repair',]
 stopifnot(nrow(current)==8L,all(table(current$model_id)==1L))
 write.csv(all,file.path(dest,'summaries/sensitivity_all_attempts.csv'),row.names=FALSE)
 write.csv(current,file.path(dest,'summaries/sensitivity_current_status.csv'),row.names=FALSE)
 write.csv(bind(params),file.path(dest,'summaries/sensitivity_parameters.csv'),row.names=FALSE)
 write.csv(bind(fits),file.path(dest,'summaries/sensitivity_fit.csv'),row.names=FALSE)
 write_json(list(executed_attempts=nrow(all),current_specifications=nrow(current),status=as.list(table(current$status)),new_interactions=0,ci_note='Diagnostic normal-approximation intervals use printed estimates/SE; no inference from nonconverged or inadmissible models.'),file.path(dest,'summaries/sensitivity_summary.json'),auto_unbox=TRUE,pretty=TRUE)
 cat('12次尝试、8个规格；当前状态：\n');print(current[,c('model_id','N','status','negative_variables')])
})
