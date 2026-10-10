# 本机静态验证、真实数据绑定与六项合成接口；不复用云端自检的PASS标签。
source(file.path(Sys.getenv('R2E_ROOT'), 'code/r2e_local.R'), local = TRUE)

selftest <- function() {
  tests <- list(); check <- function(name, ok) { tests[[length(tests)+1L]] <<- data.frame(test = name, passed = isTRUE(ok)) }
  mm <- make_model(spec('SD', 'E0'), swpath(1))
  check('SW_to_E0_all_128_common_free_parameters_mapped', sum(mm$mapping$action == 'mapped_high_precision') == 128L)
  check('E0_only_six_new_z0_coefficients', sum(mm$mapping$action == 'new_start') == 6L)
  check('start_overlay_preserves_all_target_statements', all(spec('SD', 'E0')$model %in% mm$lines))
  check('no_fixed_in_new_start_statements', !any(grepl('@', tail(mm$lines, nrow(mm$mapping)))))
  check('all_mapped_variances_positive', all(mm$mapping$value[mm$mapping$op == 'VAR'] > 0))
  check('illegal_three_process_source_rejected', inherits(try(make_model(spec('SD', 'E0'), file.path(R2D,'models/SD/D0_Z0_MI01/base')), silent=TRUE), 'try-error'))
  check('missing_alternate_start_is_not_pass', !numeric_check(list(status='USABLE'), NULL)$passed)
  check('failed_alternate_start_is_not_pass', !numeric_check(list(status='USABLE'), list(status='TIMEOUT'))$passed)
  check('different_model_signature_rejected', !numeric_check(list(status='USABLE',structural_signature='a'),list(status='USABLE',structural_signature='b'))$passed)
  p <- c(.01,NA,.04,.02); a <- fixed_holm(p,4)
  check('Holm_keeps_missing', is.na(a[2]))
  check('Holm_keeps_family_four', max(abs(a[c(1,3,4)]-c(.04,.08,.06)))<1e-10)
  Q <- cbind(bss=seq(.1,.19,.01),dc=seq(.2,.29,.01)); U <- rep(list(matrix(c(.04,.015,.015,.09),2)),10)
  pp <- pool_ten(Q,U); contrast <- c(1,2); ct <- pool_contrast(Q,U,contrast)
  check('contrast_retains_covariance', abs(ct$se^2 - drop(t(contrast)%*%pp$T%*%contrast))<1e-12)
  check('nine_members_cannot_pool', inherits(try(pool_ten(Q[1:9,],U[1:9]),silent=TRUE),'try-error'))
  check('SD_minus_one_is_outside_support', -1 < -zc()$z$SD$ref_mean/zc()$z$SD$ref_sd)
  check('H4_negative_is_not_weakening', h4_component(-.2) != 'weakening_direction')
  check('H4_positive_direction', h4_component(.2) == 'weakening_direction')
  check('fixed_SY_changes_free_count_by_one', nrow(slots(spec('SD','E1'))) == nrow(slots(spec('SD','E1B')))+1L)
  t <- do.call(rbind,tests); csv(t,file.path(ROOT,'audit/selftest.csv')); stopifnot(all(t$passed))
  progress('selftest', paste(sum(t$passed), '/', nrow(t), 'PASS'))
}

bind_data <- function() {
  bind <- support <- list(); contract <- zc()
  for(z in R2E_ZS) {
    ss <- contract$samples[[paste0(z,'_Z0')]]; first <- NULL
    for(k in 1:10) {
      p <- datpath(z,k); d <- read_dat(p,R2D_NAMES)
      h <- hashf(p); stopifnot(h==ss$data_sha256[[k]], nrow(d)==ss$N, length(unique(d$fid))==ss$households,
        all(is.finite(d$z0)), max(abs(d$z0-d$z1))<1e-10)
      if(is.null(first)) first<-d else stopifnot(identical(first$fid,d$fid),identical(first$z0,d$z0))
      C <- as.matrix(d[,expand_vars(strsplit(ss$ctrl_term,' ',fixed=TRUE)[[1]])]); stopifnot(qr(cbind(1,C))$rank==ncol(C)+1L)
      bind[[length(bind)+1L]] <- data.frame(z=z,member=k,N=nrow(d),households=ss$households,sha256=h,passed=TRUE)
    }
    zz <- contract$z[[z]]; zero <- zz$orientation*(-zz$ref_mean)/zz$ref_sd; x <- first$z0
    if(z=='SD') vals <- c(raw_zero=zero,positive_median=median(x[x>zero+1e-9]),P90=unname(quantile(x,.9))) else {
      vals<-c(raw_zero=zero,P10=unname(quantile(x,.1)),P90=unname(quantile(x,.9)))
      if(abs(vals['P10']-zero)<1e-9) vals['P10']<-median(x[x<zero-1e-9])
      if(abs(vals['P90']-zero)<1e-9) vals['P90']<-median(x[x>zero+1e-9])
    }
    for(n in names(vals)) {
      v<-vals[[n]]; near<-abs(x-v)<=.1
      support[[length(support)+1L]]<-data.frame(z=z,point=n,value=v,original_relative_value=v/zz$orientation*zz$ref_sd+zz$ref_mean,
       near_band_z=.1,n_near=sum(near),households_near=length(unique(first$fid[near])),min_z=min(x),max_z=max(x),N=nrow(first),zero_share=mean(abs(x-zero)<1e-9))
    }
  }
  csv(do.call(rbind,bind),file.path(ROOT,'contracts/DATA_BINDING.csv'))
  csv(do.call(rbind,support),file.path(ROOT,'contracts/SUPPORT_POINTS.csv'))
  stopifnot(hashf(file.path(ROOT,'code/r2e_upstream_math.R'))==hashf(file.path(R2D,'code/00_upstream_math.R')))
  progress('data_binding','40/40 source, N, households, z0 and control-rank checks PASS')
}

