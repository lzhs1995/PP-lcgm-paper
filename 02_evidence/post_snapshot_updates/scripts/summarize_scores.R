# 原生 MplusAutomation 读回已存在的因子得分；不重新估计第一阶段。
local({
 library(MplusAutomation);library(jsonlite);library(digest)
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'
 d<-readRDS(file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds'))
 source<-fromJSON(file.path(q,'exact_score_source_audit.json'),simplifyVector=FALSE)$sources
 models<-c('pp_lgca_type12_r_step1.out','pp_lgca_type13_r_step1.out','pp_lgca_type14_r_step1.out','pp_lgca_type14_4_r_step1.out')
 factors<-c('I2','I3','I4','I4');variables<-c('wfd_s12','wfd_d12','wfd_d112','wfd_d412');indicator<-c('SD','Gender','Oldest','FirstSon')
 rows<-cross<-quality<-list();all_scores<-list()
 emit<-function(s,model,label,factor,variable,sourcepath,provenance){
   names(s)<-toupper(names(s));stopifnot(all(c('PID',factor)%in%names(s)),!anyDuplicated(s$PID))
   z<-as.numeric(s[[factor]]);keep<-is.finite(z);cut<-median(z[keep]);g<-ifelse(keep,ifelse(z<=cut,'low','high'),NA_character_)
   rows[[length(rows)+1L]]<<-data.frame(indicator=label,model=model,version=provenance,factor=factor,n=sum(keep),median=cut,equal_cut=sum(z[keep]==cut),low=sum(g=='low',na.rm=TRUE),high=sum(g=='high',na.rm=TRUE),source=sourcepath,source_sha256=digest(sourcepath,algo='sha256',file=TRUE),rule='<= median is low; > median is high')
   idx<-match(s$PID,d$pid);stopifnot(!anyNA(idx));b<-as.numeric(d[[variable]][idx]);category<-ifelse(is.na(b),'missing',ifelse(b<0,'negative',ifelse(b==0,'zero','positive')))
   tab<-as.data.frame(table(observed_category=category,score_group=g,useNA='ifany'));tab$indicator<-label;tab$version<-provenance;cross[[length(cross)+1L]]<<-tab
   secol<-paste0(factor,'_SE');se<-if(secol %in% names(s))as.numeric(s[[secol]]) else rep(NA_real_,nrow(s))
   quality[[length(quality)+1L]]<<-data.frame(indicator=label,version=provenance,n_se=sum(is.finite(se)),median_se=if(any(is.finite(se)))median(se,na.rm=TRUE) else NA,score_sd=sd(z,na.rm=TRUE),uncertainty='SE describes score uncertainty; no claim of unbiased interaction')
   all_scores[[paste(label,provenance,sep='_')]]<<-data.frame(pid=s$PID,score=z,score_se=se,group=g)
 }
 for(i in seq_along(models)){
   choices<-Filter(function(x)basename(x$source_output)==models[i],source);stopifnot(length(choices)==1L)
   p<-choices[[1]]$source_output;stopifnot(digest(p,algo='sha256',file=TRUE)==choices[[1]]$output_sha256)
   a<-readModels(p,what='savedata',quiet=TRUE);stopifnot(is.data.frame(a$savedata),nrow(a$savedata)>0)
   emit(a$savedata,models[i],indicator[i],factors[i],variables[i],p,'historical_v42_source')
 }
 corrected<-fromJSON(file.path(q,'accepted_rebuilt_score_sources.json'),simplifyVector=FALSE)$accepted_sources
 for(i in c(3L,4L)){
   choices<-Filter(function(x)x$source_identity==models[i],corrected);stopifnot(length(choices)==1L);x<-choices[[1]]
   stopifnot(digest(x$output,algo='sha256',file=TRUE)==x$candidate_sha256)
   s<-read.csv(x$output,check.names=FALSE);emit(s,models[i],indicator[i],factors[i],variables[i],x$source,'corrected_score_candidate_only')
 }
 write.csv(do.call(rbind,rows),file.path(dest,'summaries/T6_score_cutpoints.csv'),row.names=FALSE,fileEncoding='UTF-8')
 write.csv(do.call(rbind,cross),file.path(dest,'summaries/T6_observed_score_crosstabs.csv'),row.names=FALSE,fileEncoding='UTF-8')
 write.csv(do.call(rbind,quality),file.path(dest,'summaries/T6_score_precision.csv'),row.names=FALSE,fileEncoding='UTF-8')
 saveRDS(all_scores,file.path(dest,'analysis/local_factor_scores.rds'))
 mortality<-fromJSON(file.path(q,'mortality_roster_linkage_20261002/mortality_linkage_decision.json'),simplifyVector=FALSE)
 stopifnot(mortality$analysis_sha256==digest(file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds'),algo='sha256',file=TRUE))
 counts<-data.frame(measure=c('cohort','reported_dead_any','unique_known_death_year','death_year_conflicts','alive_after_dead'),n=c(mortality$analysis_N,mortality$reported_dead_any,mortality$unique_known_death_year,mortality$conflicting_death_years,mortality$alive_after_dead_report),status='REUSED_HASH_BOUND_MORTALITY_LINKAGE_NOT_RANDOM_ATTRITION')
 write.csv(counts,file.path(dest,'summaries/T7_mortality_counts.csv'),row.names=FALSE,fileEncoding='UTF-8')
 write_json(list(new_mplus=0,score_sources=length(rows),historical_and_corrected_separated=TRUE,mortality_limitations=mortality$limitations),file.path(dest,'native/score_summary_receipt.json'),auto_unbox=TRUE,pretty=TRUE)
 writeLines(c(capture.output(do.call(rbind,rows)[,c('indicator','version','n','median','equal_cut','low','high')]),capture.output(sessionInfo())),file.path(dest,'native/score_summary.log'))
 print(do.call(rbind,rows)[,c('indicator','version','n','median','equal_cut','low','high')])
})
