# 真实来源自检及队列回归测试；所有新调用替身仅存在于本次测试进程。
Sys.setenv(R2F_ROOT='C:/Users/LZHS/pp_lgcm_review/round2F_20261011',R2F_RUN_MAIN='0')
root<-Sys.getenv('R2F_ROOT')
for(f in list.files(file.path(root,'code'),pattern='\\.R$',full.names=TRUE))parse(f)
source(file.path(root,'code/r2f_selftest.R'),local=TRUE)
if(Sys.getenv('R2F_SKIP_BASE')!='1'){base<-selftest_2f();stopifnot(all(base$result=='PASS'))}
source(file.path(root,'code/r2f_queue.R'),local=TRUE)
ans<-list();check<-function(n,x){ans[[length(ans)+1L]]<<-data.frame(test=n,passed=isTRUE(x));stopifnot(isTRUE(x))}
mk<-function(k=1L,sp='E1',q=30L,status='USABLE')list(id=paste(sp,k,q,status),status=status,spec=sp,member=k,points=q,conv='tight',sample='CFPS',data_tag='Z0',structural_signature=sp,seconds=1,normal=TRUE,LL=-10,dest='mock',exact_LL_difference=0,exact_LL_n_match=TRUE)
save_sel<-function(S)invisible(S)
budget_r2f<-function()list(rows=list(),calls=0,engine_seconds=0,wall_seconds=0)
calls<-list();fail_k<-NULL;fail_repair<-FALSE;crash_k<-NULL
run_r2f<-function(sp,k,attempt,category,points=30L,...){calls[[length(calls)+1L]]<<-list(k=k,attempt=attempt,points=points,sp=sp);if(identical(k,crash_k))stop('SIMULATED_INTERRUPTION');mk(k,sp,points,if(identical(k,fail_k)&&(attempt=='fam'||fail_repair))'INADMISSIBLE' else 'USABLE')}
s<-list(families=list());s<-run_family(s,'E1','E1',mk())
check('ten_members_and_q30_inheritance',family_valid_2f(s$families$E1)&&all(vapply(calls,function(r)r$points==30L,TRUE)))
n<-length(calls);s<-run_family(s,'E1','E1',mk());check('complete_family_not_relaunched',length(calls)==n)
s$families$E1$status<-'RUNNING';s$families$E1$members<-s$families$E1$members[1:4];calls<-list();s<-run_family(s,'E1','E1',mk())
check('resume_starts_at_member05',identical(vapply(calls,function(r)r$k,1L),5:10)&&family_valid_2f(s$families$E1))
bad<-s$families$E1;bad$members[['6']]$points<-20L;check('mixed_integration_not_poolable',!family_valid_2f(bad))
bad<-s$families$E1;bad$members[['6']]$spec<-'E1B';check('mixed_constraints_not_poolable',!family_valid_2f(bad))
bad<-s$families$E1;bad$members[['6']]<-NULL;check('missing_member_not_poolable',!family_valid_2f(bad))
bad<-s$families$E1;bad$members[['6']]$status<-'INADMISSIBLE_SY_ONLY';check('negative_variance_not_poolable',!family_valid_2f(bad))
fail_k<-6L;fail_repair<-TRUE;calls<-list();s<-run_family(list(families=list()),'E1','E1',mk());check('failed_member_one_repair_then_stop',s$families$E1$status=='MEMBER_FAILED'&&sum(vapply(calls,function(r)r$k==6L,TRUE))==2L&&max(vapply(calls,function(r)r$k,1L))==6L)
fail_repair<-FALSE;calls<-list();s<-run_family(list(families=list()),'E1','E1',mk());check('successful_repair_preserves_ten',family_valid_2f(s$families$E1)&&length(s$families$E1$repairs)==1L)
budget_r2f<-function()list(rows=list(),calls=0,engine_seconds=10800,wall_seconds=0);calls<-list();s<-run_family(list(families=list()),'E1','E1',mk());check('budget_blocks_whole_family',length(calls)==0L&&s$families$E1$status=='NOT_ESTIMATED_WITHIN_BUDGET')
numeric_compare_2f<-function(a,b,mode='start',diagnostic=FALSE)list(passed=a$status=='USABLE'&&b$status=='USABLE',outcome=if(a$status=='USABLE'&&b$status=='USABLE')'AGREE' else 'NOT_REPLICATED')
fail_k<-NULL;calls<-list();p<-pilot_2f(list(),'F2','E1');check('pilot_uses_both_grids_both_starts',length(calls)==4&&p$F2$passed&&p$F2$selected$points==30)
p$F2$runs$q30b$status<-'ESTIMATION_FAILED';p<-pilot_2f(p,'F2','E1');check('alternate_failure_never_passes',!p$F2$passed)
out<-do.call(rbind,ans);write.csv(out,file.path(root,'audit/CONSENSUS_QUEUE_TESTS.csv'),row.names=FALSE);cat('CONSENSUS_QUEUE_TESTS',nrow(out),'PASS\n')
