# 只读当前已保存的插补检查点，及早排除数据层错误；不替代完整链验收。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 source(file.path(root,'code/mi_validation.R'),local=TRUE)
 b<-readRDS(file.path(root,'private/baseline_preMI.rds'));d<-b$data
 imp<-readRDS(file.path(root,'private/mi_checkpoint.rds'))
 contract<-readRDS(file.path(root,'private/mi_actual_inputs.rds'))
 results<-list()
 for(k in seq_len(imp$m)){
   ck<-mice::complete(imp,k);a<-d
   for(v in contract$targets)a[[v]]<-ck[[v]]
   a$prov122<-as.integer(a$prov12==2);a$prov123<-as.integer(a$prov12==3);a$pinc412<-as.integer(a$pinc212>0)
   v<-validate_member(d,a,contract$targets,c('prov122','prov123','pinc412'),contract$household)
   v$member<-k;v$iteration<-imp$iteration;results[[k]]<-v
 }
 val<-do.call(rbind,results);out<-file.path(root,'audit',sprintf('checkpoint_iteration_%02d_validation.csv',imp$iteration));write.csv(val,out,row.names=FALSE)
 jsonlite::write_json(list(iteration=imp$iteration,m=imp$m,total_checks=nrow(val),passed=sum(val$passed),status=if(all(val$passed))'INTERIM_DATA_CHECKS_PASS_NOT_CHAIN_OR_MODEL_ACCEPTANCE'else'INTERIM_VALIDATION_FAILED'),sub('.csv$','.json',out),pretty=TRUE,auto_unbox=TRUE)
 print(table(val$passed));cat('iteration',imp$iteration,'; incomplete chains, no model adoption\n')
})
