# Round2E 执行引擎（移植自 Round2D code/03_engine.R：每次调用独立目录、不可变输入、回执与失败留档）。
# 变化：新根目录（环境变量 R2E_ROOT）；Round2D 只读（R2D_ROOT）；处理器数、积分点、单次时限按合同；
#       跨规格 SVALUES 起点拼接并登记 start_mapping.csv；按批次核算引擎秒数与墙钟；边界分类 BOUNDARY_SY；DRYRUN 只生成输入。
.r2e_dir <- local({ f <- sys.frames(); p <- NULL
  for (i in rev(seq_along(f))) if (!is.null(f[[i]]$ofile)) { p <- dirname(normalizePath(f[[i]]$ofile)); break }
  if (is.null(p)) p <- Sys.getenv('R2E_CODE', getwd()); p })
source(file.path(.r2e_dir, 'r2e_tools.R'), local = FALSE)
suppressPackageStartupMessages({ library(jsonlite); library(digest) })
R2E <- Sys.getenv('R2E_ROOT'); if (!nzchar(R2E)) stop('Set R2E_ROOT (new Round2E directory)')
R2E <- normalizePath(R2E, winslash = '/', mustWork = TRUE)
R2D <- normalizePath(Sys.getenv('R2D_ROOT', 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'), winslash = '/', mustWork = FALSE)
DRYRUN <- identical(Sys.getenv('R2E_DRYRUN'), '1')
MPLUS <- Sys.getenv('R2E_MPLUS'); if (!nzchar(MPLUS)) MPLUS <- unname(Sys.which('Mplus'))
if (!nzchar(MPLUS)) MPLUS <- 'C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Mplus.exe'
PY <- Sys.getenv('R2E_PYTHON', 'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe')
REG <- file.path(R2E, 'audit', 'CALL_REGISTER.csv')
wj <- function(x, f) { dir.create(dirname(f), recursive = TRUE, showWarnings = FALSE); write_json(x, f, auto_unbox = TRUE, pretty = TRUE, digits = NA, na = 'null') }
hashf <- function(f) digest(file = f, algo = 'sha256')
progress <- function(stage, message) {
  wj(list(stage = stage, message = message, updated_at = format(Sys.time(), tz = 'UTC', usetz = TRUE), pid = Sys.getpid()), file.path(R2E, 'runtime', 'progress.json'))
  cat(format(Sys.time()), stage, message, '\n'); utils::flush.console()
}
contract <- function() fromJSON(file.path(R2E, 'contracts', 'RUN_CONTRACT_2E.json'), simplifyVector = FALSE)
zc2d <- function() fromJSON(file.path(R2D, 'audit', 'Z_CONTRACT.json'), simplifyVector = FALSE)
budget_stop <- function(reason, message) stop(structure(list(message = message, call = NULL, reason = reason), class = c('r2e_budget_stop', 'error', 'condition')))
ctrl_of <- function(z, sample = 'Z0') { s <- zc2d()$samples[[paste(z, if (sample == 'W') 'Z0' else sample, sep = '_')]]; if (is.null(s$ctrl_term)) 'c1-c24' else s$ctrl_term }
zshape_of <- function(z) zc2d()$z[[z]]$shape
support_z <- function(z) { sp <- contract()$support[[z]]; if (is.null(sp)) c(-1, 0, 1) else unique(c(unlist(sp$z), sp$min_z, sp$max_z)) }

# ---------------------------------------------------------------- 数据位置（Round2D 私有文件只读；Round2E 只新增缩尾数据）
data_path <- function(z, k, sample = 'Z0') {
  if (sample == 'W') return(file.path(R2E, 'private', z, sprintf('W_member_%02d.dat', k)))
  file.path(R2D, 'private', z, sprintf('%s_member_%02d.dat', sample, k))
}
model_dir <- function(z, spec, k, attempt, sample = 'Z0') file.path(R2E, 'models', z, sprintf('%s_%s_MI%02d', spec, sample, k), attempt)

# ---------------------------------------------------------------- 预算台账（批次：B1=E线+诊断+敏感性，H4=资源组）
ledger <- function() { f <- file.path(R2E, 'audit', 'ENGINE_LEDGER.csv'); if (file.exists(f)) utils::read.csv(f, stringsAsFactors = FALSE) else data.frame() }
batch_clock <- function(batch) {
  f <- file.path(R2E, 'runtime', paste0('batch_', batch, '_start.json'))
  if (!file.exists(f)) wj(list(batch = batch, started_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE), epoch = as.numeric(Sys.time())), f)
  fromJSON(f)$epoch
}
budget_state <- function(batch) {
  ct <- contract(); b <- ct$budgets[[batch]]; lg <- ledger()
  used <- if (nrow(lg)) sum(lg$seconds[lg$batch == batch], na.rm = TRUE) else 0
  wall <- as.numeric(Sys.time()) - batch_clock(batch)
  list(engine_used = used, engine_left = b$engine_hours * 3600 - used, wall_used = wall, wall_left = b$wall_hours * 3600 - wall)
}
register_call <- function(row) {
  tab <- if (file.exists(REG)) utils::read.csv(REG, stringsAsFactors = FALSE) else data.frame()
  if (nrow(tab) && any(tab$id == row$id)) stop('Call already registered without terminal receipt; inspect before resubmission: ', row$id)
  caps <- contract()$caps[[row$batch]]
  nb <- if (nrow(tab)) sum(tab$batch == row$batch) else 0; nc <- if (nrow(tab)) sum(tab$batch == row$batch & tab$category == row$category) else 0
  if (is.null(caps[[row$category]])) stop('Unregistered call category ', row$category)
  if (nb >= caps$TOTAL || nc >= caps[[row$category]]) budget_stop('CALL_CAP', paste('Call cap reached before', row$id, row$category))
  bs <- budget_state(row$batch)
  if (bs$engine_left <= 0) budget_stop('ENGINE_BUDGET', paste('Engine-time budget exhausted before', row$id))
  if (bs$wall_left <= 0) budget_stop('WALL_BUDGET', paste('Wall-clock budget exhausted before', row$id))
  rec <- data.frame(id = row$id, batch = row$batch, z = row$z, spec = row$spec, member = row$member, attempt = row$attempt, sample = row$sample,
                    category = row$category, kind = row$kind, points = row$settings$points, processors = row$settings$processors,
                    created_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE), input_sha256 = row$input_sha256, data_sha256 = row$data_sha256,
                    dryrun = DRYRUN)
  dir.create(dirname(REG), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(if (nrow(tab)) rbind(tab, rec) else rec, REG, row.names = FALSE)
  bs
}
add_ledger <- function(r, batch) {
  f <- file.path(R2E, 'audit', 'ENGINE_LEDGER.csv'); lg <- ledger()
  rec <- data.frame(id = r$id, batch = batch, category = r$category, status = r$status, seconds = if (is.null(r$seconds)) NA else r$seconds,
                    mplus_reported_seconds = if (is.null(r$mplus_seconds)) NA else r$mplus_seconds, finished_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE))
  utils::write.csv(if (nrow(lg)) rbind(lg, rec) else rec, f, row.names = FALSE)
}

