# Round2E四分支先首份、后完整家族；不运行H4、潜IZ、窗口或量尺扩展。
source(file.path(Sys.getenv('R2E_ROOT'),'code/r2e_local.R'),local=TRUE)
selection_file <- file.path(ROOT,'runtime/selection.json')
save_selection <- function(s) wj(s,selection_file)
usable <- function(r) !is.null(r) && identical(r$status,'USABLE')
budget <- function() {
  b<-rj(file.path(ROOT,'runtime/budget_status.json'))
  if(is.null(b)) return(list(calls=0L,engine_seconds=0,wall_seconds=0,rows=list()))
  # 墙钟包含两次监督器之间的等待/制表，不重置批次起点。
  b$wall_seconds<-b$wall_seconds+as.numeric(difftime(Sys.time(),as.POSIXct(b$updated_utc,format='%Y-%m-%dT%H:%M:%OS',tz='UTC'),units='secs'))
  b
}
repair_available <- function(z=NULL,sp=NULL,k=NULL) {
  rows<-budget()$rows; used<-Filter(function(r) identical(r$category,'REPAIR'),rows)
  if(length(used)>=4L) return(FALSE)
  if(!is.null(z)) {
    prefix<-paste('CFPS',z,sp,sprintf('%02d',k),sep='_')
    if(any(vapply(used,function(r) startsWith(r$id,paste0(prefix,'_')),TRUE))) return(FALSE)
  }
  TRUE
}
repair_once <- function(z,sp,k,attempt,points=20L,processors=1L,source_dir=NULL) {
  if(!repair_available(z,sp,k)) return(NULL)
  run(z,sp,k,attempt,'REPAIR',points=points,processors=processors,source_dir=source_dir,perturb=TRUE)
}

