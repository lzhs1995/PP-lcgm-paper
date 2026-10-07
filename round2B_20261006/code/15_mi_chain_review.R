# 读取持久化检查点的独立诊断；不改变链、随机数或现有成员。
local({
 root <- 'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 library(mice); library(jsonlite); library(digest)
 path <- file.path(root,'private/mi_checkpoint.rds')
 before <- digest(file=path,algo='sha256')
 imp <- readRDS(path)
 stopifnot(identical(before,digest(file=path,algo='sha256')))
 inputs <- readRDS(file.path(root,'private/mi_actual_inputs.rds'))
 missing_counts <- colSums(is.na(inputs$original))
 suppressed <- names(missing_counts)[missing_counts<10]
 write_json(list(minimum_missing_records=10,missing_counts=as.list(missing_counts),
   suppressed_variables=suppressed,reason='Small missing-record summaries could disclose individual imputed values. Preserve full local checkpoint; suppress values in public summaries and traces.'),
   file.path(root,'audit/mi_release_policy.json'),pretty=TRUE,auto_unbox=TRUE)
 dest <- file.path(root,'audit',sprintf('mi_chain_review_iteration_%02d',imp$iteration))
 dir.create(dest,showWarnings=FALSE)
 method <- data.frame(variable=names(imp$method),requested=inputs$method,
                      actual=imp$method,stringsAsFactors=FALSE)
 write.csv(method,file.path(dest,'methods.csv'),row.names=FALSE)
 write.csv(imp$predictorMatrix,file.path(dest,'predictor_matrix.csv'))
 differences <- which(imp$predictorMatrix != inputs$predictorMatrix,arr.ind=TRUE)
 changed <- data.frame(target=rownames(imp$predictorMatrix)[differences[,1]],
                       predictor=colnames(imp$predictorMatrix)[differences[,2]],
                       requested=inputs$predictorMatrix[differences],
                       actual=imp$predictorMatrix[differences])
 write.csv(changed,file.path(dest,'predictor_changes.csv'),row.names=FALSE)
 events <- imp$loggedEvents
 if(is.null(events))events <- data.frame(it=integer(),im=integer(),dep=character(),meth=character(),out=character())
 write.csv(events,file.path(dest,'logged_events.csv'),row.names=FALSE)
 cv <- tryCatch(mice::convergence(imp),error=function(e)data.frame(error=conditionMessage(e)))
 write.csv(cv,file.path(dest,'convergence.csv'),row.names=FALSE)
 summary_rows <- list()
 for(v in inputs$targets)for(k in seq_len(imp$m)){
   x <- as.numeric(imp$imp[[v]][,k])
   summary_rows[[length(summary_rows)+1L]] <- data.frame(variable=v,member=k,
     missing_records=length(x),finite=all(is.finite(x)),mean=mean(x),sd=sd(x),
     minimum=min(x),q25=unname(quantile(x,.25)),median=median(x),
     q75=unname(quantile(x,.75)),maximum=max(x),unique_values=length(unique(x)))
 }
 marginals <- do.call(rbind,summary_rows)
 hide <- marginals$missing_records<10
 value_columns <- c('mean','sd','minimum','q25','median','q75','maximum','unique_values')
 marginals[hide,value_columns] <- NA_real_
 marginals$small_cell_suppressed <- hide
 marginals$minimum <- NULL; marginals$maximum <- NULL
 write.csv(marginals,file.path(dest,'imputed_marginals.csv'),row.names=FALSE)
 grDevices::pdf(file.path(dest,'chain_traces.pdf'),width=11,height=7)
 for(v in inputs$targets){
   par(mfrow=c(1,2))
   for(stat in c('chainMean','chainVar')){
     z <- imp[[stat]][v,,,drop=FALSE]
     dim(z) <- c(imp$iteration,imp$m)
     if(v%in%suppressed){plot.new();title(paste(v,stat));text(.5,.5,'Values suppressed: fewer than 10 missing records')}
     else if(any(is.finite(z)))matplot(seq_len(imp$iteration),z,type='l',lty=1,col=seq_len(imp$m),
       xlab='Iteration',ylab=stat,main=paste(v,stat))
     else {plot.new();title(paste(v,stat));text(.5,.5,'Undefined: fewer than two missing records\nor no finite chain summary')}
   }
 }
 grDevices::dev.off()
 write_json(list(iteration=imp$iteration,m=imp$m,checkpoint_sha256=before,
   methods_unchanged=identical(as.character(imp$method),as.character(inputs$method)),
   predictor_changes=nrow(changed),logged_events=nrow(events),
   complete_prespecified_iterations=imp$iteration==30,
   status='DIAGNOSTICS_REQUIRE_REVIEW_NOT_AUTOMATIC_CONVERGENCE_PASS',
   caveats='Chain moments and convergence diagnostics do not establish MAR or congeniality with latent interactions; household summaries here count missing person records, not independent households.'),
   file.path(dest,'receipt.json'),pretty=TRUE,auto_unbox=TRUE)
 cat('Read-only chain diagnostics:',dest,'; iteration',imp$iteration,'\n')
})
