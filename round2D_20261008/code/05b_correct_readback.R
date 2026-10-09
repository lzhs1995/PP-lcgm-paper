# 已有合成输出只读重建；修正的是Mplus内部参数表示到实质测量层的映射，零次新增估计。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
records<-list()
for(sp in c('E1','H4_EDU')){
 d<-model_dir('SD',sp,0,'synthetic','SYNTHETIC');rf<-file.path(d,'receipt.json');before<-fromJSON(rf)
 af<-file.path(d,'receipt_before_indicator_mapping_fix.json');if(!file.exists(af))file.copy(rf,af)
 gf<-file.path(d,'geometry_before_indicator_mapping_fix.json');if(!file.exists(gf))file.copy(file.path(d,'geometry.json'),gf)
 row<-fromJSON(file.path(d,'input_contract.json'));after<-readback_model(row,before$seconds,before$exitcode)
 stopifnot(after$output_sha256==before$output_sha256,isTRUE(after$usable))
 records[[sp]]<-list(before=before$status,after=after$status,output_sha256=after$output_sha256,new_model_calls=0,
       reason='Indicators regressed ON Z0 are promoted by Mplus into BETA/PSI; collapse unit-loading proxies to actual measurement residual covariance')
}
sf<-file.path(ROOT,'tests/synthetic_summary.json');before<-fromJSON(sf,simplifyVector=FALSE)
af<-file.path(ROOT,'tests/synthetic_summary_before_mapping_fix.json');if(!file.exists(af))file.copy(sf,af)
for(sp in c('E1','H4_EDU'))before$receipts[[sp]]<-fromJSON(file.path(model_dir('SD',sp,0,'synthetic','SYNTHETIC'),'receipt.json'),simplifyVector=FALSE)
before$all_four_models_admissible_after_readback_fix<-TRUE;wj(before,sf)
wj(list(status='READBACK_FIXED',models=records,new_model_calls=0,script_sha256=hashf(file.path(ROOT,'code/01_tools.R'))),file.path(ROOT,'audit/indicator_representation_correction.json'))
progress('readback_corrected','Two existing synthetic outputs admissible after exact measurement representation correction; zero refits')
