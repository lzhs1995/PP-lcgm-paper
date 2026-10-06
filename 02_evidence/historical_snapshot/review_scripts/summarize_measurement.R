# 七项意见的 T1–T7 汇总；只读原始数据，全部新产物写入隔离工作区。
# 依赖已有五波逐题来源登记与已修正 CESD8 候选；不采用旧插补值。
local({
 library(haven); library(jsonlite); library(digest); library(MplusAutomation)
 q <- 'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 dest <- 'C:/Users/LZHS/pp_lgcm_review/20261005'
 logcon <- file(file.path(dest,'native/measurement_summary.log'),'wt',encoding='UTF-8')
 sink(logcon,split=TRUE); on.exit({sink();close(logcon)},add=TRUE)
 step <- function(stage,message) {
   cat(format(Sys.time()),stage,message,'\n'); flush.console()
   write_json(list(stage=stage,message=message,updated_at=format(Sys.time(),tz='UTC',usetz=TRUE)),file.path(dest,'native/measurement_progress.json'),auto_unbox=TRUE,pretty=TRUE)
   if(exists('clauder_progress',mode='function',inherits=TRUE)) clauder_progress(stage,message)
 }
 savecsv <- function(x,name) {stopifnot(nrow(x)>0L);write.csv(x,file.path(dest,'summaries',name),row.names=FALSE,na='',fileEncoding='UTF-8')}
 stats <- function(x) {x<-as.numeric(x); n<-sum(is.finite(x));c(n=n,mean=if(n)mean(x,na.rm=TRUE) else NA,sd=if(n>1)sd(x,na.rm=TRUE) else NA)}
 dpath<-file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds')
 d<-readRDS(dpath); stopifnot(nrow(d)==3274L,!anyDuplicated(d$pid))
 first<-fromJSON(file.path(q,'cesd2012_scoring.json'),simplifyVector=FALSE)
 follow<-fromJSON(file.path(q,'followup_item_scoring.json'),simplifyVector=FALSE)
 ys<-c(2012,2016,2018,2020,2022); ces<-paste0('ces8',substr(ys,3,4))
 groups<-list(analysis_all=rep(TRUE,nrow(d)),observed_2012_2016=!is.na(d$ces812)&!is.na(d$ces816),observed_all_five=complete.cases(d[,ces]))
 data8<-data20<-matrix(NA_real_,nrow(d),5,dimnames=list(NULL,as.character(ys)))
 t3<-t4<-measurement<-source_rows<-list(); t2<-NULL
 for(j in seq_along(ys)) {
   y<-ys[j]; step(paste0('read_',y),paste('选择性读取',y,'题目和官方得分，生成汇总'))
   record<-if(y==2012)first else follow[[as.character(y)]]
   src<-if(y==2012)record$inputs$raw else record$source
   items<-names(record$item_labels)
   meta<-read_dta(src,n_max=0)
   twenty<-if(y==2012)paste0('qq601',1:20) else if(y==2016)paste0('pn4',sprintf('%02d',1:20)) else character()
   wanted<-unique(c('pid',items,twenty,intersect(c('cesd20sc','cesd20','cesd8','cfps_age','self_iwmode'),names(meta))))
   stopifnot(all(wanted %in% names(meta)))
   raw<-read_dta(src,col_select=tidyselect::all_of(wanted))
   stopifnot(!anyDuplicated(raw$pid)); idx<-match(d$pid,raw$pid)
   m<-as.matrix(as.data.frame(lapply(raw[items],as.numeric))); m[!m %in% 1:4]<-NA_real_
   # 各年两道积极题在共同8题中的位置均为4和6，由变量字典核验。
   scored<-m; scored[,c(4,6)]<-5-scored[,c(4,6)]
   s8<-rowSums(scored); s024<-rowSums(scored-1)
   data8[,j]<-s8[idx]
   original<-as.numeric(d[[ces[j]]]); reconstructed<-data8[,j]
   both<-!is.na(original)&!is.na(reconstructed)
   t4[[j]]<-data.frame(year=y,n_analysis=nrow(d),n_complete=sum(both),raw_to_candidate_mismatch=sum(abs(original[both]-reconstructed[both])>1e-8),missingness_mismatch=sum(xor(is.na(original),is.na(reconstructed))),nonconstant_shift_count=sum(abs((s8-s024)-8)>1e-8,na.rm=TRUE),shift_scope='all_raw_complete_eight_items')
   stopifnot(t4[[j]]$raw_to_candidate_mismatch==0L,t4[[j]]$missingness_mismatch==0L,t4[[j]]$nonconstant_shift_count==0L)
   if(y==2012) {
     all20<-as.matrix(as.data.frame(lapply(raw[twenty],as.numeric))); all20[!all20 %in% 1:4]<-NA_real_
     all20[,c(4,8,12,16)]<-5-all20[,c(4,8,12,16)]
     data20[,j]<-rowSums(all20-1)[idx]; scale20<-'actual_20_items_0_60'
   } else if('cesd20sc' %in% names(raw)) {
     published<-as.numeric(raw$cesd20sc)
     stopifnot(all(published[published>=0 & !is.na(published)]>=20),all(published[published>=0 & !is.na(published)]<=80))
     s20<-published; s20[s20<0]<-NA_real_;s20<-s20-20
     data20[,j]<-s20[idx]; scale20<-'official_cesd20sc_20_80_minus20_to_0_60'
     if(y==2016) {
       a20<-as.matrix(as.data.frame(lapply(raw[twenty],as.numeric)));a20[!a20 %in% 1:4]<-NA_real_;a20[,c(4,8,12,16)]<-5-a20[,c(4,8,12,16)]
       total20<-rowSums(a20); ok20<-!is.na(total20)&!is.na(s20)
       stopifnot(sum(ok20)>0,all(abs(total20[ok20]-20-s20[ok20])<1e-8))
       write_json(list(complete_long_n=sum(ok20),exact_match_n=sum(abs(total20[ok20]-20-s20[ok20])<1e-8),published_range=range(published[published>=0],na.rm=TRUE),transformation='published CESD20sc minus 20; actual 2012 total uses item scores minus 1',passed=TRUE),file.path(dest,'summaries/CESD20_scale_validation.json'),auto_unbox=TRUE,pretty=TRUE)
     }
   } else {scale20<-'official_cesd20sc_not_available'}
   for(k in seq_along(items)) {
     valid<-complete.cases(scored[idx,,drop=FALSE])
     t3[[length(t3)+1L]]<-data.frame(year=y,item=items[k],label=record$item_labels[[items[k]]]$label,positive_reverse=k %in% c(4,6),n_eight_complete=sum(valid),mean_original=mean(m[idx,k][valid]),mean_scored=mean(scored[idx,k][valid]),coding='original 1:4; positive items 5-x; incomplete sums missing')
     measurement[[length(measurement)+1L]]<-data.frame(year=y,item=items[k],label=record$item_labels[[items[k]]]$label,reverse=k %in% c(4,6),valid_raw_codes='1,2,3,4',special_missing='all values outside 1:4',sum_rule='all 8 items required',scale='8-32',official20_source=scale20,source=src)
   }
   if(y==2016) {
     extra<-setdiff(twenty,items); e<-as.matrix(as.data.frame(lapply(raw[extra],as.numeric)))
     long<-rowSums(matrix(e %in% 1:4,nrow=nrow(e)))>0
     short<-rowSums(e == -8,na.rm=TRUE)==length(extra)
     version<-ifelse(long,'long_inferred',ifelse(short,'short_inferred','unclassified'))
     eligible<-!is.na(raw$cfps_age)&raw$cfps_age>=60&!is.na(raw$self_iwmode)&raw$self_iwmode==1
     scope<-list(all_2016_face_age60=eligible,analysis_2016_face_age60=eligible&raw$pid %in% d$pid)
     t2<-do.call(rbind,lapply(names(scope),function(g)do.call(rbind,lapply(c('long_inferred','short_inferred','unclassified'),function(v){z<-scope[[g]]&version==v; s<-stats(s8[z]);data.frame(sample=g,version=v,n_eligible=sum(z),n_score=s['n'],mean=s['mean'],sd=s['sd'],classification='NON_OFFICIAL: any extra item valid = long; all extra items -8 = short; otherwise unknown')}))))
     write_json(list(official_assignment_flag_found=FALSE,comparison='descriptive_association_not_randomized_assignment_test',rule='12 non-common items; partial response can affect inferred groups',self_iwmode_face=1,score_requires_all8=TRUE),file.path(dest,'summaries/T2_classification.json'),pretty=TRUE,auto_unbox=TRUE)
   }
   source_rows[[j]]<-data.frame(year=y,source=src,source_bytes=file.info(src)$size,source_md5_prior=if(y==2012)unlist(first$inputs$md5)[1] else record$source_md5,selected_columns=paste(wanted,collapse=';'),official20_source=scale20)
   rm(raw,meta,m,scored); invisible(gc(FALSE))
 }
 step('assemble_summaries','五期题目核验完成，汇总样本窗口和关系分布')
 rows<-list()
 for(g in names(groups))for(j in seq_along(ys))for(scale in c('CESD8_corrected','CESD20_comparable')) {
   z<-if(scale=='CESD8_corrected')data8[,j] else data20[,j]; s<-stats(z[groups[[g]]]); rows[[length(rows)+1L]]<-data.frame(sample=g,year=ys[j],scale=scale,n_group=sum(groups[[g]]),n=s['n'],mean=s['mean'],sd=s['sd'])
 }
 savecsv(do.call(rbind,rows),'T1_wave_scale_sample.csv');savecsv(t2,'T2_2016_form_comparison.csv');savecsv(do.call(rbind,t3),'T3_item_means.csv');savecsv(do.call(rbind,t4),'T4_scale_identity.csv');savecsv(do.call(rbind,measurement),'measurement_audit.csv');savecsv(do.call(rbind,source_rows),'raw_source_manifest.csv')
 vars<-c(SD='wfd_s12',Gender='wfd_d12',Oldest='wfd_d112',FirstSon='wfd_d412')
 stopifnot(all(vars %in% names(d)))
 t5<-do.call(rbind,lapply(names(vars),function(label){x<-as.numeric(d[[vars[label]]]);z<-x[is.finite(x)];s<-stats(z);qs<-quantile(z,c(.25,.5,.75));data.frame(indicator=label,variable=vars[label],n=s['n'],mean=s['mean'],sd=s['sd'],q25=qs[1],median=qs[2],q75=qs[3],negative=mean(z<0),zero=mean(z==0),positive=mean(z>0),scope='own observed baseline indicator within original 3274 cohort')}))
 savecsv(t5,'T5_baseline_relationship.csv')
 nobs<-rowSums(!is.na(data8)); t7<-as.data.frame(table(factor(nobs,levels=0:5)));names(t7)<-c('observed_waves','n');savecsv(t7,'T7_observed_waves.csv')
 patterns<-as.data.frame(table(apply(!is.na(data8),1,paste0,collapse='')));names(patterns)<-c('pattern_2012_2016_2018_2020_2022','n');savecsv(patterns,'T7_missing_patterns.csv')
 # 个体对应只保存在本机 analysis 目录，审计包明确不包含。
 saveRDS(list(pid=d$pid,fid=d$fid,cesd8=data8,cesd20=data20,groups=groups),file.path(dest,'analysis/local_measurement_values.rds'))
 checks<-data.frame(check=c('cohort_3274','five_wave_scoring','five_wave_missingness','constant_shift_all_raw','T1_30_rows','T3_40_rows','T7_count'),passed=c(nrow(d)==3274,all(do.call(rbind,t4)$raw_to_candidate_mismatch==0),all(do.call(rbind,t4)$missingness_mismatch==0),all(do.call(rbind,t4)$nonconstant_shift_count==0),length(rows)==30,length(t3)==40,sum(t7$n)==3274))
 stopifnot(all(checks$passed));savecsv(checks,'measurement_validation.csv')
 write_json(list(source_candidate=dpath,source_candidate_sha256=digest(dpath,algo='sha256',file=TRUE),N=nrow(d),new_estimations=0,completed=c('T1','T2_nonofficial_flag','T3','T4','T5','T7_observed_waves'),remaining='T6 factor scores and T7 death/attrition source summary'),file.path(dest,'native/measurement_receipt.json'),auto_unbox=TRUE,pretty=TRUE)
 print(checks); print(sessionInfo());step('measurement_complete','T1–T5与T7观察模式已生成；原始文件未修改')
})
