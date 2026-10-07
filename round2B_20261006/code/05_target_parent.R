# 原队列正式父模型工程核验：预先固定24控制、Y日历线性/X自由、完整增长因子关联。
# SX WITH IY解除没有理论依据的零关联；不因诊断样本失败而禁止独立目标队列估计。
.libPaths(c('C:/Users/LZHS/pp_lgcm_runs/20260908/library_mplusautomation_20260926',.libPaths()))
source('C:/Users/LZHS/pp_lgcm_review/round2B_20261006/code/model_tools.R',local=TRUE)
source('C:/Users/LZHS/pp_lgcm_review/round2B_20261006/code/collect_parameters.R',local=TRUE)
local({
 b<-readRDS(file.path(R2ROOT,'private/baseline_preMI.rds'));cov<-b$covariates
 v<-read.csv(file.path(R2ROOT,'audit/mi_member_validation.csv'))
 stopifnot(nrow(v)>0,all(v$passed),identical(sort(unique(v$imputation)),1:10),
           length(unique(as.integer(table(v$imputation))))==1L)
 mi_manifest<-fromJSON(file.path(R2ROOT,'audit/mi_member_manifest.json'))
 stopifnot(nrow(mi_manifest)==10L,identical(as.integer(mi_manifest$imputation),1:10),all(mi_manifest$passed))
 checkpoint<-readRDS(file.path(R2ROOT,'private/mi_checkpoint.rds'))
 stopifnot(checkpoint$m==10L,checkpoint$iteration==30L)
 rm(checkpoint);gc(verbose=FALSE)
 scale_y<-as.matrix(b$data[,paste0('ces8',c(12,16,18,20,22))]);mu<-mean(scale_y[,1],na.rm=TRUE);sig<-sd(scale_y[,1],na.rm=TRUE)
 spec<-paste(parent2(nc=length(cov)),'sx WITH iy;',sep='\n')
 write_json(list(N=3274,covariates=cov,time_unit='decade',shape_y='linear',shape_x='free',sy_residual='unconstrained',extra_growth_relation='SX WITH IY; conditionally saturated growth covariance',samewave_residuals=FALSE,specification=spec,imputations=10,acceptance='all members must be admissible; no deletion of failed members',role='engineering_target_parent_not_automatically_formal'),file.path(R2ROOT,'audit/target_parent_contract.json'),pretty=TRUE,auto_unbox=TRUE)
 rows<-list();receipts<-list()
 for(k in 1:10){
   d<-readRDS(file.path(R2ROOT,'private/mi10',sprintf('member_%02d.rds',k)))
   yy<-(as.matrix(d[,paste0('ces8',c(12,16,18,20,22))])-mu)/sig
   xx<-as.matrix(d[,paste0('wfdms',c(12,16,18,20,22))])
   dat<-data.frame(fid=d$fid,xx,yy,d[cov]);names(dat)<-c('fid',paste0('x',1:5),paste0('y',1:5),paste0('c',seq_along(cov)))
   id<-sprintf('PARENT_MI%02d',k)
   contract<-file.path(R2ROOT,'models',id,'attempt01/input_contract.json')
   member_hash<-digest(file=file.path(R2ROOT,'private/mi10',sprintf('member_%02d.rds',k)),algo='sha256')
   stopifnot(identical(member_hash,mi_manifest$sha256[k]),nrow(d)==mi_manifest$N[k],nrow(d)==3274L)
   spec_hash<-digest(spec,algo='sha256',serialize=FALSE)
   row<-if(file.exists(contract))fromJSON(contract,simplifyVector=FALSE)else prepare2(id,dat,spec,paste0('x1-x5 y1-y5 c1-c',length(cov)),list(imputation=k,source_member_sha256=member_hash,specification_sha256=spec_hash))
   stopifnot(identical(row$source_member_sha256,member_hash),identical(row$specification_sha256,spec_hash))
   rows[[k]]<-row;receipts[[k]]<-run2(row)
   extracted<-tryCatch(collect2(dirname(row$input)),error=function(e){write_json(list(status='EXTRACTION_FAILED',message=conditionMessage(e)),file.path(dirname(row$input),'parameter_extraction_failure.json'),pretty=TRUE,auto_unbox=TRUE);NULL})
   receipts[[k]]$parameter_covariance_bound<-!is.null(extracted)
   if(!is.null(extracted)){
     m<-extracted$map;v<-m[m$matrix%in%c('psi','theta')&m$row==m$column,]
     receipts[[k]]$high_precision_negative_variance<-any(v$estimate<0)
     if(any(v$estimate<0))receipts[[k]]$status<-'INADMISSIBLE'
   }
   rm(d,dat,xx,yy);gc(verbose=FALSE)
   write_json(receipts,file.path(R2ROOT,'audit/target_parent_receipts.json'),auto_unbox=TRUE,pretty=TRUE)
 }
 write_json(rows,file.path(R2ROOT,'audit/target_parent_manifest.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 ok<-all(vapply(receipts,function(x)x$status=='REVIEWABLE'&&isTRUE(x$parameter_covariance_bound),logical(1)))
 write_json(list(all_members_admissible=ok,passed=sum(vapply(receipts,function(x)x$status=='REVIEWABLE',logical(1))),total=10,status=if(ok)'READY_FOR_POOLING_AND_PRECISION_REVIEW'else'BLOCKED_BY_INADMISSIBLE_PARENT_MEMBERS',moderation_authorized=ok),file.path(R2ROOT,'audit/target_parent_gate.json'),pretty=TRUE,auto_unbox=TRUE)
 progress2('parent_complete',if(ok)'All ten parent members admissible; proceed to pooling review'else'Parent gate failed; do not add interactions or selectively pool')
})
