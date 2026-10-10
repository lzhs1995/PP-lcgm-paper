# Round2E 主程序：按合同依次执行 B1（A→B→B2→D→C）与 H4 批次，最后合并汇总。可中断后原命令重启：已完成调用读回执，不重跑。
# 用法：Rscript r2e_run.R          （先运行 r2e_00_contract.R；环境变量同合同步骤）
#       R2E_RUN_H4 在合同冻结时决定是否自动接续 H4；R2E_SOURCE_ONLY=1 只加载函数（测试用）
local({ a <- commandArgs(FALSE); f <- sub('^--file=', '', a[grep('^--file=', a)]); f <- f[basename(f) == 'r2e_run.R']
  Sys.setenv(R2E_CODE = if (length(f)) dirname(normalizePath(f)) else Sys.getenv('R2E_CODE', '.')) })
source(file.path(Sys.getenv('R2E_CODE'), 'r2e_queue.R'))
if (!file.exists(file.path(R2E, 'contracts', 'RUN_CONTRACT_2E.json'))) stop('Run r2e_00_contract.R first')
stopifnot(identical(contract()$code_sha256$r2e_queue.R, hashf(file.path(.r2e_dir, 'r2e_queue.R'))),
          identical(contract()$code_sha256$r2e_engine.R, hashf(file.path(.r2e_dir, 'r2e_engine.R'))),
          identical(contract()$code_sha256$r2e_tools.R, hashf(file.path(.r2e_dir, 'r2e_tools.R'))))
run_phase <- function(name, f, batch) {
  if (!is.null(load_state(paste0(batch, '_stopped')))) return(invisible(NULL))
  if (!is.null(load_state(name))) return(invisible(load_state(name)))
  progress('phase_start', name)
  tryCatch(f(), r2e_budget_stop = function(e) {
    save_state(list(stopped = TRUE, phase = name, reason = e$reason, message = conditionMessage(e), at_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE)), paste0(batch, '_stopped'))
    progress('batch_stopped', paste(batch, e$reason)); invisible(NULL) })
}
run_all <- function() {
  rc <- recover_calls(); if (nrow(rc)) { cat('Recovered interrupted calls:\n'); print(rc, row.names = FALSE) }
  batch_clock('B1')
  run_phase('phase_A', phase_A, 'B1'); run_phase('phase_B', phase_B, 'B1'); run_phase('phase_B2', phase_B2, 'B1')
  run_phase('phase_D', phase_D, 'B1'); run_phase('phase_C', phase_C, 'B1')
  if (!is.null(load_state('phase_B')) && isTRUE(contract()$run_h4_after_batch1)) { batch_clock('H4'); run_phase('phase_H4', phase_H4, 'H4') }
  source(file.path(.r2e_dir, 'r2e_05_pool.R'))
  progress('done', 'Round2E finished; see results/')
}
if (!identical(Sys.getenv('R2E_SOURCE_ONLY'), '1')) run_all()
