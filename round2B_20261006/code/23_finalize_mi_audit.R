# 记录完整工程批次的验收，不替代父模型或潜交互的统计验收。
local({
 library(jsonlite);library(digest)
 r<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 v<-read.csv(file.path(r,'audit/mi_member_validation.csv'))
 m<-fromJSON(file.path(r,'audit/mi_member_manifest.json'))
 z<-fromJSON(file.path(r,'audit/mi_chain_review_iteration_30/receipt.json'))
 stopifnot(nrow(v)==4300L,all(v$passed),identical(sort(unique(v$imputation)),1:10),
   nrow(m)==10L,all(m$passed),z$iteration==30L,z$m==10L,
   isTRUE(z$methods_unchanged),z$predictor_changes==0L,z$logged_events==0L)
 for(k in 1:10)stopifnot(digest(file=file.path(r,'private/mi10',sprintf('member_%02d.rds',k)),algo='sha256')==m$sha256[k])
 cv<-read.csv(file.path(r,'audit/mi_convergence.csv'))
 final<-cv[cv$.it==30&is.finite(cv$psrf),]
 stopifnot(nrow(final)==10L)
 out<-list(status='ENGINEERING_DATA_AND_CHAIN_REVIEW_COMPLETE_READY_FOR_PARENT',
   m=10,iterations=30,data_checks=nrow(v),passed=sum(v$passed),
   observed_values_preserved=TRUE,household_shared_values_consistent=TRUE,
   target_missing_completed=TRUE,frozen_longitudinal_and_structural_masks_preserved=TRUE,
   requested_methods_and_predictors_unchanged=TRUE,logged_events=0,
   final_psrf_range=range(final$psrf),
   visual_review='Final large-target mean/variance traces inspected; no persistent common drift or separated chains observed. Occasional variance spikes retained, not trimmed. Small targets are suppressed publicly and evaluated with numerical diagnostics and member validation.',
   limits='Engineering acceptance does not prove MAR, model correctness, congeniality with latent interactions, or adequacy of m for every estimand. Parent legality and pooled Monte Carlo uncertainty remain separate gates.',
   checkpoint_sha256=digest(file=file.path(r,'private/mi_checkpoint.rds'),algo='sha256'),
   inputs_sha256=digest(file=file.path(r,'private/mi_actual_inputs.rds'),algo='sha256'),
   production_script_sha256=digest(file=file.path(r,'code/04_hierarchical_mi.R'),algo='sha256'),
   validator_sha256=digest(file=file.path(r,'code/mi_validation.R'),algo='sha256'))
 write_json(out,file.path(r,'audit/mi_engineering_acceptance.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 cat(out$status,'\n')
})
