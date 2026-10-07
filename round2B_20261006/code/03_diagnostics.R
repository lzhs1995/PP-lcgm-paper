# 有限K1-K4；K2-K4因恢复基期缺失有5人不完整，报告1976而不伪称1981。
source('C:/Users/LZHS/pp_lgcm_review/round2B_20261006/code/model_tools.R',local=TRUE)
local({
 a<-readRDS(file.path(R2ROOT,'private/baseline_preMI.rds'));rows<-list()
 for(k in 1:4){
   d<-if(k==1)a$original else a$data
   cov<-if(k==1)a$oldcov else a$covariates
   keep<-a$diagnostic & complete.cases(d[cov])
   yy<-as.matrix(d[,paste0('ces8',c(12,16,18,20,22))]);yy<-(yy-mean(yy[,1],na.rm=TRUE))/sd(yy[,1],na.rm=TRUE)
   xx<-as.matrix(d[,paste0('wfdms',c(12,16,18,20,22))])
   z<-data.frame(fid=as.numeric(d$fid[keep]),xx[keep,],yy[keep,],d[keep,cov]);names(z)<-c('fid',paste0('x',1:5),paste0('y',1:5),paste0('c',seq_along(cov)))
   id<-paste0('K',k)
   # K3全五期同波误差相关：共同访谈时间、共同报告方式可产生增长过程之外的关联。
   rows[[k]]<-prepare2(id,z,parent2(nc=length(cov),samewave=k==3,boundary=k==4),paste0('x1-x5 y1-y5 c1-c',length(cov)),list(control_names=cov,shape_y='linear',shape_x='free',time_unit='decade',purpose=c('conditional_parameterization','baseline_controls','samewave_residual_sensitivity','K2_SY_zero_sensitivity')[k]))
 }
 write_json(rows,file.path(R2ROOT,'audit/diagnostic_manifest.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 ans<-lapply(rows,run2);write_json(ans,file.path(R2ROOT,'audit/diagnostic_receipts.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 progress2('diagnostics_complete','K1-K4 all dispositions saved')
})