# ---------------------------------------------------------------- 准备输入
# warm=list(from=<源目录>, add=<追加语句>)：源输出 SVALUES 拼接；源非法时负方差起点被清洗，不作为合法拟合来源宣称。
prepare_model <- function(z, spec, k, attempt, category, batch, sample = 'Z0', points = 15L, processors = 1L, seed = 26101001L,
                          warm = NULL, source_data = NULL) {
  dest <- model_dir(z, spec, k, attempt, sample); cf <- file.path(dest, 'input_contract.json')
  if (file.exists(cf)) return(fromJSON(cf, simplifyVector = FALSE))
  si <- spec_info_r2e(z, spec, ctrl_of(z, sample), zshape_of(z))
  model <- si$model; mapping <- NULL; warm_hash <- NULL
  if (!is.null(warm)) {
    src_out <- file.path(warm$from, 'model.out')
    if (file.exists(src_out) && !is.null(svalues_block(readLines(src_out, warn = FALSE, encoding = 'latin1')))) {
      sp <- svalues_splice(src_out, if (is.null(warm$add)) character(0) else warm$add, si$fixed_zero)
      ck <- splice_check(sp$model, si)
      if (ck$ok) { model <- sp$model; mapping <- sp$log; warm_hash <- hashf(src_out) } else
        mapping <- data.frame(line = c(if (length(ck$missing)) paste('missing:', head(ck$missing, 20)), if (length(ck$foreign)) paste('foreign:', head(ck$foreign, 20))),
                              action = 'splice_structure_mismatch_default_starts_used')
    } else mapping <- data.frame(line = NA, action = paste('warm source without SVALUES; default starts used:', warm$from))
  }
  bad <- model[!grepl(';\\s*$', model) | grepl('^\\s*[@*;]', model)]
  if (length(bad)) stop('Malformed MODEL statements for ', z, ' ', spec, ': ', paste(bad, collapse = ' | '))
  if (length(si$fixed_zero) && !all(paste0(tolower(si$fixed_zero), '@0;') %in% model)) stop('Boundary statement missing for ', spec)
  an <- analysis_r2e(si$kind, points, processors, seed)
  title <- paste('Round2E', z, spec, sample, sprintf('MI%02d', k), attempt)
  text <- inp_text(title, si$use, an, model, si$define, kind = if (si$kind == 'linear') 'linear' else 'lms')
  src <- if (is.null(source_data)) data_path(z, k, sample) else source_data
  if (!file.exists(src)) stop('Missing private data file: ', src)
  dir.create(dest, recursive = TRUE, showWarnings = FALSE)
  stopifnot(file.copy(src, file.path(dest, 'data.dat'), overwrite = FALSE))
  writeLines(text, file.path(dest, 'model.inp'), useBytes = TRUE)
  if (!is.null(mapping)) utils::write.csv(mapping, file.path(dest, 'start_mapping.csv'), row.names = FALSE)
  dat <- read_dat(src)
  row <- list(id = paste(z, spec, sample, k, attempt, sep = '_'), z = z, spec = spec, member = k, attempt = attempt, category = category, batch = batch,
              kind = si$kind, sample = sample, N = nrow(dat), households = length(unique(dat[[1]])),
              settings = list(points = if (si$kind == 'linear') 0L else points, processors = processors, seed = seed),
              fixed_zero = si$fixed_zero, dest = dest, input_sha256 = hashf(file.path(dest, 'model.inp')), data_sha256 = hashf(src), source_data = src,
              warm_from = if (is.null(warm)) NULL else warm$from, warm_source_output_sha256 = warm_hash,
              contract_sha256 = hashf(file.path(R2E, 'contracts', 'RUN_CONTRACT_2E.json')),
              code_sha256 = as.list(vapply(c('r2e_tools.R', 'r2e_engine.R', 'r2e_upstream_math.R'), function(f) hashf(file.path(.r2e_dir, f)), character(1))))
  wj(row, cf); row
}

