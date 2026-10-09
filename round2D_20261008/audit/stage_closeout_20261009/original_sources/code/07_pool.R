# 全部成员与家族数值门槛通过后才进行条件MI合并；所有登记对象均列入状态表。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
stopifnot(file.exists(file.path(ROOT,'runtime/queue_terminal.json')))
queue_end<-fromJSON(file.path(ROOT,'runtime/queue_terminal.json'))
terminal_reason<-if(is.null(queue_end$reason))'COMPLETED_REGISTERED_QUEUE' else queue_end$reason
calls<-read.csv(REG,stringsAsFactors=FALSE)
zdesc<-read.csv(file.path(ROOT,'audit/moderator_descriptives.csv'));zdesc<-zdesc[zdesc$year==2012,]
families<-list();pooled<-list();slopes<-list();h4<-list();member_paths<-list();member_cov<-list()
expected<-rbind(expand.grid(z=names(R2D_Z),spec=c('D0','D1','E0','E1'),stringsAsFactors=FALSE),data.frame(z='SD',spec=paste0('H4_',names(R2D_G))))
for(i in seq_len(nrow(expected))){
 z<-expected$z[i];sp<-expected$spec[i];f<-file.path(ROOT,'results',paste0(z,'_',sp,'_family.json'))
 if(!file.exists(f)){
  parent_file<-file.path(ROOT,'results',paste0(z,'_D1_family.json'));parent_ok<-file.exists(parent_file)&&isTRUE(fromJSON(parent_file)$eligible)
  n_attempts<-sum(calls$z==z&calls$spec==sp&calls$attempt!='completecase')
  state<-missing_family_status(z,sp,parent_ok,terminal_reason,n_attempts)
  if(grepl('UNEXPECTED',state[['status']]))stop('Missing required family despite completed queue: ',z,' ',sp)
  families[[length(families)+1]]<-data.frame(z=z,spec=sp,eligible=FALSE,status=state[['status']],reason=state[['reason']]);next
 }
 fam<-fromJSON(f,simplifyVector=FALSE)
 ms<-lapply(fam$members,function(a)if(a$status=='NOT_RUN')NULL else read_model(z,sp,as.integer(a$member),a$attempt))
 si<-spec_info(z,sp);ok<-family_gate(ms,fam$numeric,si$kind!='linear');stopifnot(identical(ok,isTRUE(fam$eligible)))
 families[[length(families)+1]]<-data.frame(z=z,spec=sp,eligible=ok,status=if(ok)'CONDITIONAL_MI_REPORTABLE' else 'NOT_POOLABLE',reason=if(is.null(fam$reason))''else fam$reason)
 if(!ok)next
 labs<-si$key$label;Q<-do.call(rbind,lapply(ms,function(a)a$key$estimate[match(labs,a$key$label)]));colnames(Q)<-labs
 U<-lapply(ms,function(a){id<-a$key$parameter[match(labs,a$key$label)];a$raw$V[id,id,drop=FALSE]})
 for(k in 1:10){member_paths[[length(member_paths)+1]]<-data.frame(z=z,spec=sp,member=k,label=labs,estimate=Q[k,],se=sqrt(diag(U[[k]])))
  ij<-expand.grid(row=labs,column=labs,stringsAsFactors=FALSE);ij$covariance<-as.vector(U[[k]]);member_cov[[length(member_cov)+1]]<-data.frame(z=z,spec=sp,member=k,ij)}
 pp<-rubin_pool(Q,U);tt<-pp$table;tt$FMI<-tt$lambda+(1-tt$lambda)*2/(tt$df+3);tt$MCSE_flag<-tt$MCSE_over_SE>.05
 pooled[[length(pooled)+1]]<-data.frame(z=z,spec=sp,label=labs,tt,rownames=NULL)
 for(nm in c('W','B','T')){dimnames(pp[[nm]])<-list(labs,labs);write.csv(pp[[nm]],file.path(ROOT,'results',paste0(z,'_',sp,'_pooled_',nm,'.csv')))}
 if(sp%in%c('D1','E1'))for(zz in c(-1,0,1)){
  a<-setNames(rep(0,length(labs)),labs);a['bss']<-1;a['dc']<-zz;ss<-pool_contrast(Q,U,a)
  support<-zdesc[zdesc$z==z,];stopifnot(nrow(support)==1)
  extrapolate<-zz<support$min||zz>support$max
  slopes[[length(slopes)+1]]<-data.frame(z=z,spec=sp,reference_z=zz,ss,
    reference_scale=if(sp=='D1')'latent_IZ' else 'observed2012_Z0',
    observed2012_min=support$min,observed2012_max=support$max,
    support_status=if(sp=='D1')'LATENT_GAUSSIAN_REFERENCE' else if(extrapolate)'EXTRAPOLATION_OUTSIDE_OBSERVED_SUPPORT' else 'WITHIN_OBSERVED_RANGE',
    note=if(sp=='D1')'Observed indicator support is not the latent IZ support; Gaussian latent assumption applies' else if(extrapolate)'Not an observed low/high group; do not interpret as an observed scenario' else 'Range membership does not ensure dense local support')
 }
 if(grepl('^H4_',sp))for(cn in c('delta_low','delta_high','difference')){
  a<-setNames(rep(0,length(labs)),labs);if(cn!='difference')a['dc']<-1;if(cn!='delta_low')a['dcg']<-1
  tt<-pool_contrast(Q,U,a);crit<-qt(1-.05/(2*9),tt$df)
  h4[[length(h4)+1]]<-data.frame(resource=sub('H4_','',sp),contrast=cn,tt,simultaneous_lower=tt$estimate-crit*tt$se,simultaneous_upper=tt$estimate+crit*tt$se)
 }
}
fs<-bind_fill(families);ps<-bind_fill(pooled);sl<-bind_fill(slopes);hh<-bind_fill(h4)
if(nrow(ps)){ps$p_holm<-NA_real_;for(sp in c('D1','E1')){ix<-which(ps$spec==sp&ps$label=='dc');if(length(ix))ps$p_holm[ix]<-p.adjust(ps$p[ix],'holm',n=4)}}
if(nrow(hh)){hh$p_holm_difference<-NA_real_;ix<-which(hh$contrast=='difference');hh$p_holm_difference[ix]<-p.adjust(hh$p[ix],'holm',n=3)}
decisions<-lapply(names(R2D_G),function(g){q<-if(nrow(hh))hh[hh$resource==g,] else data.frame();v<-function(c,n)q[q$contrast==c,n];lab<-'NOT_ESTIMABLE'
 if(nrow(q)==3){pos<-all(q$simultaneous_lower[q$contrast!='difference']>0);neg<-all(q$simultaneous_upper[q$contrast!='difference']<0)
  lab<-if((pos&&v('difference','simultaneous_lower')>0)||(neg&&v('difference','simultaneous_upper')<0))'MORE_SENSITIVE_IN_RESOURCE_ONE' else if((pos&&v('difference','simultaneous_upper')<0)||(neg&&v('difference','simultaneous_lower')>0))'LESS_SENSITIVE_IN_RESOURCE_ONE' else 'MAGNITUDE_DIRECTION_UNDETERMINED'}
 data.frame(resource=g,judgment=lab,meaning=contract()$group_one_meanings[[g]])})