smoke_data <- function() {
  set.seed(26101077); n<-1600L; fid<-rep(1:(n/2),each=2); C<-matrix(rbinom(n*24,1,.4),n)
  z0<-rnorm(n); ix<-rnorm(n,0,.8)+.1*C[,1]+.1*z0; sx<-.15*ix+rnorm(n,0,.6)+.1*z0
  iy<--.35*ix+.15*z0+rnorm(n,0,.8); sy<-.1*ix-.3*sx+.2*iy+.1*z0+.2*sx*z0+rnorm(n,0,.5)
  X<-Y<-matrix(0,n,5)
  for(w in 1:5) {
    ex<-rnorm(n,0,.5); ey<-.2*ex+rnorm(n,0,.55)
    X[,w]<-ix+c(0,.65,.7,.95,1)[w]*sx+ex+if(w==1) .1*z0 else 0
    Y[,w]<-iy+R2D_TIME[w]*sy+ey+if(w==1) .1*z0 else 0
  }
  d<-data.frame(fid,X,Y,matrix(0,n,5),z0,C[,2],C[,3],C[,4],C); names(d)<-R2D_NAMES
  f<-file.path(ROOT,'runtime/synthetic_data.dat'); if(!file.exists(f)) write_dat(d,f); f
}

smoke <- function() {
  f<-smoke_data(); one<-function(sp,att,source=NULL,proc=1L,pert=FALSE)
    run('SD',sp,1L,att,'SMOKE',points=15L,processors=proc,source_dir=source,perturb=pert,sample='SYNTHETIC',source_data=f,ctrl='c1-c3')
  calls<-list(); calls$E0<-one('E0','smoke')
  if(calls$E0$status!='USABLE') { wj(calls,file.path(ROOT,'audit/smoke_calls.json')); stop('Synthetic E0 did not pass') }
  calls$E1<-one('E1','smoke',calls$E0$dest)
  if(calls$E1$status!='USABLE') { wj(calls,file.path(ROOT,'audit/smoke_calls.json')); stop('Synthetic E1 did not pass') }
  calls$E1_start<-one('E1','smoke_start',calls$E0$dest,pert=TRUE)
  calls$E1_p4<-one('E1','smoke_p4',calls$E0$dest,proc=4L)
  calls$E0B<-one('E0B','smoke',calls$E0$dest)
  calls$E1B<-one('E1B','smoke',calls$E1$dest)
  checks<-list(start=numeric_check(calls$E1,calls$E1_start),processors=numeric_check(calls$E1,calls$E1_p4,'processors'))
  key<-read.csv(file.path(calls$E1$dest,'key_paths.csv')); dc<-key[key$label=='dc',]
  out<-data.frame(test=c('E0_usable','E1_usable','start_agreement','processor_agreement','known_interaction_recovered',
    'E0B_fixed_SY','E1B_fixed_SY','E0B_no_input_error','E1B_no_input_error'),
    passed=c(calls$E0$status=='USABLE',calls$E1$status=='USABLE',checks$start$passed,checks$processors$passed,
      abs(dc$estimate-.2)<max(.15,3*dc$se),
      mval(read_mplus_raw(calls$E0B$dest),'PSI','SY','SY')==0,
      mval(read_mplus_raw(calls$E1B$dest),'PSI','SY','SY')==0,
      !calls$E0B$status %in% c('INPUT_REJECTED','EXTRACTION_FAILED','TIMEOUT'),
      !calls$E1B$status %in% c('INPUT_REJECTED','EXTRACTION_FAILED','TIMEOUT')))
  csv(out,file.path(ROOT,'audit/SMOKE_RESULTS.csv')); wj(calls,file.path(ROOT,'audit/smoke_calls.json')); wj(checks,file.path(ROOT,'audit/smoke_numeric.json'))
  stopifnot(all(out$passed)); progress('smoke_complete',paste(nrow(out),'checks PASS; six synthetic calls'))
}

preflight <- function() { selftest(); bind_data(); smoke() }