# ---------------------------------------------------------------- 读回与验收
tech8_profile <- function(L) {
  m <- regmatches(L, regexec('^\\s+([0-9]+)\\s+(-?0\\.[0-9]+D[+-][0-9]+)\\s+(-?[0-9.]+)\\s+(-?[0-9.]+)\\s+([A-Z]+)\\s+([0-9.]+)\\s+([0-9.]+)', L))
  m <- m[lengths(m) == 8]
  if (!length(m)) return(list(iterations = 0L))
  sec <- as.numeric(vapply(m, `[`, '', 7)); tot <- as.numeric(vapply(m, `[`, '', 8))
  list(iterations = length(m), median_iteration_seconds = stats::median(sec), max_iteration_seconds = max(sec),
       share_time_in_iterations_over_30s = sum(sec[sec > 30]) / max(sum(sec), 1e-9), mplus_total_seconds = max(tot))
}
readback_model <- function(row, seconds = NA_real_, exitcode = NA_integer_, timed_out = FALSE) {
  dest <- row$dest; out <- file.path(dest, 'model.out')
  r <- c(row[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'batch', 'kind', 'sample', 'N', 'households', 'settings')],
         list(usable = FALSE, seconds = seconds, exitcode = exitcode, warm_from = row$warm_from))
  save <- function(r) { wj(r, file.path(dest, 'receipt.json')); r }
  if (!file.exists(out)) { r$status <- if (timed_out) 'TIMEOUT' else 'NO_OUTPUT'; return(save(r)) }
  L <- readLines(out, warn = FALSE, encoding = 'latin1'); flat <- paste(L, collapse = ' ')
  con <- file.path(dest, 'mplus_console.log'); prof <- tech8_profile(if (file.exists(con)) readLines(con, warn = FALSE) else L)
  r$output_sha256 <- hashf(out); r$iterations <- prof$iterations; r$median_iteration_seconds <- prof$median_iteration_seconds
  r$share_time_in_slow_iterations <- prof$share_time_in_iterations_over_30s; r$mplus_seconds <- prof$mplus_total_seconds
  s <- grep('Dimensions of numerical integration', L, value = TRUE); r$integration_dimensions <- if (length(s)) as.integer(sub('.*?([0-9]+)\\s*$', '\\1', s[1])) else NA
  r$normal <- grepl('THE MODEL ESTIMATION TERMINATED NORMALLY', flat, fixed = TRUE)
  if (grepl('\\*\\*\\* ERROR|ERROR in .* command|Unknown variable|Unknown option', flat)) {
    r$status <- 'INPUT_REJECTED'; r$error_lines <- L[grepl('ERROR|Unknown|not allowed|not available|must be', L, ignore.case = TRUE)]; return(save(r)) }
  if (!r$normal) { r$status <- if (timed_out) 'TIMEOUT' else if (grepl('NO CONVERGENCE|DID NOT CONVERGE|ITERATIONS EXCEEDED|ITERATION LIMIT', flat)) 'NOT_CONVERGED' else 'ESTIMATION_FAILED'
    f <- regmatches(flat, regexpr('COMPUTATION COULD NOT BE COMPLETED IN ITERATION\\s+[0-9]+', flat)); if (length(f)) r$failure_detail <- f
    return(save(r)) }
  m <- tryCatch(read_mplus_raw(dest), error = function(e) { wj(list(error = conditionMessage(e)), file.path(dest, 'extraction_error.json')); NULL })
  if (is.null(m)) { r$status <- 'EXTRACTION_FAILED'; return(save(r)) }
  si <- spec_info_r2e(row$z, row$spec, ctrl_of(row$z, row$sample), zshape_of(row$z))
  utils::write.csv(m$par, file.path(dest, 'parameters_high_precision.csv'), row.names = FALSE); utils::write.csv(m$V, file.path(dest, 'parameter_covariance.csv'))
  zp <- support_z(row$z); gt <- gate_r2e(m, si, zp); cl <- classify_member(m, si, gt, zp)
  wj(gt[c('passed', 'flags', 'negative', 'vcov')], file.path(dest, 'gate.json')); wj(gt$geometry$checks, file.path(dest, 'geometry.json'))
  kp <- tryCatch(key_paths_r2e(m, si$key), error = function(e) { wj(list(error = conditionMessage(e)), file.path(dest, 'key_error.json')); NULL })
  printed <- NA
  if (!is.null(kp)) {
    utils::write.csv(kp, file.path(dest, 'key_paths.csv'), row.names = FALSE)
    if (requireNamespace('MplusAutomation', quietly = TRUE)) {
      pp <- tryCatch(MplusAutomation::readModels(out, quiet = TRUE)$parameters$unstandardized, error = function(e) NULL)
      if (is.data.frame(pp)) {
        pk <- vapply(seq_len(nrow(kp)), function(i) { q <- pp$est[toupper(pp$paramHeader) == paste0(kp$row[i], '.ON') & toupper(pp$param) == kp$column[i]]; if (length(q) == 1) q else NA_real_ }, numeric(1))
        printed <- all(is.finite(pk)) && all(abs(pk - kp$estimate) <= .0006)
        utils::write.csv(data.frame(kp, printed = pk), file.path(dest, 'key_printed_comparison.csv'), row.names = FALSE)
      } else printed <- FALSE
    }
  }
  r$LL <- m$extra[['H0 Loglikelihood']]; if (is.null(r$LL)) { v <- regmatches(flat, regexpr('H0 Value\\s+-?[0-9.]+', flat)); r$LL <- if (length(v)) as.numeric(sub('H0 Value\\s+', '', v)) else NA }
  r$parameters <- m$P; r$negative <- gt$negative; r$geometry_ok <- isTRUE(gt$geometry$passed); r$vcov_ok <- isTRUE(gt$vcov$ok)
  r$warnings <- gt$flags$warnings; r$printed_match <- printed; r$psi_SY <- cl$sy; r$psi_SY_se <- cl$sy_se; r$psi_SY_z <- cl$sy_z
  base_ok <- !is.null(kp) && !identical(printed, FALSE)
  r$status <- if (is.null(kp)) 'KEY_PATH_ERROR' else if (identical(printed, FALSE)) 'PRINTED_MISMATCH' else cl$status
  r$usable <- base_ok && cl$status == 'USABLE'; r$boundary <- base_ok && cl$status == 'BOUNDARY_SY'
  save(r)
}

