# Round2F批准方案：两个积分节点、两个合法来源；统一采用30点。决策与P值无关。
source(file.path(Sys.getenv('R2F_ROOT'),'code/r2f_local.R'),local=globalenv())
SEL2F <- file.path(ROOT,'runtime/selection_2f.json')
save_sel <- function(S) wj(S,SEL2F)
e0_2e <- function(k) r2e_model(sprintf('CFPS_SD_E0_%02d_base',k))
ll_gap_ok <- function(r) !is.null(r$exact_LL_difference) && is.finite(r$exact_LL_difference) && abs(r$exact_LL_difference)<=C2F$exact_ll$model_tolerance && isTRUE(r$exact_LL_n_match)
pilot_2f <- function(S,step,sp) {
 P<-S[[step]];if(is.null(P))P<-list(runs=list())
 for(q in c(20L,30L))for(origin in c('a','b')) {
  nm<-paste0('q',q,origin)
  if(is.null(P$runs[[nm]])) {
   src<-if(origin=='a')r2e_model(C2F$round2E_inputs$SD_E1B_01$id) else e0_2e(1)
   ov<-if(sp=='E1'&&origin=='a')C2F$allowed_start_override else NULL
   P$runs[[nm]]<-run_r2f(sp,1L,paste0(step,'_',nm),'NUMERIC',points=q,conv='tight',source_dir=src,start_override=ov)
   S[[step]]<-P;save_sel(S)
  }
 }
 P$a<-P$runs$q30a;P$b<-P$runs$q30b
 P$start_check<-numeric_compare_2f(P$a,P$b,'start')
 P$integration_a<-numeric_compare_2f(P$runs$q20a,P$a,'integration',diagnostic=TRUE)
 P$integration_b<-numeric_compare_2f(P$runs$q20b,P$b,'integration',diagnostic=TRUE)
 ig<-isTRUE(P$integration_a$passed)&&isTRUE(P$integration_b$passed)
 P$integration_check<-list(passed=ig,outcome=if(ig)'AGREE' else 'NOT_REPLICATED')
 P$passed<-usable(P$a)&&usable(P$b)&&isTRUE(P$start_check$passed)&&ig&&ll_gap_ok(P$a)&&ll_gap_ok(P$b)
 best<-if(usable(P$a)&&(!usable(P$b)||P$a$LL>=P$b$LL))P$a else if(usable(P$b))P$b else NULL
 P$best<-if(is.null(best))NULL else best$id;P$best_dest<-if(is.null(best))NULL else best$dest;P$selected<-best
 S[[step]]<-P;save_sel(S);S
}
run_family<-function(S,fam,sp,mi01,conv='tight') {
 F<-S$families[[fam]]
 if(!is.null(F)&&F$status %in% c('COMPLETE_10_USABLE','MEMBER_FAILED','NOT_ESTIMATED_WITHIN_BUDGET'))return(S)
 if(is.null(F)) {
  b<-budget_r2f();B<-C2F$budget;projected<-9*B$family_projection_factor*mi01$seconds
  slots<-B$categories$TARGET-sum(vapply(b$rows,function(r)identical(r$category,'TARGET'),TRUE))
  F<-list(spec=sp,members=list(`1`=mi01),repairs=list(),status='RUNNING',projected_seconds=projected)
  if(projected>min(B$engine_seconds-b$engine_seconds,B$wall_seconds-b$wall_seconds)||slots<9L)F$status<-'NOT_ESTIMATED_WITHIN_BUDGET'
  S$families[[fam]]<-F;save_sel(S);if(F$status!='RUNNING')return(S)
 }
 for(k in 2:10) {
  kk<-as.character(k);if(usable(F$members[[kk]]))next
  r<-F$members[[kk]]
  if(is.null(r))r<-run_r2f(sp,k,'fam','TARGET',conv=conv,points=mi01$points,source_dir=mi01$dest)
  F$members[[kk]]<-r;S$families[[fam]]<-F;save_sel(S)
  if(!usable(r)&&!grepl('^NOT_RUN',r$status)) {
   rr<-F$repairs[[kk]];if(is.null(rr))rr<-run_r2f(sp,k,'famrep','REPAIR',conv=conv,points=mi01$points,source_dir=e0_2e(k))
   F$repairs[[kk]]<-rr;if(usable(rr))r<-rr
  }
  F$members[[kk]]<-r
  if(!usable(r))F$status<-if(grepl('^NOT_RUN',r$status))'NOT_ESTIMATED_WITHIN_BUDGET' else 'MEMBER_FAILED'
  S$families[[fam]]<-F;save_sel(S);if(F$status!='RUNNING')return(S)
 }
 stopifnot(family_valid_2f(F));F$status<-'COMPLETE_10_USABLE';S$families[[fam]]<-F;save_sel(S);S
}
run_queue_2f<-function(){
 stopifnot(isTRUE(rj(file.path(ROOT,'audit/P0_STATUS_2F.json'))$passed),isTRUE(rj(file.path(ROOT,'audit/SMOKE_2F.json'))$passed))
 S<-rj(SEL2F);if(is.null(S))S<-list(convergence='tight',families=list(),diagnostics=list())
 if(!is.null(S$terminal)&&S$terminal$status=='FINISHED')return(invisible(S))
 tryCatch({
  S<-pilot_2f(S,'F1','E1B');S<-pilot_2f(S,'F2','E1')
  f1<-isTRUE(S$F1$passed);f2<-isTRUE(S$F2$passed)
  S$decision<-if(f1&&f2)'A' else if(f2)'A1' else if(f1)'B' else 'C'
  S[['primary']]<-switch(S$decision,A='E1',A1='E1',B='E1B',C=NULL)
  S$primary_label<-switch(S$decision,A='Free E1 primary; E1B strong-constraint sensitivity',A1='Free E1 only; E1B numerically unqualified',B='SY@0 strong-constraint sensitivity only; no unconstrained moderation inference',C='No numerically qualified pilot; no MI family')
  save_sel(S);progress('decision_2f',S$decision)
  if(S$decision %in% c('A','A1'))S<-run_family(S,'E1','E1',S$F2$selected)
  if(S$decision %in% c('A','B'))S<-run_family(S,'E1B','E1B',S$F1$selected)
  pref<-if(S$decision %in% c('A','A1'))S$F2$selected else if(S$decision=='B')S$F1$selected else NULL
  D<-S$diagnostics;if(is.null(D$F5))D$F5<-list()
  for(v in unlist(C2F$sy_fixed_grid)){
   sp<-sprintf('E1F%03d',round(v*1000))
   if(is.null(D$F5[[sp]])){D$F5[[sp]]<-run_r2f(sp,1L,'F5','DIAG',conv='tight',points=30L,source_dir=r2e_model(C2F$round2E_inputs$SD_E1B_01$id));S$diagnostics<-D;save_sel(S)}
  }
  cc<-rj(file.path(ROOT,'audit/CC_SAMPLE_2F.json'));ccf<-file.path(ROOT,'private/SD/CC_member_01.dat')
  if(isTRUE(cc$passed)){
   if(is.null(D$F6$E0)){D$F6$E0<-run_r2f('E0',1L,'F6','DIAG',source_dir=e0_2e(1),source_data=ccf,data_tag='CC');S$diagnostics<-D;save_sel(S)}
   if(!is.null(pref)&&is.null(D$F6$E1x)){D$F6$E1x<-run_r2f(pref$spec,1L,'F6','DIAG',conv='tight',points=30L,source_dir=pref$dest,source_data=ccf,data_tag='CC');S$diagnostics<-D;save_sel(S)}
  }else D$F6<-list(status='NOT_RUN_CC_UNAVAILABLE')
  if(!is.null(pref)&&is.null(D$O1)){D$O1<-run_r2f(pref$spec,1L,'O1','DIAG',conv='tight',points=30L,source_dir=pref$dest,source_data=file.path(ROOT,'private/SD/Z0TOP99_member_01.dat'),data_tag='TOP99');S$diagnostics<-D;save_sel(S)}
  S$diagnostics<-D;S$terminal<-list(status='FINISHED',utc=format(Sys.time(),tz='UTC',usetz=TRUE))
 },error=function(e){S$terminal<<-list(status='STOPPED_WITH_REASON',reason=conditionMessage(e),utc=format(Sys.time(),tz='UTC',usetz=TRUE))})
 save_sel(S);progress('queue_terminal',S$terminal$status);invisible(S)
}
if(sys.nframe()==0L||identical(Sys.getenv('R2F_RUN_MAIN'),'1'))run_queue_2f()
