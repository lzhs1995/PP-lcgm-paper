# 聚合数据说明与相容性审计；只读既有私有对象，不插补、不改变模型输入。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/01_tools.R',local=TRUE)
library(haven)
d<-readRDS(file.path(R2B,'private/baseline_preMI.rds'))$data
q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
f<-file.path(q,'missingness_source_contract_v2_20261002/person_wave_missingness_contract.csv')
ms<-read.csv(f,stringsAsFactors=FALSE);stopifnot(nrow(ms)==3274*4,!anyDuplicated(paste(ms$pid,ms$wave)))
tf<-function(x)toupper(as.character(x))=='TRUE'
out<-list();alignment<-list()
for(w in R2D_YEARS[-1]){
 a<-ms[ms$wave==2000+w,];a<-a[match(d$pid,a$pid),];stopifnot(identical(as.numeric(a$pid),as.numeric(d$pid)))
 xm<-is.na(d[[paste0('wfdms',w)]]);ym<-is.na(d[[paste0('ces8',w)]])
 alignment[[as.character(w)]]<-list(X_missing_equal=identical(xm,tf(a$wfd_missing)),Y_missing_equal=identical(ym,tf(a$cesd_missing)))
 stopifnot(alignment[[as.character(w)]]$X_missing_equal,alignment[[as.character(w)]]$Y_missing_equal)
 dead<-tf(a$confirmed_death_before_nominal_wave)
 for(z in names(R2D_Z)){
  base<-is.finite(d[[paste0(R2D_Z[[z]]$raw,12)]])
  v<-d[[paste0(R2D_Z[[z]]$raw,w)]];miss<-is.na(v)&base
  category<-ifelse(!miss,'observed_or_outside_baseline_sample',ifelse(dead,'known_prior_death',
     ifelse(!xm,'X_observed_Z_unavailable_definition_or_response_unresolved',ifelse(tf(a$person_record),'person_record_insufficient_relationship_observations','no_person_record_other_cause_unresolved'))))
  tab<-table(factor(category[miss],levels=c('known_prior_death','X_observed_Z_unavailable_definition_or_response_unresolved','person_record_insufficient_relationship_observations','no_person_record_other_cause_unresolved')))
  out[[length(out)+1]]<-data.frame(z=z,year=2000+w,category=names(tab),N=as.integer(tab))
  stopifnot(!any(is.finite(v)&dead),!any(is.finite(d[[paste0('wfdms',w)]])&dead),!any(is.finite(d[[paste0('ces8',w)]])&dead))
 }
}
write.csv(do.call(rbind,out),file.path(ROOT,'audit/moderator_missingness_sources.csv'),row.names=FALSE)
baseline<-lapply(names(R2D_Z),function(z){v<-d[[paste0(R2D_Z[[z]]$raw,12)]];missing<-is.na(v)
 structural<-if(z=='SEXGAP')d$cdsc12%in%c(1,2) else if(z=='SONGAP')d$cdsc12==2 else rep(FALSE,nrow(d))
 stopifnot(!any(structural&is.finite(v)));data.frame(z=z,observed=sum(is.finite(v)),known_structure_undefined=sum(missing&structural),other_baseline_unavailable=sum(missing&!structural),
 note='Other unavailable values are not automatically called structural; no future-only cases admitted')})
write.csv(do.call(rbind,baseline),file.path(ROOT,'audit/baseline_Z_eligibility.csv'),row.names=FALSE)
wj(list(status='BOUND_TO_CURRENT_MISSINGNESS',source_sha256=hashf(f),row_matching='PID and wave, unique exact matches',alignment=alignment,
 limitations=c('same-year death order remains uncertain','rank unavailable does not by itself prove structural undefinedness','leaving post-death values missing does not solve survival-truncation estimand')),
 file.path(ROOT,'audit/missingness_binding.json'))

# 资源编码，原始2012城乡标签直接核对；其余与已冻结来源对象和派生公式交叉核查。
src<-fromJSON(file.path(R2B,'audit/source_contract.json'));orig<-readRDS(file.path(R2B,'private/source_audit_objects.rds'))$baseline_raw
raw<-read_dta(src$baseline_source);idx<-match(d$pid,raw$pid);stopifnot(!anyNA(idx))
ed<-as.numeric(raw$edu12[idx]);ed[!is.finite(ed)|ed<0]<-NA
derived<-as.integer(ed>1);stopifnot(identical(is.na(derived),is.na(d$edu12)),all(derived[is.finite(derived)]==d$edu12[is.finite(derived)]))
urban_path<-'C:/Users/LZHS/Desktop/20230505 毕业论文/开题报告/开题报告/CFPS/20230808 CFPS官网/[CFPS Public Data] CFPS2012/Data/cfps2012adult_201906.dta'
u<-read_dta(urban_path,col_select=tidyselect::all_of(c('pid','urban12')));ii<-match(d$pid,u$pid);stopifnot(!anyNA(ii))
uv<-as.numeric(u$urban12[ii]);uv[!uv%in%c(0,1)]<-NA
stopifnot(identical(is.na(uv),is.na(d$urban12)),all(uv[is.finite(uv)]==d$urban12[is.finite(uv)]))
gg<-list(EDU=list(one='初中及以上',zero='小学及以下',rule='as.integer(source edu12 > 1)',source_labels=as.list(attr(raw$edu12,'labels')),source_sha256=hashf(src$baseline_source)),
 URBAN=list(one='城市',zero='乡村',rule='CFPS2012 urban12; negative special codes -> missing',source_labels=as.list(attr(u$urban12,'labels')),source_sha256=hashf(urban_path),classification='National Bureau of Statistics 2012; not urbancomm'),
 INC=list(one='有个人收入',zero='无个人收入',rule='as.integer(pinc212 > 0)',not_equal_to='high income',amount_unit='万元'))