write.csv(do.call(rbind,decisions),file.path(ROOT,'results/H4_direction_decisions.csv'),row.names=FALSE)
write.csv(fs,file.path(ROOT,'results/family_status.csv'),row.names=FALSE)
write.csv(ps,file.path(ROOT,'results/pooled_paths.csv'),row.names=FALSE)
write.csv(sl,file.path(ROOT,'results/conditional_slopes.csv'),row.names=FALSE)
write.csv(hh,file.path(ROOT,'results/H4_contrasts.csv'),row.names=FALSE)
write.csv(bind_fill(member_paths),file.path(ROOT,'results/member_key_paths.csv'),row.names=FALSE)
write.csv(bind_fill(member_cov),file.path(ROOT,'results/member_key_covariances.csv'),row.names=FALSE)
report<-lapply(names(R2D_Z),function(z){d<-fs[fs$z==z&fs$spec=='D1',];e<-fs[fs$z==z&fs$spec=='E1',];route<-if(d$eligible)'latent_IZ' else if(e$eligible)'observed2012_Z0' else 'not_estimable'
 data.frame(z=z,N=contract()$samples[[z]],primary_working_route=route,latent_status=d$status,observed_status=e$status)})
write.csv(do.call(rbind,report),file.path(ROOT,'results/moderation_adoption.csv'),row.names=FALSE)
wj(list(status='SUMMARIZED',families=nrow(fs),eligible=sum(fs$eligible),pooled_parameter_rows=nrow(ps),all_failed_members_preserved=TRUE,
    queue_terminal_reason=terminal_reason,
    limitations=c('conditional on model and current MI assumptions','MI01 numerical validation only','unestimated contrasts are not null effects','no model-selection uncertainty')),file.path(ROOT,'results/SUMMARY.json'))
cat('SUMMARY COMPLETE:',sum(fs$eligible),'eligible families\n')
