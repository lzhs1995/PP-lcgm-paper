# 八份已完成的 CESD 模型原生回读；模型均值与观测均值分开保存。
local({
 library(MplusAutomation);library(jsonlite);library(digest)
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'
 index<-read.csv(file.path(dest,'audit_stage1/model_index.csv'),check.names=FALSE)
 index<-index[index$layer=='corrected_measurement_candidate',]
 params<-fits<-predictions<-list()
 for(i in seq_len(nrow(index))){
   p<-file.path(dest,'audit_stage1/mplus',index$model_id[i],'model.out');a<-readModels(p,quiet=TRUE)
   b<-a$parameters$unstandardized;stopifnot(nrow(b)>0)
   b$model<-index$model[i];b$source<-p;b$source_sha256<-digest(p,algo='sha256',file=TRUE);params[[i]]<-b
   s<-a$summaries;s$model<-index$model[i];fits[[i]]<-s
   if(grepl('shape_factor',index$model[i])) {
     means<-b[b$paramHeader=='Means',];load<-b[b$paramHeader=='S5.|',]
     stopifnot(nrow(load)==5L,all(c('I5','S5')%in%means$param))
     muI<-means$est[means$param=='I5'];muS<-means$est[means$param=='S5']
     predictions[[length(predictions)+1L]]<-data.frame(model=index$model[i],indicator=load$param,year=c(2012,2016,2018,2020,2022),slope_loading=load$est,loading_se=load$se,predicted_mean=muI+load$est*muS,mean_I=muI,mean_S=muS,precision='derived from printed parameters; not unrounded model means',interpretation='endpoints 0/10; intermediate loadings free; not constant annual change')
   }
 }
 write.csv(do.call(rbind,params),file.path(dest,'summaries/growth_parameter_audit.csv'),row.names=FALSE,fileEncoding='UTF-8')
 fields<-Reduce(union,lapply(fits,names));fits<-lapply(fits,function(x){for(k in setdiff(fields,names(x)))x[[k]]<-NA;x[,fields]})
 write.csv(do.call(rbind,fits),file.path(dest,'summaries/growth_fit_audit.csv'),row.names=FALSE,fileEncoding='UTF-8')
 write.csv(do.call(rbind,predictions),file.path(dest,'summaries/growth_predicted_means.csv'),row.names=FALSE,fileEncoding='UTF-8')
 write_json(list(models=nrow(index),parameters=sum(vapply(params,nrow,1L)),new_mplus=0,source_hash_checked=all(vapply(seq_len(nrow(index)),function(i)sha<-digest(file.path(dest,'audit_stage1/mplus',index$model_id[i],'model.out'),algo='sha256',file=TRUE)==index$source_sha256[i],TRUE))),file.path(dest,'native/growth_readback_receipt.json'),auto_unbox=TRUE,pretty=TRUE)
 writeLines(c(capture.output(do.call(rbind,predictions)),capture.output(sessionInfo())),file.path(dest,'native/growth_readback.log'))
 print(do.call(rbind,predictions)[,c('model','year','slope_loading','predicted_mean')])
})
