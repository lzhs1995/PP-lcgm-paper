# Round2D 生产工具；上游纯函数原件保留，本文件明确覆盖不适用的规格与验收。
ROOT <- 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
R2B <- 'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
R2C <- 'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
.libPaths(c('C:/Users/LZHS/pp_lgcm_runs/20260908/library_mplusautomation_20260926', .libPaths()))
suppressPackageStartupMessages({library(jsonlite); library(digest); library(MplusAutomation)})
source(file.path(ROOT, 'code/00_upstream_math.R'), local=TRUE)
wj <- function(x, f) {dir.create(dirname(f), recursive=TRUE, showWarnings=FALSE); write_json(x,f,auto_unbox=TRUE,pretty=TRUE,digits=NA,na='null')}
hashf <- function(f) digest(file=f,algo='sha256')
progress <- function(stage,message) {
  wj(list(stage=stage,message=message,updated_at=as.character(Sys.time()),pid=Sys.getpid()),file.path(ROOT,'runtime/progress.json'))
  cat(format(Sys.time()),stage,message,'\n'); flush.console()
  if(exists('clauder_progress',mode='function')) clauder_progress(stage,message)
}
bind_fill <- function(xs) {xs<-Filter(function(x)!is.null(x)&&nrow(x)>0,xs); if(!length(xs))return(data.frame()); ns<-unique(unlist(lapply(xs,names))); do.call(rbind,lapply(xs,function(x){for(n in setdiff(ns,names(x)))x[[n]]<-NA; x[ns]}))}
contract <- function() fromJSON(file.path(ROOT,'RUN_CONTRACT.json'),simplifyVector=TRUE)
zcontract <- function() fromJSON(file.path(ROOT,'audit/Z_CONTRACT.json'),simplifyVector=FALSE)
execution_limit <- function(reason,message) {
  stop(structure(list(message=message,call=NULL,reason=reason),class=c('r2d_execution_limit','error','condition')))
}

# 缺少模型族文件不等于“备用未触发”。必须区分预算终止、尚无前置结果与真正未触发。
missing_family_status <- function(z,spec,parent_eligible=FALSE,terminal_reason='',attempts=0L) {
  optional<-z!='SD'&&spec%in%c('E0','E1')
  if(optional&&isTRUE(parent_eligible))return(c(status='NOT_RUN_NOT_TRIGGERED',reason='Latent branch passed; optional observed fallback not triggered'))
  suffix<-if(grepl('BUDGET',terminal_reason))'BUDGET' else if(terminal_reason=='RESOURCE_WAIT_LIMIT')'RESOURCE_LIMIT' else 'UNEXPECTED'
  status<-paste0(if(attempts>0)'INCOMPLETE_' else 'NOT_RUN_',suffix)
  c(status=status,reason=paste('Required or triggered specification lacks terminal family evidence;',terminal_reason))
}

