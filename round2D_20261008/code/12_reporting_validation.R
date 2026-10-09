# 本轮汇总纠错的针对性验证；不提交Mplus、不改活动worker、不覆写既有估计。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
tests<-list()
check<-function(name,x){ok<-isTRUE(x);tests[[length(tests)+1]]<<-data.frame(test=name,passed=ok);if(!ok)stop('Reporting validation failed: ',name)}
for(f in c('01_tools.R','03_engine.R','06_queue.R','07_pool.R')){
  parsed<-parse(file.path(ROOT,'code',f));check(paste0('parse_',f),length(parsed)>0)
}
check('SD_missing_mandatory_is_not_optional',missing_family_status('SD','E1',FALSE,'TOTAL_ESTIMATION_BUDGET')[['status']]=='NOT_RUN_BUDGET')
check('untriggered_fallback_requires_passed_latent',missing_family_status('OLDEST','E1',TRUE,'COMPLETED_REGISTERED_QUEUE')[['status']]=='NOT_RUN_NOT_TRIGGERED')
check('triggered_fallback_stopped_by_budget',missing_family_status('OLDEST','E1',FALSE,'TOTAL_ESTIMATION_BUDGET')[['status']]=='NOT_RUN_BUDGET')
check('partial_family_is_not_unexecuted',missing_family_status('SD','D1',FALSE,'TOTAL_ESTIMATION_BUDGET',2)[['status']]=='INCOMPLETE_BUDGET')
check('resource_stop_is_separate',missing_family_status('SD','H4_EDU',FALSE,'RESOURCE_WAIT_LIMIT')[['status']]=='NOT_RUN_RESOURCE_LIMIT')
check('missing_mandatory_on_full_completion_is_error',missing_family_status('SD','D1',FALSE,'COMPLETED_REGISTERED_QUEUE')[['status']]=='NOT_RUN_UNEXPECTED')
caught<-tryCatch(execution_limit('TOTAL_ESTIMATION_BUDGET','synthetic validation only'),r2d_execution_limit=function(e)e)
check('budget_condition_class_and_reason',inherits(caught,'r2d_execution_limit')&&caught$reason=='TOTAL_ESTIMATION_BUDGET')
adjusted<-p.adjust(c(.04,.005,NA),'holm',n=4)
check('Holm_keeps_declared_family_and_missing',isTRUE(all.equal(adjusted,c(.12,.02,NA))))
sd<-read.csv(file.path(ROOT,'audit/moderator_descriptives.csv'));sd<-sd[sd$z=='SD'&sd$year==2012,]
check('minus_one_SD_is_observed_extrapolation',nrow(sd)==1&&-1<sd$min&&abs(sd$min+sd$ratio_mean/sd$ratio_sd)<1e-10)
for(sp in c('D1','E1','H4_EDU')){
  d<-model_dir('SD',sp,0,'synthetic','SYNTHETIC');sv<-svalues_block(readLines(file.path(d,'model.out'),warn=FALSE))
  si<-spec_info('SD',sp,ctrl='c1-c3',sample='SYNTHETIC')
  check(paste0('SVALUES_present_',sp),length(sv)>0&&all(grepl(';\\s*$',sv)))
  check(paste0('SVALUES_key_labels_',sp),all(vapply(si$key$label,function(l)sum(grepl(paste0('\\(',l,'\\);$'),sv))==1,logical(1))))
}
write.csv(do.call(rbind,tests),file.path(ROOT,'tests/reporting_R_validation.csv'),row.names=FALSE)
wj(list(passed=TRUE,tests=length(tests),created=as.character(Sys.time()),Mplus_calls=0L,
        note='Reporting and SVALUES text checks; not real-data fit or numeric stability validation'),file.path(ROOT,'tests/reporting_R_validation.json'))
cat('REPORTING_R_VALIDATION:',length(tests),'PASS; zero Mplus calls\n')
