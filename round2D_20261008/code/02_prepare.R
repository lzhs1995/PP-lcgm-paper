# 新增Z入口与原十份MI绑定；不重做已完成清洗，不改写来源。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/01_tools.R',local=TRUE)
progress('prepare','Reading frozen pre-MI and ten existing members')
stopifnot(!file.exists(file.path(ROOT,'audit/data_preparation_PASS.json')))
man<-fromJSON(file.path(R2B,'audit/mi_member_manifest.json'))
pre<-readRDS(file.path(R2B,'private/baseline_preMI.rds'))$data
stopifnot(nrow(pre)==3274,!anyDuplicated(pre$pid))
members<-lapply(1:10,function(k){
 f<-file.path(R2B,'private/mi10',sprintf('member_%02d.rds',k));stopifnot(hashf(f)==man$sha256[k]);d<-readRDS(f)
 stopifnot(nrow(d)==3274,identical(as.numeric(pre$pid),as.numeric(d$pid)),identical(as.numeric(pre$fid),as.numeric(d$fid)))
 for(v in setdiff(c(unlist(lapply(R2D_Z,function(z)paste0(z$raw,R2D_YEARS))),paste0('wfd_m',R2D_YEARS)),names(d)))d[[v]]<-pre[[v]]
 stopifnot(all(is.finite(as.matrix(d[,R2D_CONTROLS]))))
 d$pinc412<-as.integer(d$pinc212>0);d
})
frozen<-c(unlist(lapply(R2D_Z,function(z)paste0(z$raw,R2D_YEARS))),paste0('wfd_m',R2D_YEARS),paste0('wfdms',R2D_YEARS),paste0('ces8',R2D_YEARS))
checks<-list()
for(k in 1:10)for(v in frozen){
 a<-as.numeric(members[[k]][[v]]);b<-as.numeric(pre[[v]])
 ok<-length(a)==3274&&length(b)==3274&&identical(is.na(a),is.na(b))&&identical(is.finite(a),is.finite(b))&&all(a[is.finite(b)]==b[is.finite(b)])
 checks[[length(checks)+1]]<-data.frame(member=k,variable=v,check='frozen_column',passed=ok)
}
stopifnot(all(vapply(checks,function(q)q$passed,logical(1))))
zc<-list(created=as.character(Sys.time()),contract_sha256=hashf(file.path(ROOT,'RUN_CONTRACT.json')),samples=list(),z=list(),g=list(),source_members=man)
desc<-list();row_receipts<-list();control_audit<-list()
for(z in names(R2D_Z)){
 progress('prepare',paste('Binding',z,'sample and moderator series'))
 zr<-z_series(members[[1]],z);elig<-is.finite(zr[,1]);stopifnot(sum(elig)==contract()$samples[[z]])
 ref<-c(mean=mean(zr[elig,1]),sd=sd(zr[elig,1]));stopifnot(all(is.finite(ref)),ref['sd']>0)
 hs<-character(10);cm<-list();dir.create(file.path(ROOT,'private',z),recursive=TRUE,showWarnings=FALSE)
 for(k in 1:10){
  bm<-build_member(members[[k]],z,ref);stopifnot(identical(bm$eligible,elig))
  if(z=='SD'){
   old<-read_dat(file.path(R2C,'models',sprintf('SW_MI%02d',k),'attempt01/data.dat'))
   cmp<-compare_with_r2c(bm$data,old);stopifnot(cmp$passed)
   wj(cmp,file.path(ROOT,'audit',sprintf('SW_input_binding_MI%02d.json',k)))
  }
  f<-file.path(ROOT,'private',z,sprintf('Z0_member_%02d.dat',k));write_dat(bm$data[elig,],f);hs[k]<-hashf(f)
  cm[[k]]<-as.matrix(bm$data[elig,paste0('c',1:24)])
  row_receipts[[length(row_receipts)+1]]<-data.frame(z=z,member=k,N=sum(elig),households=length(unique(pre$fid[elig])),
     ordered_pid_sha256=digest(as.numeric(pre$pid[elig]),algo='sha256'),ordered_fid_sha256=digest(as.numeric(pre$fid[elig]),algo='sha256'),data_sha256=hs[k])
 }
 idx<-valid_controls(cm);zc$samples[[paste0(z,'_Z0')]]<-list(N=sum(elig),households=length(unique(pre$fid[elig])),ctrl_index=idx,ctrl_term=ctrl_term(idx),data_sha256=hs,
   later_only_excluded=sum(!elig&apply(is.finite(zr[,-1,drop=FALSE]),1,any)))
 for(j in 1:24)control_audit[[length(control_audit)+1]]<-data.frame(z=z,variable=R2D_CONTROLS[j],column=paste0('c',j),retained=j%in%idx,
   reason=if(j%in%idx)'retained' else if(any(vapply(cm,function(C)var(C[,j])==0,logical(1))))'zero_variance_in_member' else 'exact_linear_dependence_fixed_column_order')
 zc$z[[z]]<-list(raw_prefix=R2D_Z[[z]]$raw,orientation=R2D_Z[[z]]$orient,shape=R2D_Z[[z]]$shape,ref_mean=unname(ref['mean']),ref_sd=unname(ref['sd']))
 for(w in 1:5){v<-zr[,w];o<-is.finite(v);u<-R2D_Z[[z]]$orient*(v-ref['mean'])/ref['sd'];
   desc[[length(desc)+1]]<-data.frame(z=z,year=2000+R2D_YEARS[w],N_observed=sum(o),N_in_baseline_sample=sum(o&elig),N_missing_in_baseline_sample=sum(!o&elig),
     ratio_mean=mean(v[o&elig]),ratio_sd=sd(v[o&elig]),share_zero=mean(v[o&elig]==0),min=min(u[o&elig]),p10=unname(quantile(u[o&elig],.1)),median=median(u[o&elig]),p90=unname(quantile(u[o&elig],.9)),max=max(u[o&elig]))
 }
}
targets<-c('finc12','urban12','prov12','edu12','cdar12','pinc12','pinc212','marr12','adl12')
stopifnot(all(targets%in%names(pre)));cc<-complete.cases(pre[,targets]);stopifnot(all(vapply(members,function(d)all(as.matrix(d[cc,R2D_CONTROLS])==as.matrix(members[[1]][cc,R2D_CONTROLS])),logical(1))))
bm<-build_member(members[[1]],'SD',c(mean=zc$z$SD$ref_mean,sd=zc$z$SD$ref_sd));f<-file.path(ROOT,'private/SD/CC_member_01.dat');write_dat(bm$data[cc,],f)
idx<-valid_controls(list(as.matrix(bm$data[cc,paste0('c',1:24)])))
zc$samples$SD_CC<-list(N=sum(cc),households=length(unique(pre$fid[cc])),ctrl_index=idx,ctrl_term=ctrl_term(idx),data_sha256=hashf(f),role='diagnostic only, not MI-congeniality proof')
for(g in names(R2D_G)){v<-lapply(members,function(d)d[[R2D_G[[g]]$src]]);stopifnot(all(vapply(v,function(a)all(a%in%c(0,1)),logical(1))));
 zc$g[[g]]<-list(source=R2D_G[[g]]$src,column=R2D_G[[g]]$col,one_means=contract()$group_one_meanings[[g]],share_one=vapply(v,mean,numeric(1)))
}
write.csv(do.call(rbind,checks),file.path(ROOT,'audit/frozen_columns.csv'),row.names=FALSE)
write.csv(do.call(rbind,desc),file.path(ROOT,'audit/moderator_descriptives.csv'),row.names=FALSE)
write.csv(do.call(rbind,row_receipts),file.path(ROOT,'audit/row_identity_receipts.csv'),row.names=FALSE)
write.csv(do.call(rbind,control_audit),file.path(ROOT,'audit/control_column_decisions.csv'),row.names=FALSE)
wj(zc,file.path(ROOT,'audit/Z_CONTRACT.json'))
saveRDS(list(pid=pre$pid,fid=pre$fid,cc=cc),file.path(ROOT,'private/row_keys_and_cc.rds'))
wj(list(passed=TRUE,N=3274,members=10,frozen_checks=length(checks),source_preMI_sha256=hashf(file.path(R2B,'private/baseline_preMI.rds')),
        contract_sha256=hashf(file.path(ROOT,'RUN_CONTRACT.json')),Z_contract_sha256=hashf(file.path(ROOT,'audit/Z_CONTRACT.json')),created=as.character(Sys.time())),file.path(ROOT,'audit/data_preparation_PASS.json'))
progress('prepare_complete',paste('Ten MI bound, four baseline samples frozen; complete-case N',sum(cc)))
