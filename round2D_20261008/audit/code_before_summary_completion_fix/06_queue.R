# 预登记队列；只依据合法性/数值稳定性采用，不根据估计符号或P值续跑。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
stopifnot(isTRUE(fromJSON(file.path(ROOT,'tests/synthetic_summary.json'))$interface_passed))
stopifnot(isTRUE(fromJSON(file.path(ROOT,'audit/data_preparation_PASS.json'))$passed))
repair_available<-function(){r<-if(file.exists(REG))read.csv(REG)else data.frame();sum(r$category=='REPAIR')<contract()$call_caps$REPAIR}
settings_for<-function(spec,high=FALSE) {
 syn<-fromJSON(file.path(ROOT,'tests/synthetic_summary.json'),simplifyVector=FALSE)$receipts
 type<-if(spec=='D1')'D1' else if(grepl('^H4',spec))'H4_EDU' else 'E1'
 dim<-syn[[type]]$integration_dimensions
 if(is.null(dim)||!is.finite(dim))stop('Integration dimension not established for ',type)
 mc<-dim>2
 list(method=if(mc)'montecarlo' else 'quadrature',points=if(mc)if(high)10000L else 5000L else if(high)20L else 15L,
      seed=if(high)26100802L else 26100801L)
}
schema_failure<-function(a)!is.null(a)&&a$receipt$status%in%c('INPUT_REJECTED','EXTRACTION_FAILED','KEY_PATH_ERROR','PRINTED_MISMATCH')
ensure_interface<-function(a){if(schema_failure(a))stop('MODEL_INTERFACE_ERROR: ',a$receipt$id,' ',a$receipt$status);a}
repair_member<-function(a,z,spec,k,settings,category,sample='Z0') {
 if(!is.null(a)&&isTRUE(a$receipt$usable))return(a)
 if(!repair_available()||!file.exists(file.path(a$dest,'key_paths.csv')))return(a)
 ensure_interface(run_one(z,spec,k,'repair_start','REPAIR',sample,settings,start_from=a$dest))
}
family_path<-function(z,spec)file.path(ROOT,'results',paste0(z,'_',spec,'_family.json'))
save_family<-function(z,spec,members,numeric=NULL,reason=NULL) {
 si<-spec_info(z,spec);ok<-family_gate(members,numeric,si$kind!='linear')
 attempts<-lapply(seq_len(10),function(k){a<-if(length(members)>=k)members[[k]]else NULL;
   if(is.null(a))list(member=k,status='NOT_RUN',attempt=NA,usable=FALSE)else c(a$receipt[c('member','status','attempt','usable')],list(output_sha256=a$receipt$output_sha256))})
 rr<-list(z=z,spec=spec,eligible=ok,members=attempts,numeric=numeric,reason=reason,updated_at=as.character(Sys.time()),
          inference='Fixed model/current MI assumptions; MI01 numerical checks only; no failed-member deletion')
 wj(rr,family_path(z,spec));rr
}
run_linear_family<-function(z,spec,category='TARGET') {
 fp<-family_path(z,spec);if(file.exists(fp))return(fromJSON(fp,simplifyVector=FALSE))
 ms<-list();set<-list(method='none',points=0,seed=26100801)
 for(k in 1:10){a<-ensure_interface(run_one(z,spec,k,category=category,settings=set));
   if(!isTRUE(a$receipt$usable))a<-repair_member(a,z,spec,k,set,category)
   ms[[k]]<-a
   if(!isTRUE(a$receipt$usable))return(save_family(z,spec,ms,reason=paste('Member',k,'inadmissible after limited starting-value check; later members not estimated')))
 }
 save_family(z,spec,ms)
}
run_lms_family<-function(z,spec,category='TARGET') {
 fp<-family_path(z,spec);if(file.exists(fp))return(fromJSON(fp,simplifyVector=FALSE))
 ini<-settings_for(spec,FALSE);hi<-settings_for(spec,TRUE);checkcat<-if(category=='FALLBACK')'FALLBACK' else 'CHECK'
 a<-ensure_interface(run_one(z,spec,1,category=category,settings=ini))
 if(!isTRUE(a$receipt$usable))a<-repair_member(a,z,spec,1,ini,category)
 if(!isTRUE(a$receipt$usable))return(save_family(z,spec,list(a),reason='Pilot model inadmissible; no slope or factor-significance gate applied'))
 # 高精度候选成为正式采用的MI01，而非旧base；所有比较都明确绑定。
 h<-ensure_interface(run_one(z,spec,1,'precision',checkcat,settings=hi,warm_from=a$dest));ig<-compare_numeric(a,h,'integration')
 if(!isTRUE(ig$passed)&&repair_available()){
   hi$points<-if(hi$method=='montecarlo')20000L else 30L
   prior<-h;h<-ensure_interface(run_one(z,spec,1,'repair_precision','REPAIR',settings=hi,warm_from=if(isTRUE(prior$receipt$usable))prior$dest else a$dest));ig<-compare_numeric(prior,h,'integration')
 }
 if(!isTRUE(ig$passed))return(save_family(z,spec,list(h),list(integration=ig,start=list(passed=FALSE)),reason='Integration comparison failed under preset budget'))
 s<-ensure_interface(run_one(z,spec,1,'start_check',checkcat,settings=hi,start_from=h$dest,warm_from=h$dest));sg<-compare_numeric(h,s,'start')
 if(!isTRUE(sg$passed))return(save_family(z,spec,list(h),list(integration=ig,start=sg),reason='Alternative starting values not stable; no pooling'))
 num<-list(integration=ig,start=sg,adopted_settings=hi,adopted_MI01_attempt=h$receipt$attempt,scope='MI01 only')
 ms<-list(h)
 for(k in 2:10){a<-ensure_interface(run_one(z,spec,k,category=category,settings=hi,warm_from=h$dest));
   if(!isTRUE(a$receipt$usable))a<-repair_member(a,z,spec,k,hi,category)
   ms[[k]]<-a
   if(!isTRUE(a$receipt$usable))return(save_family(z,spec,ms,num,paste('Member',k,'inadmissible; family not pooled; later members not run')))
 }
 save_family(z,spec,ms,num)
}
progress('core_queue','SD latent D0/D1 first; main path significance never used as admission')
for(z in names(R2D_Z)){
 run_linear_family(z,'D0');run_lms_family(z,'D1')
}
progress('observed_SD','Observed2012 SD has a separate estimand and supports the resource-group tests')
run_linear_family('SD','E0');run_lms_family('SD','E1')
for(g in names(R2D_G))run_lms_family('SD',paste0('H4_',g))
for(z in setdiff(names(R2D_Z),'SD')){
 d<-fromJSON(family_path(z,'D1'))
 if(!isTRUE(d$eligible)){
   wj(list(z=z,trigger=d$reason,old_estimand='latent IZ',new_estimand='observed2012 Z0',same_baseline_sample=TRUE,
      reason='Limited latent branch did not pass; not selected on significance'),file.path(ROOT,'audit',paste0(z,'_estimand_change.json')))
   run_linear_family(z,'E0','FALLBACK');run_lms_family(z,'E1','FALLBACK')
 }
}
set<-settings_for('D1',TRUE)
cc<-ensure_interface(run_one('SD','D1',1,attempt='completecase',sample='CC',settings=set))
wj(list(receipt=cc$receipt,role='Complete observed covariates diagnostic only; no MI compatibility claim or pooling; no independent numerical check'),file.path(ROOT,'results/SD_completecase_diagnostic.json'))
rr<-list.files(file.path(ROOT,'results'),pattern='_family.json$',full.names=TRUE)
fs<-lapply(rr,fromJSON);pass<-sum(vapply(fs,function(x)isTRUE(x$eligible),logical(1)))
wj(list(status='QUEUE_TERMINAL',families=length(fs),eligible=pass,call_count=nrow(read.csv(REG)),created=as.character(Sys.time()),
        note='Terminal execution does not mean all seven scientific issues resolved'),file.path(ROOT,'runtime/queue_terminal.json'))
progress('queue_terminal',paste(length(fs),'families adjudicated,',pass,'eligible; no p-based stopping'))