# ---------------------------------------------------------------- 运行
call_cap_seconds <- function(kind, category) { cc <- contract()$per_call_seconds; v <- cc[[paste0(kind, '_', category)]]; if (is.null(v)) cc[[kind]] else v }
run_model <- function(row) {
  dest <- row$dest; rf <- file.path(dest, 'receipt.json'); if (file.exists(rf)) return(fromJSON(rf, simplifyVector = FALSE))
  stopifnot(hashf(file.path(dest, 'model.inp')) == row$input_sha256, hashf(file.path(dest, 'data.dat')) == row$data_sha256)
  if (file.exists(file.path(dest, 'model.out'))) stop('Existing output without receipt: recover readback, do not rerun ', row$id)
  if (!DRYRUN && !identical(Sys.getenv('R2E_RESOURCE_GATE'), '0')) {
    t0 <- Sys.time()
    repeat {
      rr <- file.path(dest, 'resource_before.json')
      st <- system2(PY, c(shQuote(file.path(.r2e_dir, 'r2e_resource_gate.py')), shQuote(rr), shQuote(file.path(R2E, 'runtime', 'PAUSE'))), stdout = FALSE, stderr = FALSE)
      if (st == 0 && isTRUE(fromJSON(rr)$admit)) break
      progress('resource_wait', row$id); if (as.numeric(difftime(Sys.time(), t0, units = 'hours')) > 2) budget_stop('RESOURCE_WAIT_LIMIT', paste('Resource wait over 2 h before', row$id))
      Sys.sleep(30)
    }
  }
  bs <- register_call(row)
  if (DRYRUN) { r <- c(row[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'batch', 'kind', 'sample')], list(status = 'DRYRUN_PLANNED', usable = FALSE, seconds = 0)); wj(r, rf); return(r) }
  limit <- min(call_cap_seconds(row$kind, row$category), bs$engine_left, bs$wall_left)
  progress('estimate_start', paste(row$id, 'limit_s', round(limit)))
  p <- processx::process$new(MPLUS, 'model.inp', wd = dest, stdout = file.path(dest, 'mplus_console.log'), stderr = '2>&1', cleanup = TRUE)
  t0 <- Sys.time(); wj(list(id = row$id, pid = p$get_pid(), started_utc = format(t0, tz = 'UTC', usetz = TRUE)), file.path(dest, 'process.json'))
  timed_out <- FALSE
  while (p$is_alive()) { p$wait(timeout = 5000); el <- as.numeric(difftime(Sys.time(), t0, units = 'secs'))
    if (el > limit) { p$kill_tree(); timed_out <- TRUE; break } }
  sec <- as.numeric(difftime(Sys.time(), t0, units = 'secs'))
  r <- readback_model(row, sec, if (timed_out) 124L else p$get_exit_status(), timed_out)
  if (timed_out) { r$limit_seconds <- limit; wj(r, rf) }
  add_ledger(r, row$batch); progress('estimate_done', paste(row$id, r$status, round(sec), 's'))
  r
}
# 中断恢复：已登记但无回执的调用。有 model.out → 照常读回（耗时记NA）；无输出 → 写 INTERRUPTED 回执（计为已用调用，不重跑同一尝试）。
recover_calls <- function() {
  if (!file.exists(REG)) return(invisible(data.frame()))
  tab <- utils::read.csv(REG, stringsAsFactors = FALSE); done <- list()
  for (i in seq_len(nrow(tab))) {
    d <- model_dir(tab$z[i], tab$spec[i], tab$member[i], tab$attempt[i], tab$sample[i])
    if (file.exists(file.path(d, 'receipt.json'))) next
    row <- fromJSON(file.path(d, 'input_contract.json'), simplifyVector = FALSE)
    pj <- file.path(d, 'process.json')
    if (file.exists(pj)) { pid <- as.integer(fromJSON(pj)$pid)          # 只读核对：该进程仍在运行则停止，不读回、不重跑
      if (isTRUE(tryCatch(ps::ps_is_running(ps::ps_handle(pid)), error = function(e) FALSE))) stop('Registered call still running (pid ', pid, '): ', row$id) }
    r <- if (file.exists(file.path(d, 'model.out'))) { x <- readback_model(row, NA_real_, NA_integer_, FALSE)
      if (!isTRUE(x$normal) && x$status %in% c('ESTIMATION_FAILED', 'NO_OUTPUT')) { x$status <- 'INTERRUPTED'; wj(x, file.path(d, 'receipt.json')) }; x } else {
      x <- c(row[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'batch', 'kind', 'sample')], list(status = 'INTERRUPTED', usable = FALSE, seconds = NA))
      wj(x, file.path(d, 'receipt.json')); x }
    add_ledger(r, row$batch); done[[length(done) + 1]] <- data.frame(id = row$id, status = r$status)
  }
  invisible(if (length(done)) do.call(rbind, done) else data.frame())
}
read_member <- function(z, spec, k, attempt, sample = 'Z0') {
  d <- model_dir(z, spec, k, attempt, sample); f <- file.path(d, 'receipt.json'); if (!file.exists(f)) return(NULL)
  r <- fromJSON(f, simplifyVector = FALSE); a <- list(receipt = r, dest = d)
  if (isTRUE(r$usable) || isTRUE(r$boundary)) a$key <- utils::read.csv(file.path(d, 'key_paths.csv'))
  a
}
run_one <- function(z, spec, k, attempt, category, batch, sample = 'Z0', points = 15L, processors = 1L, seed = 26101001L, warm = NULL, source_data = NULL) {
  row <- prepare_model(z, spec, k, attempt, category, batch, sample, points, processors, seed, warm, source_data)
  run_model(row); read_member(z, spec, k, attempt, sample)
}
ok_member <- function(a) !is.null(a) && isTRUE(a$receipt$usable)
bnd_member <- function(a) !is.null(a) && isTRUE(a$receipt$boundary)
interface_error <- function(a) !is.null(a) && a$receipt$status %in% c('INPUT_REJECTED', 'EXTRACTION_FAILED', 'KEY_PATH_ERROR', 'PRINTED_MISMATCH')
