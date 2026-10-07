# 运行模型前的统计与输入契约测试；不调用Mplus。
source('C:/Users/LZHS/pp_lgcm_review/round2C_20261007/code/01_model_engine.R',local=TRUE)
local({
 tests<-list();record<-function(n,ok){stopifnot(isTRUE(ok));tests[[n]]<<-data.frame(test=n,passed=ok)}
 p<-read.csv(file.path(R2B,'models/PARENT_MI01/attempt01/parameters_high_precision.csv'))
 g<-geometry3(p,'ORIGINAL');record('original_inadmissible_geometry',!g$passed)
 record('original_SY_algebra_binding',abs(g$diagnostic$residual_reconstructed-g$diagnostic$SY_residual)<1e-12)
 record('original_partial_ratio',abs(g$diagnostic$partial_ratio-(-2.53685916))<1e-7)
 z<-p[!(p$matrix=='psi'&p$row=='SY'&p$column=='SY'),]
 gz<-geometry3(z,'C1',0);record('explicit_fixed_zero_psd_accepted',gz$passed&&gz$checks$G$rank==3)
 record('unknown_fixed_zero_rejected',inherits(try(geometry3(z,'C1'),silent=TRUE),'try-error'))
 zz<-z;zz$estimate[zz$matrix=='psi'&zz$row=='SX'&zz$column=='SX']<--.1
 record('negative_variance_transfer_rejected',!geometry3(zz,'C1',0)$passed)
 record('positive_diagonal_indefinite_rejected',!matrix_check3(matrix(c(1,2,2,1),2))$psd)
 record('unexpected_rank_deficiency_rejected',!matrix_check3(matrix(1,2,2))$rank_ok)
 record('covariance_is_not_directed_regression',g$B['SY','SX']!=0&&g$B['SX','SY']==0)
 for(n in c('C1','SW','XLIN')){
  row<-prepare3(n,1,if(n=='C1')0 else NA_real_)
  s<-paste(readLines(row$input,warn=FALSE),collapse='\n')
  record(paste0(n,'_data_identity'),row$data_sha256==fromJSON(file.path(R2B,'models/PARENT_MI01/attempt01/input_contract.json'))$data_sha256)
  record(paste0(n,'_sx_iy_retained'),grepl('sx WITH iy;',s,fixed=TRUE))
  record(paste0(n,'_boundary_semantics'),grepl('sy@0;',s,fixed=TRUE)==(n=='C1'))
 }
 proto<-test_pool();for(k in 1:nrow(proto))record(paste0('Rubin_',proto$test[k]),proto$passed[k])
 geom<-lapply(1:10,function(k){p<-read.csv(file.path(R2B,sprintf('models/PARENT_MI%02d/attempt01/parameters_high_precision.csv',k)));g<-geometry3(p,'ORIGINAL');data.frame(member=k,as.data.frame(g$diagnostic),G_min_eigen=g$checks$G$min_eigen,passed=g$passed)})
 write.csv(do.call(rbind,geom),file.path(R2C,'audit/original_parent_geometry.csv'),row.names=FALSE)
 write.csv(do.call(rbind,tests),file.path(R2C,'evidence/preflight_tests.csv'),row.names=FALSE)
 write_json(list(status='PASS',tests=length(tests),Mplus_calls=0,contract_sha256=hash3(file.path(R2C,'RUN_CONTRACT.json'))),file.path(R2C,'evidence/preflight_tests.json'),pretty=TRUE,auto_unbox=TRUE)
 cat('ALL PREFLIGHT TESTS PASSED',length(tests),'Mplus calls 0\n')
})
