# Round2E 本机修订：保留目标规格，按语义键覆盖全部公共参数起点。
# 上游文件保留原字节；仅本文件中的函数为本批可调用接口。
source(file.path(Sys.getenv('R2E_ROOT'), 'code/r2e_tools.R'), local = TRUE)
library(jsonlite)
library(digest)
library(processx)

ROOT <- Sys.getenv('R2E_ROOT')
R2D <- 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
R2C <- 'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
PY <- 'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
MPLUS <- 'C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Mplus.exe'
hashf <- function(f) digest::digest(file = f, algo = 'sha256')
wj <- function(x, f) { dir.create(dirname(f), recursive = TRUE, showWarnings = FALSE); jsonlite::write_json(x, f, auto_unbox = TRUE, pretty = TRUE, digits = NA, na = 'null') }
rj <- function(f) if (file.exists(f)) jsonlite::fromJSON(f, simplifyVector = FALSE) else NULL
csv <- function(x, f) utils::write.csv(x, f, row.names = FALSE, na = '')
progress <- function(stage, message) {
  wj(list(stage = stage, message = message, updated_at = format(Sys.time(), tz = 'UTC', usetz = TRUE)), file.path(ROOT, 'runtime/progress.json'))
  cat(format(Sys.time(), tz = 'UTC', usetz = TRUE), stage, message, '\n'); flush.console()
  if (exists('clauder_progress', mode = 'function', inherits = TRUE)) clauder_progress(stage, message)
}
zc <- function() rj(file.path(R2D, 'audit/Z_CONTRACT.json'))
controls <- function(z) zc()$samples[[paste0(z, '_Z0')]]$ctrl_term
datpath <- function(z, k) file.path(R2D, 'private', z, sprintf('Z0_member_%02d.dat', k))
swpath <- function(k) file.path(R2C, 'models', sprintf('SW_MI%02d', k), 'attempt01')
spec <- function(z, sp, ctrl = controls(z)) {
  stopifnot(sp %in% c('E0', 'E1', 'E0B', 'E1B'))
  spec_info_r2e(z, sp, ctrl)
}

