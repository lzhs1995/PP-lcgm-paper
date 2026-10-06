# 预先限定8个窗口/量尺对照；不替代原五期主分析，也不采用未验收的插补。
local({
 library(MplusAutomation);library(jsonlite);library(digest)
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 d<-readRDS(file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds'))
 a<-readRDS(file.path(dest,'analysis/local_measurement_values.rds'));stopifnot(identical(as.numeric(a$pid),as.numeric(d$pid)))
 old<-fromJSON('C:/Users/LZHS/pp_lgcm_sensitivity/20261002_direct11_contract/audit.json',simplifyVector=FALSE)$specifications[[1]]
 stopifnot(old$model=='c_pp_lgca_type1_mi_tics.out')
 cov<-setdiff(unlist(old$usevar),c(paste0('wfdms',c(12,16,18,20,22)),paste0('ces8sd',c(12,16,18,20,22))))
 x<-as.matrix(d[,paste0('wfdms',c(12,16,18,20,22))]);common<-rowSums(!is.na(a$cesd8[,2:5]))>=2&rowSums(!is.na(a$cesd20[,2:5]))>=2&rowSums(!is.na(x[,2:5]))>=2
 rows<-list()
 for(family in c('univariate','direct'))for(scale in c('CESD8','CESD20'))for(window in c('five','four')){
   key<-paste(family,scale,window,sep='_');out<-file.path(dest,'analysis/sensitivity',key);dir.create(out,recursive=TRUE,showWarnings=FALSE)
   if(file.exists(file.path(out,'model.out')))stop('已有输出，不能覆盖或重跑：',key)
   select<-if(family=='univariate')common else common&complete.cases(d[,cov])
   y<-if(scale=='CESD8')a$cesd8 else a$cesd20
   raw_base_mean<-mean(y[,1],na.rm=TRUE);raw_base_sd<-sd(y[,1],na.rm=TRUE)
   if(family=='direct')y<-(y-raw_base_mean)/raw_base_sd
   waves<-if(window=='five')1:5 else 2:5;years<-c(2012,2016,2018,2020,2022)[waves];times<-years-years[1]
   dat<-data.frame(fid=as.numeric(d$fid[select]),y[select,waves,drop=FALSE]);names(dat)<-c('fid',paste0('y',seq_along(waves)))
   yn<-paste0('y',seq_along(waves));xn<-paste0('x',seq_along(waves))
   growth<-function(factors,variables){paste(factors,'|',paste0(variables,c('@',rep('*',length(variables)-2),'@'),times,collapse=' '),';')}
   model<-growth('iy sy',yn)
   if(family=='direct') {
     xx<-data.frame(x[select,waves,drop=FALSE]);names(xx)<-xn;cc<-as.data.frame(d[select,cov]);names(cc)<-paste0('c',seq_along(cov));dat<-cbind(dat,xx,cc)
     model<-paste(growth('ix sx',xn),model,'iy ON ix (bii);\nsy ON ix (bis);\nsy ON sx (bss);\nsy ON iy;\niy sy ON c1-c26;',sep='\n')
   }
   usevars<-paste0('y1-y',length(waves),if(family=='direct')paste0(' x1-x',length(waves),' c1-c26') else '')
   object<-mplusObject(TITLE=paste('CFPS review sensitivity',key),VARIABLE=paste0('CLUSTER=fid;\nUSEVARIABLES=',usevars,';'),ANALYSIS='TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=1; COVERAGE=.005;',MODEL=model,OUTPUT='TECH1 TECH4 SAMPSTAT RESIDUAL;',rdata=dat,usevariables=names(dat))
   wd<-getwd();setwd(out)
   tryCatch(mplusModeler(object,dataout='data.dat',modelout='model.inp',run=0L,writeData='always',hashfilename=FALSE,quiet=TRUE),finally=setwd(wd))
   stopifnot(all(nchar(readLines(file.path(out,'model.inp')))<=90))
   check<-read.table(file.path(out,'data.dat'),na.strings='.');stopifnot(nrow(check)==nrow(dat),ncol(check)==ncol(dat),identical(as.numeric(check[,1]),as.numeric(dat$fid)))
   rows[[length(rows)+1L]]<-list(id=key,family=family,scale=scale,window=window,N=nrow(dat),households=length(unique(dat$fid)),input=file.path(out,'model.inp'),input_sha256=digest(file.path(out,'model.inp'),algo='sha256',file=TRUE),data=file.path(out,'data.dat'),data_sha256=digest(file.path(out,'data.dat'),algo='sha256',file=TRUE),years=years,anchors=range(times),raw_baseline_mean=raw_base_mean,raw_baseline_sd=raw_base_sd,common_sample_rule='original cohort; >=2 valid 2016-2022 observations in CESD8, CESD20sc, and mean closeness',covariate_rule=if(family=='direct')'complete observed baseline covariates; same26 as original type1; no imputation' else 'unadjusted',status='PREPARED_NOT_ESTIMATED')
 }
 write_json(list(scope='WINDOW_SCALE_SENSITIVITY_NOT_PRIMARY_REPLACEMENT',common_N=sum(common),complete_covariates_N=sum(common&complete.cases(d[,cov])),covariates=cov,models=rows,interpretation='四期的潜截距对应2016；完整协变量子样本为敏感性，不能冒充原3274人插补主分析。未采用因子得分或估计交互。'),file.path(dest,'analysis/sensitivity/manifest.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA)
 cat('已准备',length(rows),'个预登记模型；共同样本',sum(common),'；完整协变量样本',sum(common&complete.cases(d[,cov])),'；新增估计0\n')
})
