# 用既有SW高精度输出补齐载荷、同波残差及其不确定性；零次新增模型。
# 本脚本只在隔离环境执行，不写入当前队列的进度文件。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/01_tools.R',local=TRUE)
cat('SW structure: reading the ten existing Round2C outputs\n');flush.console()
ss<-list();raws<-list();qu<-list();origin<-list()
labels<-c(paste0('X_loading_',c(2016,2018,2020)),paste0('XY_residual_cov_',2000+R2D_YEARS),
          paste0('XY_residual_cor_',2000+R2D_YEARS),paste0('growth_residual_var_',FAC_XY))
for(k in 1:10){
 d<-file.path(R2C,'models',sprintf('SW_MI%02d',k),'attempt01');m<-read_mplus_raw(d);raws[[k]]<-m
 q<-setNames(rep(NA_real_,length(labels)),labels);J<-matrix(0,length(labels),m$P,dimnames=list(labels,NULL))
 for(j in 2:4){nm<-paste0('X_loading_',2000+R2D_YEARS[j]);id<-pnum(m,'LAMBDA',paste0('X',j),'SX');stopifnot(id>0)
  q[nm]<-m$par$estimate[id];J[nm,id]<-1}
 for(j in 1:5){
  x<-paste0('X',j);y<-paste0('Y',j);yr<-2000+R2D_YEARS[j]
  ids<-c(pnum(m,'THETA',x,y),pnum(m,'THETA',x,x),pnum(m,'THETA',y,y));stopifnot(all(ids>0))
  values<-m$par$estimate[ids];cc<-values[1];vx<-values[2];vy<-values[3];stopifnot(vx>0,vy>0)
  cn<-paste0('XY_residual_cov_',yr);rn<-paste0('XY_residual_cor_',yr)
  q[cn]<-cc;J[cn,ids[1]]<-1;q[rn]<-cc/sqrt(vx*vy)
  J[rn,ids]<-c(1/sqrt(vx*vy),-q[rn]/(2*vx),-q[rn]/(2*vy))
 }
 for(f in FAC_XY){nm<-paste0('growth_residual_var_',f);id<-pnum(m,'PSI',f,f);stopifnot(id>0);q[nm]<-m$par$estimate[id];J[nm,id]<-1}
 U<-J%*%m$V%*%t(J);stopifnot(all(is.finite(q)),all(diag(U)>0));qu[[k]]<-list(q=q,U=U)
 ss[[k]]<-data.frame(member=k,label=labels,estimate=as.numeric(q),se=sqrt(diag(U)),source_output_sha256=hashf(file.path(d,'model.out')))
 # 只复制可公开的聚合证据；绝不复制data.dat或逐人对象。
 dest<-file.path(ROOT,'provenance_SW/models',sprintf('SW_MI%02d',k));dir.create(dest,recursive=TRUE,showWarnings=FALSE)
 for(nm in c('model.inp','model.out','estimates.dat','tech3.dat','input_contract.json','receipt_round2C.json')){
  src<-file.path(d,nm);to<-file.path(dest,nm);stopifnot(file.exists(src));
  if(!file.exists(to))stopifnot(file.copy(src,to));stopifnot(hashf(src)==hashf(to))
  origin[[length(origin)+1]]<-data.frame(relative_file=paste0('models/',sprintf('SW_MI%02d',k),'/',nm),source_sha256=hashf(src),bytes=file.info(src)$size)
 }
}
Q<-do.call(rbind,lapply(qu,'[[','q'));U<-lapply(qu,'[[','U');pp<-rubin_pool(Q,U)
tt<-data.frame(label=labels,pp$table);tt$minimum_member_estimate<-apply(Q,2,min);tt$maximum_member_estimate<-apply(Q,2,max)
tt$inference<-ifelse(grepl('_cor_',labels),'Delta method within member; Rubin conditional MI','Fixed-model conditional MI')
write.csv(do.call(rbind,ss),file.path(ROOT,'results/SW_structure_members.csv'),row.names=FALSE)
write.csv(tt,file.path(ROOT,'results/SW_structure_pooled.csv'),row.names=FALSE)
for(nm in c('W','B','T')){dimnames(pp[[nm]])<-list(labels,labels);write.csv(pp[[nm]],file.path(ROOT,'results',paste0('SW_structure_',nm,'.csv')))}
write.csv(do.call(rbind,origin),file.path(ROOT,'provenance_SW/source_manifest.csv'),row.names=FALSE)
for(nm in c('conditional_MI_paths.csv','profile_MI01.csv','family_sensitivity.csv','member_dispositions.csv','model_fit.csv'))
 file.copy(file.path(R2C,'results',nm),file.path(ROOT,'provenance_SW',nm),overwrite=TRUE)
for(nm in c('input_scale_reproducible_check.json','x_scale_crosswave_check.json','family_gates.csv','start_checks.csv'))
 file.copy(file.path(R2C,'audit',nm),file.path(ROOT,'provenance_SW',nm),overwrite=TRUE)
wj(list(status='DERIVED_FROM_EXISTING_OUTPUTS',new_mplus_calls=0,members=10,rows=nrow(tt),
 limits=c('Conditional on adopted SW and current MI; not model-selection uncertainty','Residual correlations use a delta approximation; not Fisher-z pooled','Variance Wald P values are descriptive; not boundary-aware hypothesis tests'),
 source_commit=contract()$source_commit_round2C),file.path(ROOT,'results/SW_structure_receipt.json'))
cat('SW STRUCTURE TABLES COMPLETE:',nrow(tt),'pooled rows; 0 new Mplus calls\n');flush.console()
