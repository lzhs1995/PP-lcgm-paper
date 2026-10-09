# 仅绑定先前逐题审计的信度结果与当前队列；不重做五期计分，不修改任何数据。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/01_tools.R',local=TRUE)
q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
oldfile<-file.path(q,'cesd2012_corrected_only_candidate_NOT_RELEASED.rds')
old<-readRDS(oldfile);current<-readRDS(file.path(R2B,'private/baseline_preMI.rds'))$data
stopifnot(!anyDuplicated(old$pid),!anyDuplicated(current$pid),setequal(old$pid,current$pid))
old<-old[match(current$pid,old$pid),];stopifnot(identical(as.numeric(old$pid),as.numeric(current$pid)))
summary<-fromJSON(file.path(q,'cesd_five_wave_audit_summary.json'));base<-fromJSON(file.path(q,'cesd2012_alpha.json'))
follow<-fromJSON(file.path(q,'followup_item_scoring.json'),simplifyVector=FALSE)
checks<-list();tab<-list()
for(k in seq_along(R2D_YEARS)){
 w<-R2D_YEARS[k];v<-paste0('ces8',w);a<-as.numeric(old[[v]]);b<-as.numeric(current[[v]])
 same_missing<-identical(is.na(a),is.na(b));same_value<-all(a[is.finite(a)]==b[is.finite(a)])
 stopifnot(same_missing,same_value,sum(is.finite(b))==summary$N[k])
 alpha<-if(w==12)base$corrected_alpha else follow[[as.character(2000+w)]]$alpha_final_complete
 stopifnot(abs(alpha-summary$alpha[k])<1e-12)
 checks[[k]]<-data.frame(year=2000+w,N=sum(is.finite(b)),same_missing=same_missing,same_values=same_value)
 tab[[k]]<-data.frame(year=2000+w,N=sum(is.finite(b)),alpha=alpha,source='Prior corrected-item audit, exact current cohort/score binding',new_item_recomputation=FALSE)
}
dest<-file.path(ROOT,'provenance_measurement');dir.create(dest,showWarnings=FALSE)
for(nm in c('cesd2012_alpha.json','followup_item_scoring.json','cesd_five_wave_audit_summary.json')){
 src<-file.path(q,nm);to<-file.path(dest,nm);if(!file.exists(to))stopifnot(file.copy(src,to));stopifnot(hashf(src)==hashf(to))
}
write.csv(do.call(rbind,tab),file.path(ROOT,'audit/CESD_reliability_bound.csv'),row.names=FALSE)
write.csv(do.call(rbind,checks),file.path(ROOT,'audit/CESD_score_binding.csv'),row.names=FALSE)
wj(list(status='PRIOR_ITEM_RELIABILITY_BOUND_TO_CURRENT_SCORES',old_candidate_sha256=hashf(oldfile),
 current_baseline_sha256=hashf(file.path(R2B,'private/baseline_preMI.rds')),alpha_source_sha256=hashf(file.path(q,'cesd_five_wave_audit_summary.json')),
 no_new_item_reconstruction=TRUE,no_new_models=TRUE,
 note='The historical scientific_release=false referred to unresolved analyses at that time; reuse here is limited to item scoring and reliability, never to historical model estimates.'),file.path(ROOT,'audit/CESD_reliability_binding.json'))
cat('CESD RELIABILITY BINDING PASS: five waves, identical cohort and complete-score masks; 0 new fits\n')