# 显式自由参数清单；增长线与固定载荷留在原目标语法内。
slots <- function(si) {
  rows <- list(); add <- function(op, lhs, rhs = '', init = 0) {
    rows[[length(rows) + 1L]] <<- data.frame(op = op, lhs = toupper(lhs), rhs = toupper(rhs), init = init)
  }
  for (j in 2:4) add('BY', 'SX', paste0('X', j), R2D_TIME[j])
  for (f in FAC_XY) add('MEAN', f)
  for (o in OBS_XY) add('VAR', o, init = .5)
  for (f in setdiff(FAC_XY, si$fixed_zero)) add('VAR', f, init = .1)
  # ON/WITH 全部展开，完全保留目标科学规格。
  for (key in stmt_pairs(si$model)) {
    tk <- strsplit(toupper(key), ' ', fixed = TRUE)[[1]]
    add(tk[2], tk[1], tk[3])
  }
  ans <- do.call(rbind, rows)
  ans$key <- paste(ans$op, ans$lhs, ans$rhs, sep = ':')
  stopifnot(!anyDuplicated(ans$key))
  ans
}
canonical_value <- function(m, op, lhs, rhs, measurement) {
  has <- function(mat, r, c) any(.cell(m$spec, mat, r, c))
  if (op == 'BY') return(measurement$LAMBDA[rhs, lhs])
  if (op == 'VAR' && lhs %in% OBS_XY) return(measurement$THETA[lhs, lhs])
  if (op == 'WITH' && lhs %in% OBS_XY && rhs %in% OBS_XY) return(measurement$THETA[lhs, rhs])
  if (op == 'VAR') return(if (has('PSI', lhs, lhs)) mval(m, 'PSI', lhs, lhs) else NA_real_)
  if (op == 'WITH') return(if (has('PSI', lhs, rhs)) mval(m, 'PSI', lhs, rhs) else NA_real_)
  if (op == 'MEAN') return(if (has('ALPHA', '1', lhs)) mval(m, 'ALPHA', '1', lhs) else NA_real_)
  if (op == 'ON') return(if (has('BETA', lhs, rhs)) mval(m, 'BETA', lhs, rhs) else if (has('GAMMA', lhs, rhs)) mval(m, 'GAMMA', lhs, rhs) else NA_real_)
  stop('Unknown slot')
}
make_model <- function(si, source_dir = NULL, perturb = FALSE) {
  s <- slots(si); s$value <- s$init; s$source_value <- NA_real_; s$action <- 'new_start'; s$source_sha256 <- NA_character_
  if (!is.null(source_dir)) {
    m <- read_mplus_raw(source_dir)
    source_receipt <- rj(file.path(source_dir, 'receipt.json'))
    # SW来源用其自身模型核验；新批来源必须具有本批实际USABLE回执。
    if (!is.null(source_receipt) && identical(source_receipt$round, 'Round2E')) {
      stopifnot(identical(source_receipt$status, 'USABLE'))
    } else {
      source_si <- list(kind = 'linear', fac = FAC_XY, obs = OBS_XY, fixed_zero = character(0))
      stopifnot(isTRUE(gate_r2e(m, source_si)$passed))
    }
    meas <- canonical_measurement(m, FAC_XY, OBS_XY)
    source_vars <- unique(c(m$spec$row, m$spec$column))
    for (i in seq_len(nrow(s))) {
      # 新外生Z0或新乘积在源矩阵中不存在，不用缺失矩阵的默认零伪装映射。
      absent <- s$op[i] == 'ON' && !s$rhs[i] %in% source_vars
      v <- if (absent) NA_real_ else canonical_value(m, s$op[i], s$lhs[i], s$rhs[i], meas)
      if (is.finite(v)) { s$value[i] <- v; s$source_value[i] <- v; s$action[i] <- 'mapped_high_precision' }
      else if (!absent) stop('Incomplete full start mapping: ', s$key[i])
    }
    s$source_sha256 <- hashf(file.path(source_dir, 'model.out'))
    stopifnot(all(s$value[s$op == 'VAR'] > 0))
  }
  if (perturb) {
    # 只改变非方差的自由起点；所有残差协方差保持合法源结构。
    j <- s$op %in% c('ON', 'MEAN', 'BY')
    s$value[j] <- s$value[j] + .02 * ifelse(seq_len(sum(j)) %% 2, 1, -1)
    s$action[j] <- paste0(s$action[j], '_deterministic_perturbation')
  }
  fmt <- function(v) formatC(v, digits = 12, format = 'g')
  lines <- vapply(seq_len(nrow(s)), function(i) {
    lhs <- tolower(s$lhs[i]); rhs <- tolower(s$rhs[i]); v <- trimws(fmt(s$value[i]))
    switch(s$op[i], MEAN = paste0('[', lhs, '*', v, '];'), VAR = paste0(lhs, '*', v, ';'),
      paste(lhs, s$op[i], paste0(rhs, '*', v, ';')))
  }, '')
  # 原始目标语法始终在前；仅追加其本来已自由的同名参数起点。
  list(lines = c(si$model, lines), mapping = s, expected_free = nrow(s))
}

