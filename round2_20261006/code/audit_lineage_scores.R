# 来源核查与得分SE恢复；不重估模型，不公开逐人数据。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2_20261006'
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 .libPaths(readRDS(file.path(dirname(q),'foreground_library_paths.rds')))
 library(MplusAutomation);library(jsonlite);library(digest);library(haven)
 plain<-function(z){if(inherits(z,'haven_labelled'))attributes(z)<-NULL;z}
 dfplain<-function(x)as.data.frame(lapply(x,plain),check.names=FALSE)
 rawd<-readRDS(file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds'))
 d<-dfplain(rawd)
 cov<-unlist(fromJSON('C:/Users/LZHS/pp_lgcm_review/20261005/analysis/sensitivity/manifest.json',simplifyVector=FALSE)$covariates)
 dict<-do.call(rbind,lapply(seq_along(cov),function(i){v<-cov[i];z<-d[[v]];lab<-attr(rawd[[v]],'label',exact=TRUE);vl<-attr(rawd[[v]],'labels',exact=TRUE);data.frame(mplus=paste0('c',i),variable=v,label=if(is.null(lab))'' else paste(lab,collapse=';'),value_labels=if(is.null(vl))'' else paste(names(vl),vl,sep='=',collapse=';'),missing_original=sum(is.na(z)),unique_observed=length(unique(z[!is.na(z)])),min=min(z,na.rm=TRUE),max=max(z,na.rm=TRUE),type=class(z)[1],time_review=if(v=='wave')'FOLLOWUP_COUNT_REQUIRES_INTERPRETATION' else 'BASELINE_NAME_VERIFY_SOURCE')}))
 stopifnot(nrow(dict)==26L,!anyDuplicated(dict$variable));write.csv(dict,file.path(root,'audit/covariates_26.csv'),row.names=FALSE)
 repair<-fromJSON(file.path(q,'cesd_repair_receipt.json'))
 old<-dfplain(read_dta(repair$source));idx<-match(d$pid,old$pid);stopifnot(!anyNA(idx));old<-old[idx,]
 rows<-list()
 for(v in c('ces812','ces816','ces818','ces820','ces822','ces8sd12','ces8sd16','ces8sd18','ces8sd20','ces8sd22')){
  a<-old[[v]];b<-d[[v]];ok<-is.finite(a)&is.finite(b)
  rows[[length(rows)+1L]]<-data.frame(variable=v,n=sum(ok),missing_difference=sum(is.na(a)!=is.na(b)),changed=sum(abs(a[ok]-b[ok])>1e-6),old_mean=mean(a,na.rm=TRUE),new_mean=mean(b,na.rm=TRUE),difference_mean=mean(b[ok]-a[ok]),difference_min=min(b[ok]-a[ok]),difference_max=max(b[ok]-a[ok]))
 }
 write.csv(do.call(rbind,rows),file.path(root,'audit/old_corrected_comparison.csv'),row.names=FALSE)
 # 用已保存数据检验X各期是否使用同一仿射变换；不把推定常数冒充源脚本。
 b<-coef(lm(d$wfdms12~d$wfd_m12));xr<-lapply(c(12,16,18,20,22),function(y){raw<-d[[paste0('wfd_m',y)]];z<-d[[paste0('wfdms',y)]];data.frame(year=2000+y,offset=b[1],multiplier=b[2],max_affine_error=max(abs(z-(b[1]+b[2]*raw)),na.rm=TRUE),missing_mismatch=sum(is.na(raw)!=is.na(z)))})
 write.csv(do.call(rbind,xr),file.path(root,'audit/x_scale_identity.csv'),row.names=FALSE)
 inp<-file.path(q,'mi_measurement_repair_v3_marriage_aligned/corrected_measurement_MI.inp');text<-paste(readLines(inp),collapse='\n');clean<-gsub('![^\n]*','',text)
 field<-function(n){r<-regmatches(clean,regexec(paste0('(?is)\\b',n,'\\s*=([^;]+);'),clean,perl=TRUE))[[1]];stopifnot(length(r)==2);strsplit(tolower(trimws(r[2])),'\\s+')[[1]]}
 nm<-field('names');used<-field('usevar');aux<-field('auxiliary')
 mp<-file.path(dirname(inp),'corrected_measurement_MI_input.dat');mi<-read.table(mp,col.names=nm,na.strings=c('.','*'),check.names=FALSE)
 ii<-match(d$pid,mi$pid);stopifnot(nrow(mi)==3274L,!anyNA(ii));mi<-mi[ii,]
 vars<-intersect(c('ces812','ces816','ces818','ces820','ces822','ces8sd12','ces8sd16','ces8sd18','ces8sd20','ces8sd22','wfd_m12','wfd_s12','wfd_d12','wfd_d112','marr12'),names(mi))
 check<-do.call(rbind,lapply(vars,function(v){data.frame(variable=v,role=if(v%in%used)'imputation_predictor' else if(v%in%aux)'saved_auxiliary' else 'other',missing_mismatch=sum(is.na(mi[[v]])!=is.na(d[[v]])),max_abs_difference=max(abs(mi[[v]]-d[[v]]),na.rm=TRUE))}))
 write.csv(check,file.path(root,'audit/mi_input_alignment.csv'),row.names=FALSE)
 write_json(list(source_original=repair$source,source_original_sha256=digest(file=repair$source,algo='sha256'),MI_input_sha256=digest(file=inp,algo='sha256'),MI_data_sha256=digest(file=mp,algo='sha256'),imputation_predictors=used,saved_only_auxiliary=aux,limitation='数据对齐不代表插补方法或其下游潜交互已验收'),file.path(root,'audit/mi_dependency.json'),auto_unbox=TRUE,pretty=TRUE)
 # 修正排行得分的原始SAVEDATA实际上包含SE；旧CSV导出只保留了PID/I4/S4。
 reg<-fromJSON(file.path(q,'accepted_rebuilt_score_sources.json'),simplifyVector=FALSE)$accepted_sources
 wanted<-c('pp_lgca_type14_r_step1.out','pp_lgca_type14_4_r_step1.out');outrows<-list();bindings<-list()
 for(i in seq_along(wanted)){
  r<-Filter(function(z)z$source_identity==wanted[i],reg);stopifnot(length(r)==1L);r<-r[[1]]
  stopifnot(digest(file=r$source,algo='sha256')==r$source_sha256,digest(file=r$output,algo='sha256')==r$candidate_sha256)
  model<-readModels(r$source,quiet=TRUE);scores<-model$savedata;stopifnot(is.data.frame(scores));names(scores)<-toupper(names(scores))
  csv<-read.csv(r$output);names(csv)<-toupper(names(csv));ii<-match(csv$PID,scores$PID);stopifnot(!anyNA(ii),!anyDuplicated(scores$PID),all(c('I4_SE','S4_SE')%in%names(scores)))
  stopifnot(max(abs(csv$I4-scores$I4[ii]),na.rm=TRUE)<1e-10,max(abs(csv$S4-scores$S4[ii]),na.rm=TRUE)<1e-10)
  label<-c('Oldest','FirstSon')[i];saveRDS(scores[,c('PID','I4','I4_SE','S4','S4_SE')],file.path(root,'private',paste0(label,'_scores_with_SE.rds')))
  p<-model$parameters$unstandardized;v<-p[p$paramHeader%in%c('Variances','Residual.Variances'),]
  negative<-any(v$est<0,na.rm=TRUE)||any(v$se>0&v$est_se<0&v$est_se> -900,na.rm=TRUE)
  tx<-paste(readLines(r$source,warn=FALSE),collapse=' ');normal<-grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',tx,fixed=TRUE)
  for(f in c('I4','S4')){z<-scores[[f]];se<-scores[[paste0(f,'_SE')]];cut<-median(z,na.rm=TRUE)
   outrows[[length(outrows)+1L]]<-data.frame(indicator=label,factor=f,N=sum(is.finite(z)),N_SE=sum(is.finite(se)),score_SD=sd(z,na.rm=TRUE),SE_median=median(se,na.rm=TRUE),SE_min=min(se,na.rm=TRUE),SE_max=max(se,na.rm=TRUE),cutpoint=cut,equal_cut=sum(z==cut,na.rm=TRUE),low=sum(z<=cut,na.rm=TRUE),high=sum(z>cut,na.rm=TRUE),source_normal=normal,source_negative_variance=negative,saved_decimals=3,source_identity=r$source_identity)
  }
  bindings[[i]]<-list(indicator=label,output=r$source,output_sha256=r$source_sha256,candidate_csv_sha256=r$candidate_sha256,score_match=TRUE,read_method='MplusAutomation readModels savedata',export_omission='Historical candidate CSV omitted I4_SE and S4_SE; restored from exact producer savedata, no reestimation',model_warnings=model$warnings)
 }
 write.csv(do.call(rbind,outrows),file.path(root,'audit/corrected_score_precision.csv'),row.names=FALSE)
 write_json(bindings,file.path(root,'audit/corrected_score_bindings.json'),auto_unbox=TRUE,pretty=TRUE)
 writeLines(c('LINEAGE_SCORES_COMPLETE',capture.output(sessionInfo())),file.path(root,'runtime/lineage_scores.log'))
 cat('LINEAGE_SCORES_COMPLETE; corrected SE recovered for two producers\n')
})
