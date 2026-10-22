# 仅从保存参数重算有限社区数敏感性；原结果和Mplus输出保持只读。
local({
 library(jsonlite); library(digest)
 ROOT <- 'C:/Users/LZHS/pp_lgcm_review/charls_education_postprocess_correction_20261022'
 key <- function(p) vapply(seq_len(nrow(p)),function(i){
   a<-toupper(p$row[i]);b<-toupper(p$column[i]);mat<-tolower(p$matrix[i])
   if(mat %in% c('psi','theta')){s<-sort(c(a,b));a<-s[1];b<-s[2]}
   paste(mat,a,b,sep=':')
 },'')
 for(z in c('gender','oldest','son')) {
  src<-paste0('C:/Users/LZHS/pp_lgcm_review/charls_latent_h42_',z,'_edu_full_20261022')
  dst<-file.path(ROOT,z);dir.create(dst,showWarnings=FALSE)
  con<-fromJSON(file.path(src,'contracts/RUN_CONTRACT.json'));ids<-con$primary_sequence
  source(file.path(src,'code/mi_pool_math.R'),local=TRUE)
  Q<-matrix(NA_real_,20,134); U<-list(); clusters<-numeric(20); hashes<-list()
  for(k in seq_along(ids)) {
   d<-file.path(src,'models',ids[k]);rec<-fromJSON(file.path(d,'receipt.json'));stopifnot(rec$status=='USABLE')
   p<-read.csv(file.path(d,'parameters_high_precision.csv'));if(k==1){first<-p;keys<-key(p)}
   ord<-match(keys,key(p));stopifnot(!anyNA(ord));Q[k,]<-p$estimate[ord]
   U[[k]]<-as.matrix(read.csv(file.path(d,'parameter_covariance.csv'),header=FALSE))[ord,ord]
   dat<-read.table(file.path(d,'data.dat'),header=FALSE);clusters[k]<-length(unique(dat[[1]]));rm(dat)
   hashes[[k]]<-data.frame(id=ids[k],parameters_sha256=digest(file=file.path(d,'parameters_high_precision.csv'),algo='sha256'),covariance_sha256=digest(file=file.path(d,'parameter_covariance.csv'),algo='sha256'))
  }
  stopifnot(length(unique(clusters))==1,clusters[1]==con$communities)
  nu<-clusters[1]-1;po<-rubin_pool(Q,U,nu)
  write.csv(cbind(first[,c('parameter','matrix','row','column')],key=keys,po$table),file.path(dst,'POOLED_CLUSTER_DF_CORRECTED.csv'),row.names=FALSE)
  rows<-list()
  for(path in c('IY:IX','SY:IX','SY:SX','IY:IZ','SY:IZ','SY:SZ','SY:SXIZ'))for(g in c('group0','group1','difference')){
   a<-numeric(134);if(g!='difference')a[match(paste0('beta:',path),keys)]<-1
   if(g!='group0')a[match(paste0('beta:',path,'G'),keys)]<-1
   rows[[paste(path,g)]]<-data.frame(path=path,contrast=g,pool_contrast(Q,U,a,nu))
  }
  write.csv(do.call(rbind,rows),file.path(dst,'CONTRASTS_CLUSTER_DF_CORRECTED.csv'),row.names=FALSE)
  write.csv(do.call(rbind,hashes),file.path(dst,'SOURCES.csv'),row.names=FALSE)
  write_json(list(status='DERIVED_SENSITIVITY_CORRECTED',indicator=z,m=20,communities=clusters[1],old_dfcom=437,corrected_dfcom=nu,convention='community count minus one; sensitivity only, not exact finite-cluster calibration',primary_unchanged=TRUE,original_primary_sha256=digest(file=file.path(src,'results/PRIMARY_H42.csv'),algo='sha256'),Mplus_calls=0,MI_calls=0,full_H4_complete=FALSE),file.path(dst,'CORRECTION.json'),auto_unbox=TRUE,pretty=TRUE)
  cat('FINITE_CLUSTER_CORRECTED',z,'communities',clusters[1],'dfcom',nu,'\n');flush.console()
 }
})