# 固定零不是已采用的边界估计，只允许SD的单成员诊断。
classify_local <- function(m, si, gate) {
  if (isTRUE(gate$passed)) return('USABLE')
  if (identical(gate$negative, 'psi:SY') && gate$flags$normal && !gate$flags$fatal &&
      !gate$flags$theta_warning && isTRUE(gate$vcov$ok) &&
      isTRUE(gate$geometry$checks$THETA$positive_definite)) return('INADMISSIBLE_SY_ONLY')
  'INADMISSIBLE'
}
numeric_check <- function(a, b, mode = 'start') {
  if (is.null(a) || is.null(b) || a$status != 'USABLE' || b$status != 'USABLE')
    return(list(passed = FALSE, outcome = 'UNAVAILABLE_OR_FAILED', mode = mode))
  if (!identical(a$structural_signature, b$structural_signature))
    return(list(passed = FALSE, outcome = 'STRUCTURE_MISMATCH', mode = mode))
  aa <- list(key = utils::read.csv(file.path(a$dest, 'key_paths.csv')), receipt = a)
  bb <- list(key = utils::read.csv(file.path(b$dest, 'key_paths.csv')), receipt = b)
  ans <- compare_numeric(aa, bb, mode)
  ans$outcome <- if (ans$passed) 'AGREE' else if (mode == 'integration') 'INTEGRATION_DISAGREES' else 'NOT_REPLICATED'
  ans
}
fixed_holm <- function(p, n) { stopifnot(length(p) == n); out <- rep(NA_real_, n); j <- which(is.finite(p)); out[j] <- p.adjust(p[j], 'holm', n = n); out }
pool_ten <- function(Q, U) { stopifnot(nrow(Q) == 10L, length(U) == 10L, all(is.finite(Q))); rubin_pool(Q, U) }

# H4仅写入操作化对应表，不运行或作整项支持判定。
h4_component <- function(delta) if (delta > 0) 'weakening_direction' else if (delta < 0) 'buffering_direction' else 'zero'

read_result <- function(job) {
  d <- job$dest; er <- rj(file.path(d, 'engine_receipt.json'))
  r <- c(job[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'sample', 'points', 'processors', 'dest', 'expected_free', 'structural_signature')],
    list(round = 'Round2E', seconds = er$seconds, engine_status = er$status, status = er$status, usable = FALSE))
  f <- file.path(d, 'model.out')
  if (file.exists(f)) { L <- readLines(f, warn = FALSE); r$output_sha256 <- hashf(f) } else L <- character(0)
  r$normal <- any(grepl('THE MODEL ESTIMATION TERMINATED NORMALLY', L, fixed = TRUE))
  if (er$status != 'EXITED') { wj(r, file.path(d, 'receipt.json')); return(r) }
  flat <- paste(L, collapse = ' ')
  if (grepl('\\*\\*\\* ERROR', flat)) r$status <- 'INPUT_REJECTED'
  else if (!r$normal) r$status <- 'ESTIMATION_FAILED'
  else tryCatch({
    m <- read_mplus_raw(d); si <- spec(job$z, job$spec, job$ctrl)
    if (m$P != job$expected_free) stop('Free parameter count differs from semantic slot inventory: ', m$P, ' vs ', job$expected_free)
    gt <- gate_r2e(m, si, unlist(job$support_points)); r$status <- classify_local(m, si, gt)
    kp <- key_paths_r2e(m, si$key)
    csv(m$par, file.path(d, 'parameters_high_precision.csv')); csv(kp, file.path(d, 'key_paths.csv'))
    csv(m$values, file.path(d, 'matrix_values.csv')); csv(m$spec, file.path(d, 'tech1_parameter_map.csv'))
    utils::write.table(m$V, file.path(d, 'parameter_covariance.csv'), sep = ',', row.names = FALSE, col.names = FALSE)
    wj(gt, file.path(d, 'gate.json'))
    r$LL <- m$extra[['Loglikelihood']]; if (is.null(r$LL)) {
      ll <- grep('H0 Value', L, value = TRUE); r$LL <- as.numeric(sub('.*H0 Value\\s+(-?[0-9.]+).*', '\\1', ll[1]))
    }
    r$parameters <- m$P; r$negative <- gt$negative; r$warnings <- gt$flags$warnings
    r$sy <- mval(m, 'PSI', 'SY', 'SY'); r$usable <- r$status == 'USABLE'
    dims <- grep('Dimensions of numerical integration', L, value = TRUE)
    r$integration_dimensions <- if (length(dims)) as.integer(sub('.*?([0-9]+)\\s*$', '\\1', dims[1])) else 0L
    if (si$kind == 'lms_observed' && !identical(r$integration_dimensions, 1L)) { r$status <- 'INTEGRATION_DIMENSION_MISMATCH'; r$usable <- FALSE }
  }, error = function(e) { r$status <<- 'EXTRACTION_FAILED'; r$error <<- conditionMessage(e) })
  wj(r, file.path(d, 'receipt.json')); r
}