run_queue <- function() {
  stopifnot(file.exists(file.path(ROOT,'contracts/FROZEN_CODE.json')),
    all(read.csv(file.path(ROOT,'audit/SMOKE_RESULTS.csv'))$passed))
  S<-rj(selection_file)
  if(is.null(S)) {
    S<-list(branches=setNames(lapply(R2E_ZS,function(z) list(z=z,E0=list(),E1=list(),numeric=list(),status='PENDING')),R2E_ZS),processors=1L)
    save_selection(S)
  }
  tryCatch({
    # A1：四分支无交互首份。非法E0不充当E1起点或似然比较来源。
    for(z in R2E_ZS) {
      r<-run(z,'E0',1L,'base','TARGET',source_dir=swpath(1))
      if(!usable(r)) { rr<-repair_once(z,'E0',1L,'repair_start',source_dir=swpath(1)); if(!is.null(rr)) r<-rr }
      S$branches[[z]]$E0[['1']]<-r; save_selection(S)
    }
    # A2：四分支观测交互15点首份。全部分支有实际试验，不以其他分支结果准入。
    for(z in R2E_ZS) {
      e0<-S$branches[[z]]$E0[['1']]; src<-if(usable(e0)) e0$dest else swpath(1)
      r<-run(z,'E1',1L,'q15','NUMERIC',points=15L,source_dir=src)
      if(!usable(r)) { rr<-repair_once(z,'E1',1L,'q15_repair',points=15L,source_dir=src); if(!is.null(rr)) r<-rr }
      S$branches[[z]]$low<-r; S$branches[[z]]$start_source<-src; save_selection(S)
    }
    # 完整实际配对，只更改PROCESSORS，不由合成计时推断CFPS加速。
    if(usable(S$branches$SD$low)) {
      sd<-S$branches$SD$low
      # 若q15发生起点修复，配对必须复制同样扰动起点。
      p4<-run('SD','E1',1L,'q15_p4','PERFORMANCE',points=15L,processors=4L,
        source_dir=S$branches$SD$start_source,perturb=identical(sd$attempt,'q15_repair'))
      cmp<-numeric_check(sd,p4,'processors'); faster<-usable(p4)&&p4$seconds<=.8*sd$seconds
      S$performance<-list(single=sd$id,candidate=p4$id,check=cmp,faster20=faster,seconds1=sd$seconds,seconds4=p4$seconds)
      if(isTRUE(cmp$passed)&&faster) S$processors<-4L
      save_selection(S)
    }
    # A3：20点与独立完整起点。仅成功的15点候选进入精度检查。
    for(z in R2E_ZS) {
      b<-S$branches[[z]]; low<-b$low
      if(!usable(low)) { S$branches[[z]]$status<-'PILOT_NOT_USABLE'; save_selection(S); next }
      hi<-run(z,'E1',1L,'q20','TARGET',points=20L,processors=S$processors,source_dir=low$dest)
      if(!usable(hi)) { rr<-repair_once(z,'E1',1L,'q20_repair',processors=S$processors,source_dir=b$start_source); if(!is.null(rr)) hi<-rr }
      pts<-20L; ig<-numeric_check(low,hi,'integration')
      if(usable(hi)&&!isTRUE(ig$passed)&&repair_available(z,'E1',1L)) {
        r30<-run(z,'E1',1L,'q30','REPAIR',points=30L,processors=S$processors,source_dir=hi$dest)
        ig<-numeric_check(hi,r30,'integration'); hi<-r30; pts<-30L
      }
      st<-NULL; sc<-list(passed=FALSE,outcome='NOT_RUN')
      if(usable(hi)&&isTRUE(ig$passed)) {
        st<-run(z,'E1',1L,paste0('start_q',pts),'NUMERIC',points=pts,processors=S$processors,
          source_dir=b$start_source,perturb=TRUE)
        sc<-numeric_check(hi,st)
        if(!isTRUE(sc$passed)&&repair_available(z,'E1',1L)) {
          best<-if(usable(st)&&st$LL>hi$LL) st else hi
          alt<-repair_once(z,'E1',1L,paste0('start_repair_q',pts),points=pts,processors=S$processors,source_dir=best$dest)
          sc<-numeric_check(best,alt); hi<-best
        }
      }
      S$branches[[z]]$E1[['1']]<-hi; S$branches[[z]]$points<-pts
      S$branches[[z]]$numeric<-list(integration=ig,start=sc)
      S$branches[[z]]$status<-if(usable(hi)&&isTRUE(ig$passed)&&isTRUE(sc$passed)) 'PILOT_PASS' else 'NUMERIC_OR_MODEL_FAILED'
      save_selection(S)
    }
    # B1：先补廉价、已合法的E0。成员一旦修复仍失败便停止该家族。
    for(k in 2:10) for(z in R2E_ZS) {
      b<-S$branches[[z]]; if(!usable(b$E0[['1']])||isTRUE(b$E0_failed)) next
      r<-run(z,'E0',k,'base','TARGET',source_dir=b$E0[['1']]$dest)
      if(!usable(r)) { rr<-repair_once(z,'E0',k,'repair_start',source_dir=swpath(k)); if(!is.null(rr)) r<-rr }
      S$branches[[z]]$E0[[as.character(k)]]<-r; if(!usable(r)) S$branches[[z]]$E0_failed<-TRUE
      save_selection(S)
    }
    # B2：按完整家族成本准入，所有预算均包括合成、修复与配对，不比较P值。
    eligible<-R2E_ZS[vapply(R2E_ZS,function(z) identical(S$branches[[z]]$status,'PILOT_PASS'),TRUE)]
    cost<-vapply(eligible,function(z) 9*1.25*S$branches[[z]]$E1[['1']]$seconds,0)
    orderz<-eligible[order(cost,match(eligible,R2E_ZS))]
    for(z in orderz) {
      b<-S$branches[[z]]; bs<-budget(); remaining<-min(28800-bs$engine_seconds,36000-bs$wall_seconds)
      if(cost[[z]]>remaining || 101-bs$calls<9L) {
        S$branches[[z]]$status<-'NOT_ESTIMATED_WITHIN_BUDGET'; S$branches[[z]]$projected_seconds<-cost[[z]]; save_selection(S); next
      }
      for(k in 2:10) {
        r<-run(z,'E1',k,'base','TARGET',points=b$points,processors=S$processors,source_dir=b$E1[['1']]$dest)
        if(!usable(r)) {
          src<-if(usable(S$branches[[z]]$E0[[as.character(k)]])) S$branches[[z]]$E0[[as.character(k)]]$dest else swpath(k)
          rr<-repair_once(z,'E1',k,'repair_start',points=b$points,processors=S$processors,source_dir=src); if(!is.null(rr)) r<-rr
        }
        S$branches[[z]]$E1[[as.character(k)]]<-r; save_selection(S)
        if(!usable(r)) { S$branches[[z]]$status<-'MEMBER_FAILED'; save_selection(S); break }
      }
      if(length(S$branches[[z]]$E1)==10L&&all(vapply(S$branches[[z]]$E1,usable,TRUE))) S$branches[[z]]$status<-'ADOPT'
      save_selection(S)
    }
    # C：SD仅SY负方差时两个单成员固定零诊断；绝不替代完整自由家族。
    allsd<-c(S$branches$SD$E0,S$branches$SD$E1,list(S$branches$SD$low))
    hit<-Filter(function(x) !is.null(x)&&identical(x$status,'INADMISSIBLE_SY_ONLY'),allsd)
    if(length(hit)) {
      k<-min(vapply(hit,function(x) as.integer(x$member),1L)); bs<-budget()
      if(min(28800-bs$engine_seconds,36000-bs$wall_seconds)>=2100 && 101-bs$calls>=2L) {
        S$boundary<-list(member=k,role='single-member sensitivity; never substitutes for free-SY primary MI')
        for(sp in c('E0B','E1B')) {
          S$boundary[[sp]]<-run('SD',sp,k,'diagnostic','BOUNDARY',points=20L,processors=S$processors,source_dir=swpath(k))
          save_selection(S)
        }
      } else S$boundary<-list(status='NOT_ESTIMATED_WITHIN_BUDGET')
    }
    S$terminal<-list(status='FINISHED',utc=format(Sys.time(),tz='UTC',usetz=TRUE))
  },error=function(e) {
    S$terminal<<-list(status='STOPPED_WITH_REASON',reason=conditionMessage(e),utc=format(Sys.time(),tz='UTC',usetz=TRUE))
  })
  save_selection(S); progress('queue_terminal',S$terminal$status)
  source(file.path(ROOT,'code/pool_results.R'),local=TRUE); build_results()
  invisible(S)
}
