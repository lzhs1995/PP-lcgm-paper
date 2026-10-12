# 三次合成调用：严格准则、固定正值、固定零释放为自由残差。
source(file.path(Sys.getenv('R2F_ROOT'),'code/r2f_local.R'),local=globalenv())
smoke_run<-function(){
 stopifnot(isTRUE(rj(file.path(ROOT,'audit/P0_STATUS_2F.json'))$passed))
 syn<-r2e_model(C2F$round2E_inputs$SYN_E1B$id);dd<-file.path(syn,'data.dat');stopifnot(identical(hashf(dd),C2F$data$synthetic_sha256))
 call<-function(sp,at,q,ov=NULL)run_r2f(sp,1L,at,'SMOKE',conv='tight',points=q,source_dir=syn,start_override=ov,sample='SYNTHETIC',source_data=dd,ctrl='c1-c3')
 a<-call('E1B','smoke_tight',20L);b<-call('E1F034','smoke_fixed',20L);c<-call('E1','smoke_release',30L,C2F$allowed_start_override)
 out<-list();add<-function(n,ok,detail='')out[[length(out)+1L]]<<-data.frame(check=n,passed=isTRUE(ok),detail=paste(detail,collapse=';'))
 for(r in list(a,b,c)){
  add(paste0(r$id,'_usable'),usable(r),r$status);add(paste0(r$id,'_criteria'),isTRUE(r$criteria_as_requested));add(paste0(r$id,'_dimension'),identical(r$integration_dimensions,1L))
  add(paste0(r$id,'_exact_LL'),!is.null(r$exact_LL_difference)&&is.finite(r$exact_LL_difference)&&abs(r$exact_LL_difference)<=C2F$exact_ll$model_tolerance&&isTRUE(r$exact_LL_n_match))
 }
 add('SY_fixed_zero',usable(a)&&a$sy==0);add('SY_fixed_positive',usable(b)&&abs(b$sy-.034)<1e-10);add('SY_released_parameter_count',usable(c)&&c$parameters==a$parameters+1L)
 ck<-do.call(rbind,out);csv(ck,file.path(ROOT,'audit/SMOKE_CHECKS_2F.csv'))
 st<-list(passed=all(ck$passed),convergence_choice='tight',failed=ck$check[!ck$passed],calls=vapply(list(a,b,c),function(r)r$id,''))
 wj(st,file.path(ROOT,'audit/SMOKE_2F.json'));progress('smoke_done',paste('passed=',st$passed));invisible(st)
}
if(sys.nframe()==0L||identical(Sys.getenv('R2F_RUN_MAIN'),'1'))smoke_run()