prepare <- function(z, sp, k, attempt, category, points = 20L, processors = 1L, source_dir = NULL,
                    perturb = FALSE, sample = 'CFPS', source_data = datpath(z, k), ctrl = controls(z)) {
  id <- paste(sample, z, sp, sprintf('%02d', k), attempt, sep = '_'); d <- file.path(ROOT, 'models', id)
  cf <- file.path(d, 'input_contract.json')
  if (file.exists(cf)) return(rj(cf))
  si <- spec(z, sp, ctrl); mm <- make_model(si, source_dir, perturb)
  an <- analysis_r2e(si$kind, points, processors)
  inp <- inp_text(paste('Round2E', id), si$use, an, mm$lines, kind = if (si$kind == 'linear') 'linear' else 'lms')
  dir.create(d, recursive = TRUE, showWarnings = FALSE)
  stopifnot(file.copy(source_data, file.path(d, 'data.dat'), overwrite = FALSE))
  writeLines(inp, file.path(d, 'model.inp')); csv(mm$mapping, file.path(d, 'start_mapping.csv'))
  dt <- read_dat(source_data, R2D_NAMES)
  signature <- digest(list(spec = sp, ctrl = ctrl, slots = mm$mapping$key, fixed = si$fixed_zero), algo = 'sha256')
  job <- list(id = id, z = z, spec = sp, member = k, attempt = attempt, category = category, sample = sample,
    points = if (si$kind == 'linear') 0L else points, processors = processors, dest = d, ctrl = ctrl,
    N = nrow(dt), households = length(unique(dt$fid)), data_sha256 = hashf(source_data),
    input_sha256 = hashf(file.path(d, 'model.inp')), source_data = source_data, source_start = source_dir,
    expected_free = mm$expected_free, structural_signature = signature,
    support_points = unique(c(min(dt$z0), max(dt$z0), median(dt$z0))),
    cap_seconds = if (sample == 'SYNTHETIC') 180L else if (si$kind == 'linear') 300L else 1800L,
    mplus = MPLUS, root = ROOT)
  wj(job, cf); job
}
run <- function(...) {
  job <- prepare(...); rf <- file.path(job$dest, 'receipt.json'); if (file.exists(rf)) return(rj(rf))
  progress('estimate_start', job$id)
  pp <- processx::process$new(PY, c(file.path(ROOT, 'code/run_engine.py'), file.path(job$dest, 'input_contract.json')),
      stdout = file.path(job$dest, 'engine_console.log'), stderr = '2>&1', cleanup = TRUE)
  while (pp$is_alive()) {
    pp$wait(1000L)
    now <- as.numeric(Sys.time())
    if (!exists('last', inherits = FALSE) || now - last >= 25) {
      hb <- rj(file.path(job$dest, 'engine_progress.json'))
      progress(if (is.null(hb$stage)) 'engine_starting' else hb$stage,
        paste(job$id, if (is.null(hb$message)) '' else hb$message)); last <- now
    }
  }
  if (!file.exists(file.path(job$dest, 'engine_receipt.json'))) {
    msg <- paste(readLines(file.path(job$dest, 'engine_console.log'), warn = FALSE), collapse = '\n')
    stop('Engine stopped before receipt: ', msg)
  }
  r <- read_result(job); progress('estimate_done', paste(job$id, r$status, round(r$seconds), 'seconds')); r
}