# 删除上游E路线中的IX乘积，只估计用户已确认的SX调节。
e_lines <- function(interaction='none',ctrl='c1-c24',yshape='linear') {
  stopifnot(interaction %in% c('none','C'))
  m<-c(sw_lines(yshape=yshape,ctrl=ctrl),'ix sx ON z0;','iy ON z0 (gi0);','sy ON z0 (gs0);','x1 y1 ON z0;')
  if(interaction=='C')m<-c(m,'sxz | sx XWITH z0;','sy ON sxz (dc);')
  m
}
e2_lines <- function(g,g_in_controls,ctrl='c1-c24') {
  m<-c(sw_lines(ctrl=ctrl),'ix sx ON z0 zg;','iy ON z0 (gi0);','iy ON zg (gizg);',
       'sy ON z0 (gs0);','sy ON zg (gszg);','x1 y1 ON z0;')
  if(!g_in_controls)m<-c(m,paste('ix sx iy sy ON',g,';'))
  c(m,'sxz | sx XWITH z0;',paste('sxg | sx XWITH',paste0(g,';')),'sxzg | sx XWITH zg;',
    'sy ON sxz (dc);','sy ON sxg (bxg);','sy ON sxzg (dcg);')
}
FAC_XY<-c('IX','SX','IY','SY'); OBS_XY<-c(paste0('X',1:5),paste0('Y',1:5))
KEY_XY<-data.frame(label=c('bii','bis','bss','bsyiy'),row=c('IY','SY','SY','SY'),column=c('IX','IX','SX','IY'))
key_add<-function(label,row,column)data.frame(label=label,row=row,column=column)
spec_info<-function(z,spec,ctrl=NULL,sample='Z0',shape=NULL) {
  if(is.null(ctrl))ctrl<-zcontract()$samples[[paste(z,sample,sep='_')]]$ctrl_term
  if(is.null(shape))shape<-R2D_Z[[z]]$shape
  keyd<-rbind(KEY_XY,key_add(c('gii','gis','gss'),c('IY','SY','SY'),c('IZ','IZ','SZ')))
  keye<-rbind(KEY_XY,key_add(c('gi0','gs0'),c('IY','SY'),c('Z0','Z0')))
  if(spec %in% c('D0','D1'))return(list(kind=if(spec=='D0')'linear' else 'lms_latent',
    model=d_lines(shape,if(spec=='D0')'none' else 'C',ctrl),fac=c('IX','SX','IZ','SZ','IY','SY'),
    obs=c(OBS_XY,paste0('Z',1:5)),use=c('x1-x5','y1-y5','z1-z5',ctrl),
    key=if(spec=='D0')keyd else rbind(keyd,key_add('dc','SY','SXIZ'))))
  if(spec %in% c('E0','E1'))return(list(kind=if(spec=='E0')'linear' else 'lms_observed',
    model=e_lines(if(spec=='E0')'none' else 'C',ctrl),fac=FAC_XY,obs=OBS_XY,use=c('x1-x5','y1-y5','z0',ctrl),
    key=if(spec=='E0')keye else rbind(keye,key_add('dc','SY','SXZ'))))
  if(grepl('^H4_',spec)) {
    g<-R2D_G[[sub('H4_','',spec)]];stopifnot(!is.null(g))
    return(list(kind='lms_observed',model=e2_lines(g$col,g$in_controls,ctrl),fac=FAC_XY,obs=OBS_XY,
      use=c('x1-x5','y1-y5','z0',if(!g$in_controls)g$col,ctrl,'zg'),define=paste0('zg=z0*',g$col,';'),
      key=rbind(keye,key_add(c('gizg','gszg','dc','bxg','dcg'),c('IY','SY','SY','SY','SY'),c('ZG','ZG','SXZ','SXG','SXZG')))))
  }
  stop('unregistered specification: ',spec)
}

# 精确线性依赖规则：先除常数，各列单位化后用较严格秩容差，全部MI同一列集。
valid_controls<-function(mats) {
  stopifnot(length(mats)>0,all(vapply(mats,function(C)ncol(C)==24&&all(is.finite(C)),logical(1))))
  idx<-which(Reduce('&',lapply(mats,function(C)apply(C,2,var)>0)))
  out<-integer()
  for(j in idx){cand<-c(out,j);ok<-all(vapply(mats,function(C){D<-scale(C[,cand,drop=FALSE]); qr(cbind(1,D),tol=1e-10)$rank==length(cand)+1},logical(1)));if(ok)out<-cand}
  stopifnot(length(out)>0);out
}

