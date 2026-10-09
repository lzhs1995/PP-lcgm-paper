# 原分析队列真实退出后自动接续；本脚本不调用Mplus，不发布GitHub。
# 独立持久文件模式；所有既有模型、数据和执行合同保持原样。
library(jsonlite)
library(digest)
library(ps)
library(processx)

pq_root <- 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
pq_dir <- file.path(pq_root, 'runtime/postqueue')
dir.create(pq_dir, recursive=TRUE, showWarnings=FALSE)
pq_contract_path <- file.path(pq_root, 'runtime/postqueue_launch_contract.json')
pq_contract <- jsonlite::fromJSON(pq_contract_path, simplifyVector=FALSE)
pq_started <- Sys.time()
pq_log <- file.path(pq_dir, 'postqueue_R.log')

pq_emit <- function(stage, message, status='RUNNING') {
  record <- list(status=status, stage=stage, message=message,
    updated_at=as.character(Sys.time()), pid=Sys.getpid(),
    upstream_job_id=pq_contract$upstream_job_id,
    elapsed_seconds=as.numeric(difftime(Sys.time(),pq_started,units='secs')),
    new_Mplus_calls=0L, publication_performed=FALSE)
  jsonlite::write_json(record,file.path(pq_dir,'state.json'),auto_unbox=TRUE,pretty=TRUE)
  cat(jsonlite::toJSON(record,auto_unbox=TRUE),'\n',file=file.path(pq_dir,'events.jsonl'),append=TRUE)
  if(exists('clauder_progress',mode='function',inherits=TRUE)) clauder_progress(stage,message)
  cat(format(Sys.time()), stage, message, '\n'); flush.console()
}

pq_check_sources <- function() {
  for(entry in pq_contract$sources) {
    path <- file.path(pq_root,entry$path)
    actual <- digest::digest(file=path,algo='sha256')
    if(!identical(actual,entry$sha256))stop('Source changed after postqueue registration: ',entry$path)
  }
}

pq_upstream_alive <- function() {
  tryCatch({
    handle <- ps::ps_handle(as.integer(pq_contract$upstream_worker_pid))
    identity <- abs(as.numeric(ps::ps_create_time(handle))-pq_contract$upstream_worker_created)<0.1
    identity && ps::ps_is_running(handle)
  },error=function(e)FALSE)
}

pq_run_python <- function(script, args=character()) {
  stage <- sub('\\.py$','',script)
  pq_check_sources()
  output <- file.path(pq_dir,paste0(stage,'.stdout.log'))
  errors <- file.path(pq_dir,paste0(stage,'.stderr.log'))
  pq_emit(stage,paste('Running',script,'after verified upstream terminal'))
  child <- processx::process$new(pq_contract$python,
    c('-X','utf8',file.path(pq_root,'code',script),args),
    stdout=output,stderr=errors,cleanup_tree=FALSE)
  began <- Sys.time()
  while(child$is_alive()) {
    child$wait(timeout=10000)
    if(child$is_alive()) pq_emit(stage,paste(script,'elapsed_seconds',
      round(as.numeric(difftime(Sys.time(),began,units='secs')))))
  }
  exitcode <- child$get_exit_status()
  receipt <- list(script=script,args=args,exitcode=exitcode,
    stdout=output,stderr=errors,completed_at=as.character(Sys.time()))
  jsonlite::write_json(receipt,file.path(pq_dir,paste0(stage,'_process.json')),
    auto_unbox=TRUE,pretty=TRUE)
  if(!identical(exitcode,0L))stop('Postqueue step failed: ',script,'; see saved logs')
}

pq_run <- function() {
  # 独立锁只防止本接续被重复执行，不占用或更改原模型队列锁。
  lock <- file.path(pq_dir,'execution.lock')
  if(!dir.create(lock,showWarnings=FALSE))stop('Postqueue lock exists; inspect original job instead of resubmitting')
  jsonlite::write_json(list(pid=Sys.getpid(),created=as.character(Sys.time())),
    file.path(lock,'owner.json'),auto_unbox=TRUE,pretty=TRUE)
  pq_check_sources()
  terminal <- file.path(pq_root,'runtime/queue_terminal.json')
  repeat {
    alive <- pq_upstream_alive()
    if(!alive && file.exists(terminal))break
    if(!alive)stop('Upstream worker exited without a queue terminal; no pooling or manuscript generation performed')
    pq_emit('waiting_original_queue',paste('Original job',pq_contract$upstream_job_id,
      'still running; no estimation or result writes by this waiting worker'))
    Sys.sleep(30)
  }
  pq_check_sources()
  end <- jsonlite::fromJSON(terminal)
  stopifnot(identical(end$status,'QUEUE_TERMINAL'))
  # 逐调用确认回执齐全；不能仅凭一个终态文件就开始合并。
  calls <- read.csv(file.path(pq_root,'audit/CALL_REGISTER.csv'),stringsAsFactors=FALSE)
  receipts <- list.files(file.path(pq_root,'models'),pattern='^receipt\\.json$',recursive=TRUE,full.names=TRUE)
  ids <- vapply(receipts,function(path)jsonlite::fromJSON(path)$id,character(1))
  stopifnot(!anyDuplicated(calls$id),!anyDuplicated(ids),all(calls$id%in%ids),
    identical(nrow(calls),as.integer(end$call_count)))
  registry_before <- digest::digest(file=file.path(pq_root,'audit/CALL_REGISTER.csv'),algo='sha256')
  jsonlite::write_json(list(upstream_worker_exited=TRUE,terminal=end,
    terminal_sha256=digest::digest(file=terminal,algo='sha256'),registered_calls=nrow(calls),
    receipts_matched=TRUE,registry_sha256=registry_before,verified_at=as.character(Sys.time())),
    file.path(pq_dir,'upstream_terminal_verified.json'),auto_unbox=TRUE,pretty=TRUE)
  pq_emit('pooling','All registered calls terminal; executing existing 07_pool.R with full-member gates')
  source(file.path(pq_root,'code/07_pool.R'),local=TRUE)
  pq_run_python('09_independent_verify.py',c('--require-terminal'))
  pq_run_python('15_build_manuscripts.py')
  pq_run_python('17_export_manuscript_pdf.py')
  pq_run_python('18_validate_manuscripts.py',c('--render'))
  pq_run_python('19_build_reports.py')
  stopifnot(identical(registry_before,
    digest::digest(file=file.path(pq_root,'audit/CALL_REGISTER.csv'),algo='sha256')))
  check <- jsonlite::fromJSON(file.path(pq_root,'manuscript/delivery/manuscript_validation.json'))
  stopifnot(identical(check$status,'PASS_PENDING_VISUAL'),!isTRUE(check$preview))
  pq_emit('awaiting_final_review',
    'Pooling, independent recalculation, DOCX/PDF and cell checks finished; final scientific/page review and authorized GitHub delivery remain',
    'AWAITING_FINAL_REVIEW')
}

sink(pq_log,split=TRUE)
tryCatch(pq_run(),error=function(e){
  pq_emit('postqueue_error',conditionMessage(e),'ERROR')
  stop(e)
},finally={sink()})
