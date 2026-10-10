# 所有十份同规格且数值通过才合并；未完成项保留显式状态。
source(file.path(Sys.getenv('R2E_ROOT'),'code/r2e_local.R'),local=TRUE)
build_results <- function() {
  S<-rj(file.path(ROOT,'runtime/selection.json')); RES<-file.path(ROOT,'results')
  dir.create(RES,showWarnings=FALSE)
  receipts<-list.files(file.path(ROOT,'models'),pattern='^receipt.json$',recursive=TRUE,full.names=TRUE)
  rr<-lapply(receipts,rj); val<-function(x,default=NA) if(is.null(x)||!length(x)) default else x
  execution<-do.call(rbind,lapply(rr,function(r) data.frame(id=r$id,z=r$z,spec=r$spec,member=r$member,sample=r$sample,attempt=r$attempt,
    category=r$category,status=r$status,seconds=val(r$seconds),LL=val(r$LL),SY=val(r$sy),processors=r$processors,points=r$points,
    negative=paste(unlist(r$negative),collapse=';'),warnings=paste(unlist(r$warnings),collapse=';'),error=val(r$error,''))))
  csv(execution,file.path(RES,'MODEL_EXECUTION.csv'))
  families<-paths<-slopes<-diffs<-numeric<-list(); pool<-list()
  for(z in R2E_ZS) for(sp in c('E0','E1')) {
    b<-S$branches[[z]]; ms<-b[[sp]]
    statuses<-vapply(1:10,function(k) {r<-ms[[as.character(k)]];if(is.null(r)) 'NOT_RUN' else r$status},'')
    numok<-sp=='E0'||(isTRUE(b$numeric$integration$passed)&&isTRUE(b$numeric$start$passed))
    allok<-all(statuses=='USABLE')&&numok
    status<-if(allok) 'ADOPT' else if(any(grepl('INADMISSIBLE|FAILED|TIMEOUT|REJECTED|MISMATCH',statuses))) 'NOT_POOLABLE' else if(!numok) 'NUMERIC_CHECK_FAILED' else 'INCOMPLETE'
    if(sp=='E1'&&identical(b$status,'PILOT_NOT_USABLE')) {status<-'PILOT_NOT_USABLE';statuses[1]<-b$low$status}
    if(sp=='E1'&&identical(b$status,'NOT_ESTIMATED_WITHIN_BUDGET')) status<-'NOT_ESTIMATED_WITHIN_BUDGET'
    families[[length(families)+1L]]<-data.frame(z=z,spec=sp,status=status,n_usable=sum(statuses=='USABLE'),numeric_ok=numok,member_statuses=paste(statuses,collapse=';'))
    if(sp=='E1') for(ck in c('integration','start')) {
      n<-b$numeric[[ck]]
      numeric[[length(numeric)+1L]]<-data.frame(z=z,check=ck,passed=isTRUE(n$passed),outcome=val(n$outcome,'NOT_RUN'),delta_LL=val(n$delta_LL),max_path_over_SE=val(n$max_path_over_SE),max_SE_relative=val(n$max_SE_relative))
    }
    if(!allok) next
    labels<-spec(z,sp)$key$label; Q<-matrix(NA_real_,10,length(labels),dimnames=list(sprintf('MI%02d',1:10),labels)); U<-list()
    for(k in 1:10) {
      r<-ms[[as.character(k)]]; key<-read.csv(file.path(r$dest,'key_paths.csv')); key<-key[match(labels,key$label),]
      v<-as.matrix(read.csv(file.path(r$dest,'parameter_covariance.csv'),header=FALSE))
      Q[k,]<-key$estimate; U[[k]]<-v[key$parameter,key$parameter,drop=FALSE]
    }
    pooled<-pool_ten(Q,U); tb<-pooled$table; tb$FMI<-( (1+1/10)*diag(pooled$B)/diag(pooled$W)+2/(tb$df+3) )/( (1+1/10)*diag(pooled$B)/diag(pooled$W)+1 )
    tb$label<-labels;tb$z<-z;tb$spec<-sp;tb$N<-zc()$samples[[paste0(z,'_Z0')]]$N;tb$households<-zc()$samples[[paste0(z,'_Z0')]]$households
    paths[[length(paths)+1L]]<-tb; pool[[paste(z,sp,sep='_')]]<-list(Q=Q,U=U,W=pooled$W,B=pooled$B,T=pooled$T)
    if(sp=='E1') {
      sup<-read.csv(file.path(ROOT,'contracts/SUPPORT_POINTS.csv'));sup<-sup[sup$z==z,]
      for(i in seq_len(nrow(sup))) {
        aa<-setNames(rep(0,length(labels)),labels);aa['bss']<-1;aa['dc']<-sup$value[i]
        t<-pool_contrast(Q,U,aa);slopes[[length(slopes)+1L]]<-cbind(z=z,point=sup$point[i],zvalue=sup$value[i],original_relative_value=sup$original_relative_value[i],n_near=sup$n_near[i],households_near=sup$households_near[i],t)
      }
      low<-min(sup$value);high<-max(sup$value);aa<-setNames(rep(0,length(labels)),labels);aa['dc']<-high-low
      diffs[[length(diffs)+1L]]<-cbind(z=z,z_low=low,z_high=high,pool_contrast(Q,U,aa))
    }
  }
  bind_or_empty<-function(xs) if(length(xs)) do.call(rbind,xs) else data.frame(note='No complete admissible family; no pooled estimate')
  ff<-do.call(rbind,families); pt<-bind_or_empty(paths)
  csv(ff,file.path(RES,'FAMILY_STATUS.csv'));csv(pt,file.path(RES,'POOLED_KEY_PATHS.csv'))
  csv(bind_or_empty(slopes),file.path(RES,'CONDITIONAL_SLOPES.csv'));csv(bind_or_empty(diffs),file.path(RES,'SLOPE_DIFFERENCES.csv'))
  csv(bind_or_empty(numeric),file.path(RES,'NUMERIC_CHECKS.csv'))
  mult<-list()
  for(lab in c('dc','gi0','gs0')) {
    sp<-if(lab=='dc') 'E1' else 'E0'; p<-rep(NA_real_,4)
    if('label'%in%names(pt)) for(j in seq_along(R2E_ZS)) {
      hit<-pt$z==R2E_ZS[j]&pt$spec==sp&pt$label==lab;if(any(hit)) p[j]<-pt$p[hit]
    }
    mult[[length(mult)+1L]]<-data.frame(z=R2E_ZS,spec=sp,label=lab,p=p,holm=fixed_holm(p,4),family_size=4)
  }
  csv(do.call(rbind,mult),file.path(RES,'MULTIPLICITY.csv'));saveRDS(pool,file.path(ROOT,'runtime/pooled_matrices.rds'))
  # 公开JSON仅模型参数与协方差，无逐人记录或插补对象。
  wj(pool,file.path(RES,'MI_PARAMETER_MATRICES.json'))
  later<-data.frame(task=c('H4_EDU','H4_URBAN','H4_INC','latent_IZ_probes','window_scale_Yshape','complete_case_winsorization'),
    status=c(rep('DEFERRED_BY_USER_STAGE_CHOICE',3),'NOT_IN_APPROVED_BATCH',rep('DEFERRED_TO_SEPARATE_CONTRACT',2)))
  csv(later,file.path(RES,'DEFERRED.csv'));wj(S$boundary,file.path(RES,'SD_BOUNDARY_DIAGNOSTIC.json'))
  wj(list(families=ff,terminal=S$terminal,performance=S$performance,budget=rj(file.path(ROOT,'runtime/budget_status.json')),
    inference='Conditional on the current household-person MI and fixed working model; observed Z0 is not latent IZ; numeric checks are MI01 only; no constrained family replaces the primary.'),file.path(RES,'SUMMARY.json'))
  progress('results_written',paste(sum(ff$status=='ADOPT'),'complete admissible families; H4 deferred'))
}