# Mplus将带直接ON回归的指标提升到BETA/PSI（如x1 y1 ON z0）。
# 把这些固定单位载荷的辅助表示精确还原为测量层，不能把THETA中的占位零判为零测量误差。
canonical_measurement<-function(m,fac,obs) {
  TH<-outer(obs,obs,Vectorize(function(r,c)mval(m,'THETA',r,c)));dimnames(TH)<-list(obs,obs)
  L<-outer(obs,fac,Vectorize(function(r,c)mval(m,'LAMBDA',r,c)));dimnames(L)<-list(obs,fac)
  promoted<-obs[vapply(obs,function(o)pnum(m,'PSI',o,o)>0,logical(1))]
  if(length(promoted)){
    LP<-outer(obs,promoted,Vectorize(function(r,c)mval(m,'LAMBDA',r,c)))
    BP<-outer(promoted,fac,Vectorize(function(r,c)mval(m,'BETA',r,c)))
    PP<-outer(promoted,promoted,Vectorize(function(r,c)mval(m,'PSI',r,c)))
    cross<-outer(promoted,fac,Vectorize(function(r,c)mval(m,'PSI',r,c)))
    selfB<-outer(promoted,promoted,Vectorize(function(r,c)mval(m,'BETA',r,c)))
    stopifnot(all(cross==0),all(selfB==0))
    L<-L+LP%*%BP;TH<-TH+LP%*%PP%*%t(LP)
  }
  list(THETA=TH,LAMBDA=L,promoted=promoted)
}
geometry_linear<-function(m,fac,obs,fixed_zero=character()) {
  B<-outer(fac,fac,Vectorize(function(r,c)mval(m,'BETA',r,c)));P<-outer(fac,fac,Vectorize(function(r,c)mval(m,'PSI',r,c)))
  dimnames(B)<-dimnames(P)<-list(fac,fac);A<-solve(diag(length(fac))-B);G<-A%*%P%*%t(A)
  meas<-canonical_measurement(m,fac,obs);TH<-meas$THETA;L<-meas$LAMBDA;S<-L%*%G%*%t(L)+TH
  ch<-list(PSI=mcheck(P,length(fac)-length(fixed_zero)),G=mcheck(G,length(fac)-length(fixed_zero)),THETA=mcheck(TH),SIGMA=mcheck(S))
  list(B=B,PSI=P,G=G,THETA=TH,LAMBDA=L,SIGMA=S,checks=ch,promoted_measurement_variables=meas$promoted,
       passed=all(vapply(ch,function(q)q$psd&&q$rank_ok,logical(1)))&&ch$THETA$positive_definite&&ch$SIGMA$positive_definite)
}

