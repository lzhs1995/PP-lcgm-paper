# 既有PMM候选逐成员来源与家庭收入一致性审查，不生成新插补。
local({
 library(jsonlite);library(digest)
 root<-'C:/Users/LZHS/pp_lgcm_review/round2_20261006'
 q<-'C:/Users/LZHS/pp_lgcm_runs/20260908_parallel/recovery/20261001_pp_lgcm_reconciliation/10_resume_verified_20261001/scientific_followup/measurement_audit'
 base<-file.path(q,'pmm_observed_future_v3_NOT_RELEASED');v<-fromJSON(file.path(base,'validation.json'),simplifyVector=FALSE);protocol<-fromJSON(file.path(base,'protocol.json'))
 raw<-readRDS(file.path(q,'cesd_marriage_repair_v3_candidate/corrected_data_NOT_RELEASED.rds'))
 plain<-function(z){if(inherits(z,'haven_labelled'))attributes(z)<-NULL;z};d<-as.data.frame(lapply(raw,plain))
 stopifnot(protocol$data_sha256==digest(file=file.path(q,'mi_measurement_repair_v3_marriage_aligned/corrected_measurement_MI_input.dat'),algo='sha256'))
 groups<-split(seq_len(nrow(d)),d$fid)
 conflict<-function(x,ii){z<-x[ii];z<-z[is.finite(z)];length(z)>1L&&max(z)-min(z)>1e-6}
 obsconf<-sum(vapply(groups,function(ii)conflict(d$finc12,ii),logical(1)))
 affected<-Filter(function(ii)length(ii)>1L&&anyNA(d$finc12[ii]),groups)
 rows<-list();targets<-c('cdar12','pinc12','pinc212','pinc412','sat12','adl12','finc12')
 for(k in seq_along(v$members)){
  m<-v$members[[k]];stopifnot(digest(file=m$path,algo='sha256')==m$sha256)
  a<-readRDS(m$path);stopifnot(identical(as.numeric(a$pid),as.numeric(d$pid)))
  changes<-0L
  for(n in intersect(names(d),names(a))){keep<-!is.na(d[[n]]);changes<-changes+sum(abs(a[[n]][keep]-d[[n]][keep])>1e-6,na.rm=TRUE)}
  rows[[k]]<-data.frame(imputation=k,hash_ok=TRUE,observed_cells_changed=changes,personal_income_negative=sum(a$pinc212<0),household_income_negative=sum(a$finc12<0),income_binary_mismatch=sum(a$pinc412!=as.integer(a$pinc212>median(d$pinc212,na.rm=TRUE))),observed_household_income_conflict_groups=obsconf,affected_multi_person_families=length(affected),affected_family_income_conflict_groups=sum(vapply(affected,function(ii)conflict(a$finc12,ii),logical(1))))
 }
 write.csv(do.call(rbind,rows),file.path(root,'audit/pmm_member_audit.csv'),row.names=FALSE)
 # 仅本地用于发布前检查，绝不复制到公开包。
 writeLines(unique(as.character(c(d$pid,d$fid))),file.path(root,'private/identifiers.txt'))
 cat('PMM_AUDIT_COMPLETE\n');print(do.call(rbind,rows))
})
