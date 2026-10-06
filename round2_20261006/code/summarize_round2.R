# 完整TECH3/TECH4、参数序号、局部残差和预测均值导出；打印舍入不作精确正定判据。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2_20261006'
 library(jsonlite);library(digest)
 manifests<-c('manifest.json','followups_manifest.json','followups_v2_manifest.json','moderation_diagnostic_manifest.json')
 rows<-list();for(f in manifests[file.exists(file.path(root,manifests))])rows<-c(rows,fromJSON(file.path(root,f),simplifyVector=FALSE)$models)
 fitrows<-varrows<-pathrows<-matrixrows<-localrows<-meanrows<-list()
 sym<-function(x){if(is.null(x))return(NULL);x<-as.matrix(x);x[upper.tri(x)]<-t(x)[upper.tri(x)];x}
 for(r in rows){
  dest<-dirname(r$input);rp<-file.path(dest,'receipt.json');if(!file.exists(rp))next
  rc<-fromJSON(rp);m<-readRDS(file.path(dest,'readback.rds'));p<-m$parameters$unstandardized
  if(!is.data.frame(p))next
  identity<-data.frame(id=r$id,attempt=r$attempt_id,status=rc$status,N=r$N)
  if(is.data.frame(m$summaries))fitrows[[length(fitrows)+1L]]<-cbind(identity,m$summaries[,intersect(c('Parameters','LL','CFI','TLI','RMSEA_Estimate','RMSEA_90CI_LB','RMSEA_90CI_UB','SRMR'),names(m$summaries)),drop=FALSE])
  v<-p[p$paramHeader%in%c('Variances','Residual.Variances')&p$param%in%c('IX','SX','IY','SY','IZ','SZ'),]
  if(nrow(v))varrows[[length(varrows)+1L]]<-cbind(identity,v)
  pa<-p[p$paramHeader%in%c('IY.ON','SY.ON')&p$param%in%c('IX','SX','IY','IZ','SZ','INT'),]
  if(nrow(pa)){pa$lower95<-pa$est-1.96*pa$se;pa$upper95<-pa$est+1.96*pa$se;pathrows[[length(pathrows)+1L]]<-cbind(identity,pa)}
  mats<-list(TECH3_parameter_covariance=sym(m$tech3$paramCov),TECH4_latent_covariance=sym(m$tech4$latCovEst),TECH4_latent_correlation=sym(m$tech4$latCorEst))
  for(n in names(mats)){
    z<-mats[[n]];if(is.null(z))next
    write.csv(z,file.path(dest,paste0(n,'.csv')),row.names=TRUE)
    ev<-if(all(is.finite(z)))eigen(z,symmetric=TRUE,only.values=TRUE)$values else NA_real_
    matrixrows[[length(matrixrows)+1L]]<-cbind(identity,data.frame(matrix=n,dimension=nrow(z),all_finite=all(is.finite(z)),minimum_eigenvalue=min(ev),maximum_eigenvalue=max(ev),rounding_caution='Matrices are parsed printed output; small negative eigenvalues require rounding-aware review, not automatic rejection'))
  }
  mp<-list();sp<-m$tech1$parameterSpecification
  for(n in names(sp)){
    z<-sp[[n]];ind<-which(!is.na(z)&z>0,arr.ind=TRUE)
    if(nrow(ind))mp[[length(mp)+1L]]<-data.frame(matrix=n,row=rownames(z)[ind[,1]],column=colnames(z)[ind[,2]],parameter_number=z[ind])
  }
  if(length(mp))write.csv(do.call(rbind,mp),file.path(dest,'TECH1_parameter_map.csv'),row.names=FALSE)
  res<-m$residuals$covarianceResid.norm
  if(!is.null(res)){
    res<-as.matrix(res);ij<-which(lower.tri(res,diag=FALSE)&is.finite(res)&abs(res)<900,arr.ind=TRUE)
    if(nrow(ij)){
     tab<-data.frame(variable1=rownames(res)[ij[,1]],variable2=colnames(res)[ij[,2]],normalized_residual=res[ij]);tab<-tab[order(-abs(tab$normalized_residual)),];tab<-head(tab,10)
     localrows[[length(localrows)+1L]]<-cbind(identity,tab)
    }
  }
  mu<-m$residuals$meanEst
  if(!is.null(mu)){
   vals<-as.numeric(mu);nms<-colnames(mu);keep<-grepl('^Y[1-5]$',nms);base<-fromJSON(file.path(root,'audit/source_contract.json'))
   raw<-vals[keep];if(r$scale=='CESD8_baseline_standardized')raw<-raw*base$baseline_sd+base$baseline_mean
   meanrows[[length(meanrows)+1L]]<-cbind(identity,data.frame(variable=nms[keep],year=if(r$window=='four')c(2016,2018,2020,2022) else c(2012,2016,2018,2020,2022),model_mean=vals[keep],CESD8_raw_mean=raw))
  }
 }
 export<-function(x,name){if(length(x))write.csv(do.call(rbind,x),file.path(root,'audit',name),row.names=FALSE)}
 export(fitrows,'model_fit.csv');export(varrows,'growth_variances.csv');export(pathrows,'target_paths.csv');export(matrixrows,'matrix_diagnostics.csv');export(localrows,'largest_local_residuals.csv');export(meanrows,'predicted_means.csv')
 writeLines('SUMMARY_COMPLETE',file.path(root,'runtime/summary_complete.txt'));cat('SUMMARY_COMPLETE',length(fitrows),'attempts\n')
})