# 非线性验收：乘积没有另设自由方差；Gaussian reference只用于正确乘积矩计算。
product_covariance<-function(mu,G,a,b,delta,target) {
  covgp<-mu[a]*G[,b]+mu[b]*G[,a]
  vp<-G[a,a]*G[b,b]+G[a,b]^2+mu[a]^2*G[b,b]+mu[b]^2*G[a,a]+2*mu[a]*mu[b]*G[a,b]
  e<-rep(0,length(mu));e[target]<-delta
  list(cov=G+outer(covgp,e)+outer(e,covgp)+vp*outer(e,e),
       mean=mu+e*(mu[a]*mu[b]+G[a,b]),product_variance=vp)
}
geometry_nonlinear<-function(m,si) {
  fac<-si$fac;obs<-si$obs
  B<-outer(fac,fac,Vectorize(function(r,c)mval(m,'BETA',r,c)));dimnames(B)<-list(fac,fac)
  P<-outer(fac,fac,Vectorize(function(r,c)mval(m,'PSI',r,c)));dimnames(P)<-list(fac,fac)
  meas<-canonical_measurement(m,fac,obs);TH<-meas$THETA;L<-meas$LAMBDA
  checks<-list(PSI=mcheck(P),THETA=mcheck(TH))
  mats<-list(B_without_product=B,PSI=P,THETA=TH,LAMBDA=L)
  if(si$kind=='lms_latent') {
    A<-solve(diag(length(fac))-B);G0<-A%*%P%*%t(A)
    alpha<-vapply(fac,function(f)mval(m,'ALPHA','1',f),numeric(1));mu<-as.vector(A%*%alpha)
    q<-product_covariance(mu,G0,match('SX',fac),match('IZ',fac),mval(m,'BETA','SY','SXIZ'),match('SY',fac))
    S<-L%*%q$cov%*%t(L)+TH
    checks$NONLINEAR_COV_C0<-mcheck(q$cov);checks$NONLINEAR_SIGMA_C0<-mcheck(S)
    mats$NONLINEAR_COV_C0<-q$cov;mats$NONLINEAR_SIGMA_C0<-S
    note<-'Exact Gaussian product moments conditional on controls=0; validity of primitive residual blocks is also checked. No independent product variance. Not a population-marginal covariance.'
  } else {
    for(z in c(-1,0,1))for(g in 0:1){
      BC<-B;BC['SY','SX']<-BC['SY','SX']+mval(m,'BETA','SY','SXZ')*z+mval(m,'BETA','SY','SXG')*g+mval(m,'BETA','SY','SXZG')*z*g
      A<-solve(diag(length(fac))-BC);G<-A%*%P%*%t(A);S<-L%*%G%*%t(L)+TH
      nm<-paste0('CONDITIONAL_Z',z,'_G',g);checks[[nm]]<-mcheck(S);mats[[nm]]<-S
    }
    note<-'Covariance conditional on fixed observed Z0/G; SX coefficients include observed products. No Gaussian product latent factor invented.'
  }
  pass<-all(vapply(checks,function(x)x$psd&&x$rank_ok,logical(1)))&&checks$THETA$positive_definite
  list(matrices=mats,checks=checks,passed=pass,note=note,promoted_measurement_variables=meas$promoted)
}
gate2<-function(m,si) {
  fl<-out_flags(m$lines);neg<-free_negative(m)
  vc<-tryCatch({stopifnot(all(is.finite(m$V)),all(is.finite(m$par$se)),all(m$par$se>0));
    e<-eigen(m$V/outer(sqrt(diag(m$V)),sqrt(diag(m$V))),symmetric=TRUE,only.values=TRUE)$values
    list(ok=min(e)>1e-10&&all(abs(diag(m$V)-m$par$se^2)<=1e-6+1e-5*m$par$se^2),minimum=min(e))},error=function(e)list(ok=FALSE,error=conditionMessage(e)))
  geo<-tryCatch(if(si$kind=='linear'){
    q<-geometry_linear(m,si$fac,si$obs);list(matrices=q[c('B','PSI','G','THETA','LAMBDA','SIGMA')],checks=q$checks,passed=q$passed,note='Linear model covariance reconstruction')
  }else geometry_nonlinear(m,si),error=function(e)list(passed=FALSE,error=conditionMessage(e)))
  list(passed=fl$normal&&!fl$fatal&&!length(neg)&&vc$ok&&geo$passed&&!fl$psi_warning&&!fl$theta_warning,
       flags=fl,negative=neg,vcov=vc,geometry=geo)
}
key_paths<-function(m,key)do.call(rbind,lapply(seq_len(nrow(key)),function(i){
  k<-key[i,];id<-pnum(m,'BETA',k$row,k$column);if(id==0)stop('missing path ',k$label)
  p<-m$par[m$par$parameter==id,];stopifnot(nrow(p)==1,is.finite(p$estimate),is.finite(p$se))
  data.frame(label=k$label,parameter=id,row=k$row,column=k$column,estimate=p$estimate,se=p$se)
}))
compare_numeric<-function(a,b,mode) {
  if(is.null(a)||is.null(b)||!isTRUE(a$receipt$usable)||!isTRUE(b$receipt$usable))return(list(passed=FALSE,reason='unusable or absent comparison member'))
  stopifnot(setequal(a$key$label,b$key$label));bk<-b$key[match(a$key$label,b$key$label),]
  d<-abs(a$key$estimate-bk$estimate);se<-bk$se
  lim<-if(mode=='start')pmax(.001,.01*se) else .05*se
  ll<-abs(a$receipt$LL-b$receipt$LL);sdiff<-abs(a$key$se-bk$se)/bk$se
  ok<-all(is.finite(d))&&all(d<=lim)&&all(sdiff<=.05)&&if(mode=='start')is.finite(ll)&&ll<=.01 else TRUE
  list(passed=ok,mode=mode,reference_attempt=a$receipt$attempt,candidate_attempt=b$receipt$attempt,
       delta_LL=ll,max_delta_path_over_SE=max(d/se),max_SE_relative_difference=max(sdiff),paths=data.frame(label=a$key$label,difference=d,tolerance=lim))
}
family_gate<-function(members,numeric=NULL,lms=FALSE) {
  allok<-length(members)==10&&all(vapply(members,function(a)!is.null(a)&&isTRUE(a$receipt$usable)&&!is.null(a$raw),logical(1)))
  if(lms)allok<-allok&&!is.null(numeric)&&isTRUE(numeric$start$passed)&&isTRUE(numeric$integration$passed)
  allok
}
