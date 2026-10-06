# 第二轮：固定来源和11个基础规格；在隔离worker执行，不修改前台对象。
local({
 root <- 'C:/Users/LZHS/pp_lgcm_review/round2_20261006'
 prior <- 'C:/Users/LZHS/pp_lgcm_review/20261005'
 q <- 'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 .libPaths(readRDS(file.path(dirname(q),'foreground_library_paths.rds')))
 library(MplusAutomation);library(jsonlite);library(digest)
 progress <- function(s,m){cat(s,m,'\n');flush.console();if(exists('clauder_progress'))clauder_progress(s,m)}
 progress('R1_read','读取修正数据与测量核验对象')
 dp <- file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds')
 ap <- file.path(prior,'analysis/local_measurement_values.rds')
 d <- readRDS(dp);a <- readRDS(ap)
 # 仅清除工作副本的haven元数据，避免不同vctrs版本禁止as.matrix；原数值及原文件不变。
 labels <- lapply(d,function(z)attr(z,'label',exact=TRUE))
 plain <- function(z){if(inherits(z,'haven_labelled'))attributes(z)<-NULL;z}
 d <- as.data.frame(lapply(d,plain),check.names=FALSE)
 stopifnot(nrow(d)==3274L,identical(as.numeric(d$pid),as.numeric(plain(a$pid))),!anyDuplicated(d$pid))
 yrs <- c(12,16,18,20,22)
 y <- as.matrix(a$cesd8);yy <- as.matrix(d[,paste0('ces8',yrs)])
 stopifnot(identical(unname(is.na(y)),unname(is.na(yy))),max(abs(y-yy),na.rm=TRUE)<1e-10)
 x <- as.matrix(d[,paste0('wfdms',yrs)])
 old <- fromJSON(file.path(prior,'analysis/sensitivity/manifest.json'),simplifyVector=FALSE)
 cov <- unlist(old$covariates);stopifnot(length(cov)==26L)
 common <- rowSums(!is.na(y[,2:5]))>=2 & rowSums(!is.na(a$cesd20[,2:5]))>=2 & rowSums(!is.na(x[,2:5]))>=2
 cc <- common & complete.cases(d[,cov]);stopifnot(sum(common)==2225L,sum(cc)==1981L)
 ym <- mean(y[,1],na.rm=TRUE);ys <- sd(y[,1],na.rm=TRUE); yz <- (y-ym)/ys
 dir.create(file.path(root,'audit'),showWarnings=FALSE);dir.create(file.path(root,'models'),showWarnings=FALSE)
 saveRDS(list(original_PID=d$pid,original_FID=d$fid,common=common,complete_covariates=cc),file.path(root,'private/sample_membership.rds'))
 dict <- do.call(rbind,lapply(seq_along(cov),function(i){v<-cov[i];z<-d[[v]];lab<-labels[[v]];data.frame(mplus=paste0('c',i),variable=v,label=if(is.null(lab))'' else lab,missing_original=sum(is.na(z)),unique_observed=length(unique(z[!is.na(z)])),min=min(z,na.rm=TRUE),max=max(z,na.rm=TRUE),type=class(z)[1],time_review=if(v=='wave')'FOLLOWUP_COUNT_REQUIRES_INTERPRETATION' else 'BASELINE_NAME_VERIFY_SOURCE')}))
 write.csv(dict,file.path(root,'audit/covariates_26.csv'),row.names=FALSE)
 write.csv(data.frame(year=2000+yrs,N=colSums(!is.na(y)),minimum=apply(y,2,min,na.rm=TRUE),maximum=apply(y,2,max,na.rm=TRUE),entry_difference=colSums(abs(y-yy)>1e-10,na.rm=TRUE)),file.path(root,'audit/analysis_entry.csv'),row.names=FALSE)
 source <- list(data_file=dp,data_sha256=digest(file=dp,algo='sha256'),measurement_file=ap,measurement_sha256=digest(file=ap,algo='sha256'),N=3274,common_N=2225,diagnostic_N=1981,baseline_mean=ym,baseline_sd=ys,PID_hash=digest(d$pid,algo='sha256'),FID_hash=digest(d$fid,algo='sha256'),MplusAutomation=as.character(packageVersion('MplusAutomation')),R=R.version.string,mplus=unname(Sys.which('Mplus')),script_sha256=digest(file='C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/cfps_round2_20261006/prepare_round2.R',algo='sha256'))
 write_json(source,file.path(root,'audit/source_contract.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 models <- list()
 growth <- function(f,v,t,shape){paste(f,'|',paste0(v,if(shape=='linear')'@' else c('@',rep('*',length(v)-2),'@'),t,collapse=' '),';')}
 prepare <- function(id,dat,model,use,meta,analysis='TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=1; COVERAGE=.005; ITERATIONS=1000;'){
   dest<-file.path(root,'models',id,'attempt01');stopifnot(!dir.exists(dest));dir.create(dest,recursive=TRUE)
   obj<-mplusObject(TITLE=paste('Round2',id),VARIABLE=paste0('CLUSTER=fid; USEVARIABLES=',use,';'),ANALYSIS=analysis,MODEL=model,OUTPUT='TECH1 TECH3 TECH4 SAMPSTAT RESIDUAL CINTERVAL;',rdata=dat,usevariables=names(dat))
   wd<-getwd();setwd(dest);tryCatch(mplusModeler(obj,dataout='data.dat',modelout='model.inp',run=0L,writeData='always',hashfilename=FALSE,quiet=TRUE),finally=setwd(wd))
   inp<-file.path(dest,'model.inp');data<-file.path(dest,'data.dat')
   stopifnot(all(nchar(readLines(inp,warn=FALSE))<=90));back<-read.table(data,na.strings='.')
   stopifnot(nrow(back)==nrow(dat),ncol(back)==ncol(dat),max(abs(as.matrix(back)-as.matrix(dat)),na.rm=TRUE)<1e-8)
   models[[length(models)+1L]]<<-c(list(id=id,attempt_id='attempt01',N=nrow(dat),households=length(unique(dat$fid)),input=inp,data=data,input_sha256=digest(file=inp,algo='sha256'),data_sha256=digest(file=data,algo='sha256')),meta)
 }
 # 科学规格固定：同样本同尺度；双过程的 SY ON IY 单列说明。
 for(shape in c('linear','free'))for(stage in c('U0','U1','P0','P1')){
   id<-paste0('D1981_',stage,'_',shape);dat<-data.frame(fid=as.numeric(d$fid[cc]),yz[cc,]);names(dat)<-c('fid',paste0('y',1:5))
   model<-growth('iy sy',paste0('y',1:5),c(0,4,6,8,10),shape);use<-'y1-y5'
   if(substr(stage,1,1)=='P'){
     xx<-data.frame(x[cc,]);names(xx)<-paste0('x',1:5);dat<-cbind(dat,xx);use<-paste(use,'x1-x5')
     model<-paste(growth('ix sx',paste0('x',1:5),c(0,4,6,8,10),'free'),model,'iy ON ix (bii);\nsy ON ix (bis);\nsy ON sx (bss);\nsy ON iy;',sep='\n')
   }
   if(substr(stage,2,2)=='1'){
     z<-as.data.frame(d[cc,cov]);names(z)<-paste0('c',1:26);dat<-cbind(dat,z);use<-paste(use,'c1-c26');model<-paste(model,'iy sy ON c1-c26;',sep='\n')
   }
   prepare(id,dat,model,use,list(stage=stage,shape_y=shape,shape_x=if(substr(stage,1,1)=='P')'free' else 'none',window='five',scale='CESD8_baseline_standardized',purpose='same_sample_diagnostic'))
 }
 for(shape in c('linear','free')){
   dat<-data.frame(fid=as.numeric(d$fid),y);names(dat)<-c('fid',paste0('y',1:5))
   prepare(paste0('D3274_U0_',shape),dat,growth('iy sy',paste0('y',1:5),c(0,4,6,8,10),shape),'y1-y5',list(stage='U0',shape_y=shape,shape_x='none',window='five',scale='CESD8_raw',purpose='cluster_recheck'))
 }
 dat<-data.frame(fid=as.numeric(d$fid[common]),y[common,2:5]);names(dat)<-c('fid',paste0('y',1:4))
 prepare('D2225_U0_four_linear',dat,growth('iy sy',paste0('y',1:4),c(0,2,4,6),'linear'),'y1-y4',list(stage='U0',shape_y='linear',shape_x='none',window='four',scale='CESD8_raw',purpose='four_wave_failure_diagnostic'))
 stopifnot(length(models)==11L)
 write_json(list(status='PREPARED_NOT_ESTIMATED',baseline=source,models=models),file.path(root,'manifest.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 progress('prepared','11个科学规格及数据入口断言已保存')
})
