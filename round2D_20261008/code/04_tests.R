# 有意义的验收回归测试：失败成员/失败数值检查不能合并，产品矩与带协方差对比必须正确。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
tests<-list()
check<-function(name,x){ok<-isTRUE(x);tests[[length(tests)+1]]<<-data.frame(test=name,passed=ok);if(!ok)stop('TEST FAILED: ',name)}
sw<-read_mplus_raw(file.path(R2C,'models/SW_MI01/attempt01'))
old<-read.csv(file.path(R2C,'models/SW_MI01/attempt01/parameters_high_precision.csv'))
check('real_SW_TECH1_parameter_mapping',identical(sw$par$parameter,old$parameter)&&all(sw$par$row==old$row)&all(sw$par$column==old$column))
check('real_SW_high_precision_values',max(abs(sw$par$estimate-old$estimate))<1e-8)
g<-gate2(sw,list(kind='linear',fac=FAC_XY,obs=OBS_XY));check('real_SW_linear_geometry_admissible',g$passed)
bad<-sw;j<-which(bad$par$matrix=='psi'&bad$par$row=='SY'&bad$par$column=='SY');bad$par$estimate[j]<--.001
check('negative_free_variance_blocks',!gate2(bad,list(kind='linear',fac=FAC_XY,obs=OBS_XY))$passed)
si<-spec_info('SD','D1');check('one_core_latent_product',sum(grepl('XWITH',si$model))==1&&!any(grepl('ixiz',si$model)))
check('all_fifteen_samewave_covariances',sum(grepl('^[xyz][1-5] WITH [yz][1-5];$',si$model))==15)
check('E1_excludes_extra_IX_products',sum(grepl('XWITH',spec_info('SD','E1')$model))==1&&!any(grepl('ixz',spec_info('SD','E1')$model)))
h<-spec_info('SD','H4_EDU');check('H4_all_SX_low_order_products',sum(grepl('XWITH',h$model))==3&&all(c('sy ON sxz (dc);','sy ON sxg (bxg);','sy ON sxzg (dcg);')%in%h$model))
mock<-list(receipt=list(usable=TRUE,LL=-100,attempt='adopted'),raw=list(),key=data.frame(label=c('dc','bss'),estimate=c(.2,-.3),se=c(.1,.2)))
ms<-rep(list(mock),10);num<-list(start=list(passed=TRUE),integration=list(passed=TRUE))
check('ten_members_and_numeric_pass',family_gate(ms,num,TRUE))
check('nine_members_block',!family_gate(ms[1:9],num,TRUE))
mb<-ms;mb[[4]]$receipt$usable<-FALSE;check('failed_member_blocks',!family_gate(mb,num,TRUE))
check('failed_start_blocks',!family_gate(ms,list(start=list(passed=FALSE),integration=list(passed=TRUE)),TRUE))
check('failed_integration_blocks',!family_gate(ms,list(start=list(passed=TRUE),integration=list(passed=FALSE)),TRUE))
mo<-mock;mo$receipt$attempt<-'retry_adopted';mo$key<-mo$key[2:1,];check('parameter_name_alignment',compare_numeric(mock,mo,'start')$passed)
mo$key$estimate[1]<-mo$key$estimate[1]+.2;check('unstable_target_blocks',!compare_numeric(mock,mo,'integration')$passed)
Q<-cbind(a=seq(.1,.19,.01),b=seq(-.2,-.11,.01));U<-rep(list(matrix(c(.04,.018,.018,.09),2)),10);a<-c(1,2)
p<-rubin_pool(Q,U);co<-pool_contrast(Q,U,a)
check('contrast_includes_covariance',abs(co$se^2-as.numeric(t(a)%*%p$T%*%a))<1e-12&&abs(co$se^2-sum(diag(p$T)*a^2))>.01)
set.seed(261008);V<-matrix(c(1,.2,.1,.2,.8,-.15,.1,-.15,1.2),3);mu<-c(.4,-.2,.5)
q<-product_covariance(mu,V,1,2,.7,3);x<-sweep(matrix(rnorm(600000),ncol=3)%*%chol(V),2,mu,'+');x[,3]<-x[,3]+.7*x[,1]*x[,2]
check('Gaussian_product_moments_vs_simulation',max(abs(cov(x)-q$cov))<.035&&max(abs(colMeans(x)-q$mean))<.02)
check('nonlinear_covariance_differs_from_linear',max(abs(q$cov-V))>.1)
check('invalid_covariance_detected',!mcheck(matrix(c(1,2,2,1),2))$psd)
check('sexgap_deterministic_control_removal',all(c(8,9)%in%setdiff(1:24,unlist(zcontract()$samples$SEXGAP_Z0$ctrl_index))))
for(sp in c('E1','H4_EDU')){
 d<-model_dir('SD',sp,0,'synthetic','SYNTHETIC')
 if(file.exists(file.path(d,'estimates.dat'))){
  mm<-read_mplus_raw(d);ss<-spec_info('SD',sp,ctrl='c1-c3',sample='SYNTHETIC');cm<-canonical_measurement(mm,ss$fac,ss$obs)
  check(paste0(sp,'_promoted_measurement_mapping'),setequal(cm$promoted,c('X1','Y1'))&&cm$LAMBDA['X1','IX']==1&&cm$LAMBDA['Y1','IY']==1&&cm$THETA['X1','X1']==mval(mm,'PSI','X1','X1'))
  check(paste0(sp,'_real_synthetic_geometry_after_mapping'),gate2(mm,ss)$passed)
 }
}
write.csv(do.call(rbind,tests),file.path(ROOT,'tests/unit_results.csv'),row.names=FALSE)
wj(list(passed=TRUE,tests=length(tests),software=list(R=R.version.string,MplusAutomation=as.character(packageVersion('MplusAutomation')),processx=as.character(packageVersion('processx'))),created=as.character(Sys.time())),file.path(ROOT,'tests/unit_summary.json'))
progress('unit_tests_complete',paste(length(tests),'tests passed; existing SW readback independently matched'))
