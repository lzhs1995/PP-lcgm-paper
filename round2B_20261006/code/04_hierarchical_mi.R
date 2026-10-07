# 家庭-个人FCS工程批次。插补协变量，纵向X/Y/Z及其结构性缺失完全冻结。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 .libPaths(c(file.path(root,'private/library'),.libPaths()))
 library(mice);library(miceadds);library(jsonlite);library(digest)
 source(file.path(root,'code/mi_validation.R'),local=TRUE)
 write.csv(test_validator(),file.path(root,'audit/validator_synthetic_tests.csv'),row.names=FALSE)
 log<-file.path(root,'runtime',paste0('mi_engineering_',getOption('round2B.mi_attempt','attempt01'),'.log'));sink(log,split=TRUE);on.exit(sink())
 progress<-function(s,m){cat(format(Sys.time()),s,m,'\n');flush.console();write_json(list(stage=s,message=m,updated_at=as.character(Sys.time()),pid=Sys.getpid()),file.path(root,'runtime/mi_progress.json'),auto_unbox=TRUE,pretty=TRUE);clauder_progress(s,m)}
 progress('mi_synthetic_smoke','Test actual two-level PMM integration before real-data imputation')
 source(file.path(root,'code/mi_smoke.R'),local=TRUE);mi_smoke(root)
 progress('mi_preparation','Read verified baseline input and preserve observed masks')
 b<-readRDS(file.path(root,'private/baseline_preMI.rds'));d<-b$data
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 wp<-file.path(q,'pmm_observed_future_v3_NOT_RELEASED/working_observed.rds');old<-readRDS(wp)
 protocol<-fromJSON(file.path(q,'pmm_observed_future_v3_NOT_RELEASED/protocol.json'))
 # 旧辅助表不携带ID；用其绑定的实际MI输入再核对PID/FID顺序，不能只靠相同行数。
 ip<-file.path(q,'mi_measurement_repair_v3_marriage_aligned/corrected_measurement_MI.inp')
 mp<-file.path(dirname(ip),'corrected_measurement_MI_input.dat')
 stopifnot(digest(file=mp,algo='sha256')==protocol$data_sha256)
 txt<-gsub('![^\n]*','',paste(readLines(ip,warn=FALSE),collapse='\n'))
 nms<-regmatches(txt,regexec('(?is)\\bnames\\s*=([^;]+);',txt,perl=TRUE))[[1]][2]
 nm<-strsplit(tolower(trimws(nms)),'\\s+')[[1]]
 bound<-read.table(mp,col.names=nm,na.strings=c('.','*'),check.names=FALSE)
 stopifnot(identical(as.numeric(bound$pid),as.numeric(d$pid)),identical(as.numeric(bound$fid),as.numeric(d$fid)))
 write_json(list(N=nrow(bound),PID_order_matches=TRUE,FID_order_matches=TRUE,source_data_sha256=digest(file=mp,algo='sha256'),auxiliary_sha256=digest(file=wp,algo='sha256')),file.path(root,'audit/auxiliary_identity_binding.json'),pretty=TRUE,auto_unbox=TRUE)
 rm(bound);gc(verbose=FALSE)
 stopifnot(nrow(old)==nrow(d));binding<-list()
 for(v in c('wfd_m12','wfd_s12','ces812','sex12','age12')){
   x<-as.numeric(old[[v]]);y<-as.numeric(d[[v]])
   stopifnot(identical(is.na(x),is.na(y)),all(is.finite(x[!is.na(x)])),all(is.finite(y[!is.na(y)])),max(abs(x-y),na.rm=TRUE)<1e-12)
   binding[[v]]<-data.frame(variable=v,maximum_difference=max(abs(x-y),na.rm=TRUE),missing_pattern_identical=TRUE,tolerance=1e-12)
 }
 write.csv(do.call(rbind,binding),file.path(root,'audit/auxiliary_row_binding.csv'),row.names=FALSE)
 hhvars<-c('finc12','urban12','prov12');persons<-c('edu12','cdar12','pinc12','pinc212','marr12','sat12','adl12');targets<-c(hhvars,persons)
 # 排除未核实时间来源的party12；保留合法后期观测辅助信息，不把它们称作基期控制。
 base<-c('wfd_m12','wfd_s12','ces812','sex12','edu12','urban12','prov12','cdn12','cdar12','cdsc12','minor12','hukou12','age12','pinc12','pinc212','cores12','heal12','marr12','eco12','hwc12','sat12','adl12','finc12','employ12')
 dd<-d[base]
 for(v in protocol$auxiliary_features)dd[[v]]<-old[[v]]
 for(yr in c(16,18,20,22))for(v in c('wfdms','ces8sd')){
   x<-d[[paste0(v,yr)]];obs<-paste0('obs_',v,yr);mis<-paste0('missing_',v,yr)
   stopifnot(all(dd[[mis]]==as.integer(is.na(x))))
   dd[[obs]]<-ifelse(is.na(x),0,x)
 }
 # 基期Z缺失只创建辅助特征，不填改原始Z或其资格。
 for(v in c('wfd_d12','wfd_d112','wfd_d412')){
   stopifnot(v%in%names(d));dd[[paste0('obs_',v)]]<-ifelse(is.na(d[[v]]),0,d[[v]]);dd[[paste0('missing_',v)]]<-as.integer(is.na(d[[v]]))
 }
 dd$cluster<-as.integer(factor(d$fid));stopifnot(all(is.finite(dd$cluster)))
 non<-setdiff(names(dd),targets);stopifnot(all(vapply(dd[non],function(x)all(is.finite(x)),logical(1))))
 meth<-make.method(dd);meth[]<-'';meth[hhvars]<-'2lonly.pmm';meth[persons]<-'2l.pmm'
 pm<-matrix(0,ncol(dd),ncol(dd),dimnames=list(names(dd),names(dd)))
 for(v in targets){pm[v,setdiff(names(dd),c(v,'cluster'))]<-1;pm[v,'cluster']<--2}
 seed<-20261007L;set.seed(seed)
 # 初始化也保持家庭共同值；保留初始化对象，便于独立复核。
 init<-dd
 for(v in targets){
   obs<-dd[[v]][is.finite(dd[[v]])]
   if(v%in%hhvars){for(ii in split(seq_len(nrow(dd)),dd$cluster))if(all(is.na(dd[[v]][ii])))init[[v]][ii]<-sample(obs,1)}
   else init[[v]][is.na(dd[[v]])]<-sample(obs,sum(is.na(dd[[v]])),replace=TRUE)
 }
 saveRDS(list(original=dd,initial=init,mask=is.na(dd),method=meth,predictorMatrix=pm,visitSequence=targets,seed=seed,targets=targets,household=hhvars,personal=persons,auxiliary_source_sha256=digest(file=wp,algo='sha256')),file.path(root,'private/mi_actual_inputs.rds'))
 write.csv(pm,file.path(root,'audit/mi_predictor_matrix_requested.csv'))
 write_json(list(m=10,maxit=30,seed=seed,donors=5,methods=as.list(meth),visitSequence=targets,person_model='random-intercept PMM via miceadds::2l.pmm',household_model='mice::2lonly.pmm, one household draw',mice_version=as.character(packageVersion('mice')),miceadds_version=as.character(packageVersion('miceadds')),source_hash=digest(file=file.path(root,'private/baseline_preMI.rds'),algo='sha256'),limitations='FCS MAR working model; not proven congenial to latent interactions; categorical targets use donor support rather than Gaussian draws.'),file.path(root,'audit/mi_protocol.json'),auto_unbox=TRUE,pretty=TRUE)
 progress('mi_start','10 imputations, household and individual random-intercept PMM')
 imp<-mice(dd,m=10,maxit=1,method=meth,predictorMatrix=pm,visitSequence=targets,data.init=init,seed=seed,donors=5,printFlag=FALSE,remove.collinear=TRUE)
 saveRDS(imp,file.path(root,'private/mi_checkpoint.rds'))
 for(iter in 2:30){
   progress(paste0('mi_iteration_',iter),'Continue same chains; no restart or result-driven change')
   imp<-mice.mids(imp,maxit=1,donors=5,printFlag=FALSE)
   saveRDS(imp,file.path(root,'private/mi_checkpoint.rds'))
 }
 write.csv(imp$predictorMatrix,file.path(root,'audit/mi_predictor_matrix_actual.csv'))
 if(!is.null(imp$loggedEvents))write.csv(imp$loggedEvents,file.path(root,'audit/mi_logged_events.csv'),row.names=FALSE)
 write.csv(as.data.frame.table(imp$chainMean),file.path(root,'audit/mi_chain_means.csv'),row.names=FALSE)
 write.csv(as.data.frame.table(imp$chainVar),file.path(root,'audit/mi_chain_variances.csv'),row.names=FALSE)
 conv<-tryCatch(mice::convergence(imp),error=function(e)data.frame(error=conditionMessage(e)))
 write.csv(conv,file.path(root,'audit/mi_convergence.csv'),row.names=FALSE)
 rows<-list();manifest<-list();dir.create(file.path(root,'private/mi10'),showWarnings=FALSE)
 for(k in 1:10){
   ck<-complete(imp,k);a<-d
   for(v in targets)a[[v]]<-ck[[v]]
   a$prov122<-as.integer(a$prov12==2);a$prov123<-as.integer(a$prov12==3);a$pinc412<-as.integer(a$pinc212>0)
   val<-validate_member(d,a,targets,c('prov122','prov123','pinc412'),hhvars);val$imputation<-k;rows[[k]]<-val
   path<-file.path(root,'private/mi10',sprintf('member_%02d.rds',k));saveRDS(a,path)
   manifest[[k]]<-list(imputation=k,sha256=digest(file=path,algo='sha256'),N=nrow(a),passed=all(val$passed))
 }
 val<-do.call(rbind,rows);write.csv(val,file.path(root,'audit/mi_member_validation.csv'),row.names=FALSE)
 write_json(manifest,file.path(root,'audit/mi_member_manifest.json'),pretty=TRUE,auto_unbox=TRUE)
 stopifnot(all(val$passed));progress('mi_engineering_complete','All ten members validated; convergence and model adoption require review')
})
