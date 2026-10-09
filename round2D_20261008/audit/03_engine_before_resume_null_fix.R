# 实际Mplus队列：每次调用单独目录、不可变输入、实时进度、数值核查和完整失败留档。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/01_tools.R',local=TRUE)
library(processx)
MP<-unname(Sys.which('Mplus'));if(!nzchar(MP))MP<-'C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Mplus.exe'
PY<-'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
REG<-file.path(ROOT,'audit/CALL_REGISTER.csv')
register_call<-function(row) {
 tab<-if(file.exists(REG))read.csv(REG,stringsAsFactors=FALSE)else data.frame()
 if(nrow(tab)&&any(tab$id==row$id))stop('Existing call without terminal receipt; inspect running state before resubmission: ',row$id)
 caps<-contract()$call_caps
 if(nrow(tab)>=caps$TOTAL||sum(tab$category==row$category)>=caps[[row$category]])
  execution_limit('CALL_COUNT_BUDGET',paste('Call budget exhausted before',row$id,'category',row$category))
 rec<-data.frame(id=row$id,z=row$z,spec=row$spec,member=row$member,attempt=row$attempt,category=row$category,kind=row$kind,created=as.character(Sys.time()),input_sha256=row$input_sha256,data_sha256=row$data_sha256)
 write.csv(rbind(tab,rec),REG,row.names=FALSE)
}
model_dir<-function(z,spec,k,attempt,sample='Z0')file.path(ROOT,'models',z,paste0(spec,'_',sample,sprintf('_MI%02d',k)),attempt)
data_path<-function(z,k,sample='Z0')file.path(ROOT,'private',z,sprintf('%s_member_%02d.dat',sample,k))
extract_dims<-function(L) {
 s<-grep('Dimensions of numerical integration',L,value=TRUE)
 if(!length(s))return(NA_integer_);as.integer(sub('.*?([0-9]+)[[:space:]]*$','\\1',s[1]))
}
prepare_model<-function(z,spec,k,attempt='base',category='TARGET',sample='Z0',settings=list(method='quadrature',points=15,seed=26100801),start_from=NULL,warm_from=NULL,source_data=NULL,ctrl=NULL,shape=NULL) {
 dest<-model_dir(z,spec,k,attempt,sample);cf<-file.path(dest,'input_contract.json')
 if(file.exists(cf))return(fromJSON(cf))
  si<-spec_info(z,spec,ctrl,sample,shape);isL<-si$kind!='linear';m<-si$model
  warm_hash<-NULL
  if(!is.null(warm_from)){
    wr<-fromJSON(file.path(warm_from,'receipt.json'));stopifnot(isTRUE(wr$usable),wr$spec==spec)
    sv<-svalues_block(readLines(file.path(warm_from,'model.out'),warn=FALSE));stopifnot(length(sv)>0)
    m<-sv;warm_hash<-hashf(file.path(warm_from,'model.out'))
  }
 # 仅改变起点，不固定终值；基线和高精度模型不沿用非法父模型。
 if(!is.null(start_from)){
  kp<-read.csv(file.path(start_from,'key_paths.csv'));la<-intersect(kp$label,c('dc','dcg','bss'))
  for(lab in la){kk<-kp[kp$label==lab,];start<-if(kk$estimate<=0).3 else -.3
    hit<-grep(paste0('\\(',lab,'\\);$'),m);stopifnot(length(hit)==1)
    m[hit]<-paste0(tolower(kk$row),' ON ',tolower(kk$column),'*',start,' (',lab,');')}
 }
 optimizer<-if(is.null(settings$optimizer))'automatic' else settings$optimizer
 stopifnot(optimizer%in%c('automatic','EM'))
 integration_algorithm<-if(optimizer=='EM')'ALGORITHM=INTEGRATION EM;' else 'ALGORITHM=INTEGRATION;'
 an<-if(!isL)'TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=1; COVERAGE=.005; ITERATIONS=2000;' else c(
   'TYPE=COMPLEX RANDOM; ESTIMATOR=MLR; PROCESSORS=1;',
   if(settings$method=='montecarlo')paste0(integration_algorithm,' INTEGRATION=MONTECARLO(',settings$points,');')else paste0(integration_algorithm,' INTEGRATION=',settings$points,';'),
   paste0('MCSEED=',settings$seed,'; COVERAGE=.005; ITERATIONS=2000; MITERATIONS=4000;'))
 text<-inp_text(paste('Round2D',z,spec,sample,sprintf('MI%02d',k),attempt),si$use,an,m,si$define,kind=if(isL)'lms' else 'linear')
 src<-if(is.null(source_data))data_path(z,k,sample)else source_data;stopifnot(file.exists(src))
 dir.create(dest,recursive=TRUE,showWarnings=FALSE);stopifnot(file.copy(src,file.path(dest,'data.dat'),overwrite=FALSE))
 writeLines(text,file.path(dest,'model.inp'),useBytes=TRUE)
 dat<-read_dat(src)
 row<-list(id=paste(z,spec,sample,k,attempt,sep='_'),z=z,spec=spec,member=k,attempt=attempt,category=category,kind=si$kind,sample=sample,
  N=nrow(dat),households=length(unique(dat[[1]])),settings=settings,ctrl=ctrl,shape=shape,dest=dest,
  input_sha256=hashf(file.path(dest,'model.inp')),data_sha256=hashf(src),source_data=src,contract_sha256=hashf(file.path(ROOT,'RUN_CONTRACT.json')),
  warm_start_output_sha256=warm_hash,producer_code_sha256=setNames(vapply(c('01_tools.R','03_engine.R','06_queue.R'),function(f)hashf(file.path(ROOT,'code',f)),character(1)),c('tools','engine','queue')))
 wj(row,cf);row
}
readback_model<-function(row,seconds=NA_real_,exitcode=NA_integer_) {
 dest<-row$dest;out<-file.path(dest,'model.out');r<-c(row[c('id','z','spec','member','attempt','category','kind','sample','N','households','settings')],list(usable=FALSE,seconds=seconds,exitcode=exitcode))
 save_receipt<-function(r){wj(r,file.path(dest,'receipt.json'));r}
 if(!file.exists(out)){r$status<-'NO_OUTPUT';return(save_receipt(r))}
 L<-readLines(out,warn=FALSE);flat<-paste(L,collapse=' ');r$output_sha256<-hashf(out);r$integration_dimensions<-extract_dims(L)
 r$normal<-grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',flat,fixed=TRUE)
 if(grepl('\\*\\*\\* ERROR|ERROR in .* command|Unknown variable|Unknown option',flat)){r$status<-'INPUT_REJECTED';r$error_lines<-L[grepl('ERROR|Unknown|not allowed|not available|must be',L,ignore.case=TRUE)];return(save_receipt(r))}
 if(!r$normal){r$status<-if(exitcode==124L&&!is.na(exitcode))'TIMEOUT' else if(grepl('NO CONVERGENCE|DID NOT CONVERGE|ITERATIONS EXCEEDED|ITERATION LIMIT',flat))'NOT_CONVERGED' else 'ESTIMATION_FAILED';return(save_receipt(r))}
 rd<-tryCatch(MplusAutomation::readModels(out,quiet=TRUE),error=function(e){wj(list(error=conditionMessage(e)),file.path(dest,'MplusAutomation_readback_error.json'));NULL})
 if(!is.null(rd$summaries))write.csv(rd$summaries,file.path(dest,'fit.csv'),row.names=FALSE)
 if(!is.null(rd$parameters$unstandardized))write.csv(rd$parameters$unstandardized,file.path(dest,'parameters.csv'),row.names=FALSE)
 if(!is.null(rd$tech1))wj(rd$tech1,file.path(dest,'tech1.json'))
 if(!is.null(rd$tech4))wj(rd$tech4,file.path(dest,'tech4.json'))
 if(!is.null(rd$residuals))wj(rd$residuals,file.path(dest,'local_residuals.json'))
 m<-tryCatch(read_mplus_raw(dest),error=function(e){wj(list(error=conditionMessage(e)),file.path(dest,'extraction_error.json'));NULL})
 if(is.null(m)){r$status<-'EXTRACTION_FAILED';return(save_receipt(r))}
 si<-spec_info(row$z,row$spec,row$ctrl,row$sample,row$shape)
 write.csv(m$par,file.path(dest,'parameters_high_precision.csv'),row.names=FALSE);write.csv(m$V,file.path(dest,'parameter_covariance.csv'));wj(m$extra,file.path(dest,'fit_raw.json'))
 gt<-gate2(m,si);wj(gt[setdiff(names(gt),'geometry')],file.path(dest,'parameter_gate.json'))
 if(!is.null(gt$geometry$matrices))for(n in names(gt$geometry$matrices))write.csv(gt$geometry$matrices[[n]],file.path(dest,paste0('matrix_',n,'.csv')))
 wj(gt$geometry[setdiff(names(gt$geometry),'matrices')],file.path(dest,'geometry.json'))
 kp<-tryCatch(key_paths(m,si$key),error=function(e){wj(list(error=conditionMessage(e)),file.path(dest,'key_error.json'));NULL})
 match_print<-FALSE
 if(!is.null(kp)){
  write.csv(kp,file.path(dest,'key_paths.csv'),row.names=FALSE)
  if(is.data.frame(rd$parameters$unstandardized)){
   pp<-rd$parameters$unstandardized
   pk<-vapply(seq_len(nrow(kp)),function(i){q<-pp$est[toupper(pp$paramHeader)==paste0(kp$row[i],'.ON')&toupper(pp$param)==kp$column[i]];if(length(q)==1)q else NA_real_},numeric(1))
   match_print<-all(is.finite(pk))&&all(abs(pk-kp$estimate)<=.0006)
   write.csv(data.frame(kp,printed=pk),file.path(dest,'key_printed_comparison.csv'),row.names=FALSE)
  }
 }
 r$LL<-m$extra[['H0 Loglikelihood']];if(is.null(r$LL)&&!is.null(rd$summaries$LL))r$LL<-rd$summaries$LL
 r$parameters<-m$P;r$negative<-gt$negative;r$geometry_ok<-gt$geometry$passed;r$vcov_ok<-gt$vcov$ok;r$warnings<-gt$flags$warnings;r$printed_match<-match_print
 r$usable<-gt$passed&&!is.null(kp)&&match_print
 r$status<-if(r$usable)'USABLE' else if(is.null(kp))'KEY_PATH_ERROR' else if(!match_print)'PRINTED_MISMATCH' else 'INADMISSIBLE'
 save_receipt(r)
}
run_model<-function(row) {
 dest<-row$dest;rf<-file.path(dest,'receipt.json');if(file.exists(rf))return(fromJSON(rf))
 stopifnot(hashf(file.path(dest,'model.inp'))==row$input_sha256,hashf(file.path(dest,'data.dat'))==row$data_sha256)
 if(file.exists(file.path(dest,'model.out')))stop('Existing output without final receipt: recover readback, do not rerun ',row$id)
 # 每次准入只检查Windows宿主；资源等待不是统计失败。
 tgate<-Sys.time()
 repeat{
  rr<-file.path(dest,'resource_before.json');res<-processx::run(PY,c(file.path(ROOT,'code/resource_gate.py'),rr),error_on_status=FALSE)
  stopifnot(res$status==0);a<-fromJSON(rr)
  if(isTRUE(a$admit))break
  progress('resource_wait',paste(row$id,'available GiB',round(a$available_physical_gib,2),'external Mplus',a$external_mplus_count))
  if(as.numeric(difftime(Sys.time(),tgate,units='hours'))>6)execution_limit('RESOURCE_WAIT_LIMIT',paste('Resource wait limit before',row$id))
  Sys.sleep(30)
 }
 completed<-list.files(file.path(ROOT,'models'),pattern='receipt.json$',full.names=TRUE,recursive=TRUE)
 hours<-sum(vapply(completed,function(f){r<-fromJSON(f);if(is.null(r$seconds)||is.na(r$seconds))0 else r$seconds/3600},numeric(1)))
 remaining<-max(0,(contract()$total_estimation_hours-hours)*3600)
 if(remaining<=0)execution_limit('TOTAL_ESTIMATION_BUDGET',paste('Estimation time budget exhausted before',row$id))
 attempt_limit<-min(contract()$single_attempt_hours*3600,remaining)
 register_call(row);t0<-Sys.time();progress('estimate_start',paste(row$id,'N',row$N,'integration',row$settings$method,row$settings$points))
  p<-processx::process$new(MP,'model.inp',wd=dest,stdout=file.path(dest,'mplus_console.log'),stderr='2>&1',cleanup=FALSE)
 wj(list(id=row$id,pid=p$get_pid(),started=as.character(t0),input_sha256=row$input_sha256),file.path(dest,'process.json'))
 timedout<-FALSE
 while(p$is_alive()){
  p$wait(timeout=10000);elapsed<-as.numeric(difftime(Sys.time(),t0,units='secs'))
  progress('estimating',paste(row$id,'elapsed_s',round(elapsed),'out_bytes',if(file.exists(file.path(dest,'model.out')))file.info(file.path(dest,'model.out'))$size else 0))
  if(elapsed>attempt_limit){p$kill_tree();timedout<-TRUE;break}
 }
 sec<-as.numeric(difftime(Sys.time(),t0,units='secs'));ec<-if(timedout)124L else p$get_exit_status()
 r<-readback_model(row,sec,ec)
 if(timedout){r$timeout_reason<-if(remaining<contract()$single_attempt_hours*3600)'TOTAL_ESTIMATION_BUDGET' else 'SINGLE_ATTEMPT_LIMIT';r$limit_seconds<-attempt_limit;wj(r,file.path(dest,'receipt.json'))}
 progress('estimate_complete',paste(row$id,r$status,'seconds',round(sec)))
 r
}
read_model<-function(z,spec,k,attempt='base',sample='Z0') {
 d<-model_dir(z,spec,k,attempt,sample);f<-file.path(d,'receipt.json');if(!file.exists(f))return(NULL)
 r<-fromJSON(f);a<-list(receipt=r,dest=d);if(isTRUE(r$usable)){a$raw<-read_mplus_raw(d);a$key<-read.csv(file.path(d,'key_paths.csv'))};a
}
run_one<-function(z,spec,k,attempt='base',category='TARGET',sample='Z0',settings=list(method='quadrature',points=15,seed=26100801),...) {
 row<-prepare_model(z,spec,k,attempt,category,sample,settings,...);run_model(row);read_model(z,spec,k,attempt,sample)
}