for(k in 1:10){a<-readRDS(file.path(R2B,'private/mi10',sprintf('member_%02d.rds',k)));stopifnot(all(a$pinc412==as.integer(a$pinc212>0)))}
wj(list(status='VERIFIED',groups=gg,all_ten_income_derivations_match=TRUE),file.path(ROOT,'audit/G_CODING_CONFIRMATION.json'))

dictionary<-read.csv('C:/Users/LZHS/pp_lgcm_review/round2_20261006/audit/covariates_26.csv',stringsAsFactors=FALSE)
labels<-c(sex12='男=1；女=0',edu12='初中及以上=1；小学及以下=0',urban12='城市=1；乡村=0',prov122='中部=1；参照东部',prov123='西部=1；参照东部',cdn12='子女人数',cdar12='子女年龄极差（岁）',cdsc121='仅儿子=1；参照儿女双全',cdsc122='仅女儿=1；参照儿女双全',minor12='少数民族=1；汉族=0',ageg12='76岁及以上=1；61—75岁=0',pinc12='自评相对收入（1—5级）',pinc212='个人收入金额（万元）',cores12='与子女同住=1',heal121='不健康=1；参照一般',heal123='健康=1；参照一般',marr12='已婚或同居=1；其他=0',eco122='所有子女提供经济帮助=1；参照无帮助',eco123='部分子女提供经济帮助=1；参照无帮助',hwc122='所有子女提供工具帮助=1；参照无帮助',hwc123='部分子女提供工具帮助=1；参照无帮助',hukou12='农业户口=1；非农业=0',adl12='ADL计数（0—7）',finc12='家庭收入（万元）')
stopifnot(all(d$ageg12==as.integer(d$age12>75)))
ds<-lapply(seq_along(R2D_CONTROLS),function(j){v<-R2D_CONTROLS[j];a<-as.numeric(d[[v]]);o<-is.finite(a);data.frame(model_column=paste0('c',j),variable=v,definition=labels[[v]],observed=sum(o),missing=sum(!o),mean=mean(a[o]),sd=sd(a[o]),minimum=min(a[o]),maximum=max(a[o]),share_one=if(all(a[o]%in%c(0,1)))mean(a[o])else NA_real_)})
write.csv(do.call(rbind,ds),file.path(ROOT,'audit/baseline_controls_descriptives.csv'),row.names=FALSE)
obs<-lapply(R2D_YEARS,function(w)do.call(rbind,lapply(c('wfd_m','ces8'),function(v){a<-as.numeric(d[[paste0(v,w)]]);a<-a[is.finite(a)];data.frame(year=2000+w,variable=v,N=length(a),mean=mean(a),sd=sd(a))})))
write.csv(do.call(rbind,obs),file.path(ROOT,'audit/observed_longitudinal_descriptives.csv'),row.names=FALSE)

# 审计实际而非请求的FCS预测矩阵；不执行原插补脚本。
pmf<-file.path(R2B,'audit/mi_predictor_matrix_actual.csv');pm<-as.matrix(read.csv(pmf,row.names=1,check.names=FALSE));
pr<-fromJSON(file.path(R2B,'audit/mi_protocol.json'));features<-lapply(colnames(pm),function(v)data.frame(predictor=v,target_rows_used=sum(pm[,v]!=0),
 role=if(v=='cluster')'household_cluster' else if(grepl('^obs_|^missing_|^death_|^proxy_|^no_record_',v))'auxiliary_observation_or_missingness' else 'baseline_feature',has_product_in_name=grepl('product|interact|xwith|slope',v,ignore.case=TRUE)))
write.csv(do.call(rbind,features),file.path(ROOT,'audit/MI_actual_predictor_coverage.csv'),row.names=FALSE)
dir.create(file.path(ROOT,'audit/MI_source_snapshot'),showWarnings=FALSE)
for(v in c('mi_predictor_matrix_actual.csv','mi_protocol.json','mi_convergence.csv','mi_member_validation.csv'))file.copy(file.path(R2B,'audit',v),file.path(ROOT,'audit/MI_source_snapshot',v),overwrite=TRUE)
file.copy(file.path(R2B,'code/04_hierarchical_mi.R'),file.path(ROOT,'audit/MI_source_snapshot/04_hierarchical_mi.R'),overwrite=TRUE)
wj(list(status='WORKING_INFERENCE_WITH_CONGENIALITY_LIMITATION',actual_predictor_matrix_sha256=hashf(pmf),producer_script_sha256=hashf(file.path(R2B,'code/04_hierarchical_mi.R')),
  targets=pr$visitSequence,methods=pr$methods,base_Z_features=c('wfd_s12','obs_wfd_d12','obs_wfd_d112','obs_wfd_d412'),
  missing_features=c('joint latent SX IZ distribution','SX*IZ product','all later Z series'),
  judgment='No evidence of substantive-model-compatible imputation for three-process LMS; existing validated MI reused for conditional working inference; no new MI performed'),file.path(ROOT,'audit/MI_CONGENIALITY_AUDIT.json'))
cat('SUPPORT AUDIT COMPLETE: missingness bound, resource coding verified, actual MI predictors audited\n')
