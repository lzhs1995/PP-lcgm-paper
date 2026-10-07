# 检查缺失掩码和有限性；不得用na.rm掩盖原观测变缺失。
validate_member <- function(before,after,targets,derived,hhvars,key='fid'){
 checks<-list();add<-function(n,v)checks[[n]]<<-isTRUE(v)
 add('row_count',nrow(before)==nrow(after));add('column_order',identical(names(before),names(after)))
 add('row_key_unchanged',identical(before$pid,after$pid));add('unique_person',!anyDuplicated(after$pid))
 add('household_key_unchanged',identical(before[[key]],after[[key]]))
 for(v in targets){
   obs<-is.finite(before[[v]]);add(paste0(v,'_observed_finite'),all(is.finite(after[[v]][obs])))
   add(paste0(v,'_observed_unchanged'),all(after[[v]][obs]==before[[v]][obs]))
   add(paste0(v,'_target_completed'),all(is.finite(after[[v]])))
   add(paste0(v,'_donor_support'),all(after[[v]][!obs]%in%before[[v]][obs]))
 }
 for(v in setdiff(names(before),c(targets,derived)))add(paste0(v,'_frozen'),identical(before[[v]],after[[v]]))
 for(v in hhvars)add(paste0(v,'_household_constant'),all(vapply(split(after[[v]],after[[key]]),function(x)all(is.finite(x))&&length(unique(x))==1L,logical(1))))
 add('derived_income',identical(after$pinc412,as.integer(after$pinc212>0)))
 for(k in c(2,3))add(paste0('derived_prov',k),identical(after[[paste0('prov12',k)]],as.integer(after$prov12==k)))
 data.frame(check=names(checks),passed=unlist(checks),row.names=NULL)
}
test_validator<-function(){
 b<-data.frame(pid=1:4,fid=c(1,1,2,2),finc12=c(2,2,NA,NA),pinc212=c(0,1,NA,1),prov12=c(1,1,NA,NA),y=c(1,NA,3,4));b$pinc412<-as.integer(b$pinc212>0);b$prov122<-as.integer(b$prov12==2);b$prov123<-as.integer(b$prov12==3)
 a<-b;a$finc12[3:4]<-2;a$pinc212[3]<-0;a$prov12[3:4]<-1;a$pinc412<-as.integer(a$pinc212>0);a$prov122<-as.integer(a$prov12==2);a$prov123<-as.integer(a$prov12==3)
 check<-function(z)all(validate_member(b,z,c('finc12','pinc212','prov12'),c('pinc412','prov122','prov123'),c('finc12','prov12'))$passed)
 rows<-data.frame(case='valid_member',passed=check(a))
 variants<-list(observed_NA=function(z){z$finc12[1]<-NA;z},observed_Inf=function(z){z$pinc212[2]<-Inf;z},target_unfilled=function(z){z$pinc212[3]<-NA;z},household_conflict=function(z){z$finc12[4]<-3;z},frozen_filled=function(z){z$y[2]<-0;z},observed_changed=function(z){z$pinc212[2]<-0;z},derived_wrong=function(z){z$pinc412[3]<-1L;z},rows_reordered=function(z)z[4:1,],duplicate_pid=function(z){z$pid[2]<-1;z})
 for(n in names(variants))rows<-rbind(rows,data.frame(case=n,passed=!check(variants[[n]](a))))
 stopifnot(all(rows$passed));rows
}
