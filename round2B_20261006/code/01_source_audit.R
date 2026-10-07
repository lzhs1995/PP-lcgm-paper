# Round2B：绑定补齐前2012年协变量，逐记录比较仅在本地进行，公开聚合证据。
local({
 library(haven);library(jsonlite);library(digest)
 root <- 'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 q <- 'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 dp <- file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds')
 rawp <- 'C:/Users/LZHS/Desktop/开题报告/0_data_clo/satisfaction1_2012_covar.dta'
 plain <- function(z){if(inherits(z,'haven_labelled'))attributes(z)<-NULL;z}
 d <- as.data.frame(lapply(readRDS(dp),plain));r <- as.data.frame(lapply(read_dta(rawp),plain))
 stopifnot(!anyDuplicated(d$pid),!anyDuplicated(r$pid),all(d$pid%in%r$pid))
 r <- r[match(d$pid,r$pid),];stopifnot(all(r$pid==d$pid))
 map <- c(sex12='gender12',edu12='edu12',urban12='urban12',prov12='provcdn12',cdn12='childn12',cdar12='childager12',cdsc12='childsexc12',minor12='minor12',age12='age12',ageg12='ageg12',pinc12='pincome12',pinc212='pincome212',cores12='coreside12',heal12='health12',marr12='marr12',eco12='eco12',hwc12='howcare12',hukou12='hukou12',sat12='satif12',adl12='adl12',finc12='fffinc12')
 raw <- r[,unname(map)];names(raw)<-names(map)
 raw$edu12 <- ifelse(is.na(raw$edu12),NA,as.integer(raw$edu12>1))
 raw$pinc212 <- raw$pinc212/10000;raw$finc12 <- raw$finc12/10000
 rows <- lapply(names(map),function(v){a<-raw[[v]];b<-d[[v]];both<-is.finite(a)&is.finite(b);data.frame(variable=v,source_column=map[[v]],source_missing=sum(is.na(a)),current_missing=sum(is.na(b)),source_missing_current_observed=sum(is.na(a)&is.finite(b)),source_observed_current_missing=sum(is.finite(a)&is.na(b)),observed_differences=sum(abs(a[both]-b[both])>1e-5),max_observed_difference=if(any(both))max(abs(a[both]-b[both]))else NA)})
 write.csv(do.call(rbind,rows),file.path(root,'audit/baseline_source_comparison.csv'),row.names=FALSE)
 saveRDS(list(current=d,baseline_raw=raw,raw_fid=r$fid12),file.path(root,'private/source_audit_objects.rds'))
 hh <- split(seq_len(nrow(d)),d$fid)
 hs <- do.call(rbind,lapply(hh,function(i){x<-d$finc12[i];o<-unique(x[is.finite(x)]);data.frame(members=length(i),observed=sum(is.finite(x)),missing=sum(is.na(x)),state=if(length(o)>1)'CONFLICT'else if(length(o)==0)'ALL_MISSING'else if(anyNA(x))'PARTIAL'else'CONSISTENT')}))
 write.csv(as.data.frame(with(hs,table(state,multiple=members>1))),file.path(root,'audit/household_missing_counts.csv'),row.names=FALSE)
 cov <- read.csv('C:/Users/LZHS/pp_lgcm_review/round2_20261006/audit/covariates_26.csv')$variable
 write.csv(data.frame(set=c('historical26','without_wave','without_wave_sat'),N=sapply(list(cov,setdiff(cov,'wave'),setdiff(cov,c('wave','sat12'))),function(v)sum(complete.cases(d[v])))),file.path(root,'audit/complete_case_counts.csv'),row.names=FALSE)
 write.csv(as.data.frame(table(age=d$age12,category=d$ageg12)),file.path(root,'audit/age_crosswalk.csv'),row.names=FALSE)
 contract<-list(N=nrow(d),data_sha256=digest(file=dp,algo='sha256'),baseline_source_sha256=digest(file=rawp,algo='sha256'),baseline_source=rawp,household_key_matches=sum(d$fid==r$fid12,na.rm=TRUE),household_key_missing=sum(!is.finite(r$fid12)),missing_households=sum(hs$state=='ALL_MISSING'),missing_people=sum(hs$missing),observed_conflict_households=sum(hs$state=='CONFLICT'),script_sha256=digest(file=file.path(root,'code/01_source_audit.R'),algo='sha256'))
 write_json(contract,file.path(root,'audit/source_contract.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 print(do.call(rbind,rows));print(contract[c('N','household_key_matches','missing_households','missing_people')])
})
