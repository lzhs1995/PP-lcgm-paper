# Round2F 本机模块：Astra Round2E 代码三件（r2e_local.R、r2e_tools.R、r2e_upstream_math.R）按合同哈希原样复制到本轮
# code/，本文件只在其上做最小覆盖：
#   E1F（SY残差固定为正值）；新自由参数的显式正起点（仅 VAR:SY）；收敛准则、估计量与无聚类变体；
#   精确条件高斯LL核对；Round2F回执、预算读取与准入。任何函数都不比较P值。
# 用法：先设环境变量 R2F_ROOT，再 source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())。
local({
  root <- Sys.getenv('R2F_ROOT'); if (!nzchar(root)) stop('Set R2F_ROOT first')
  Sys.setenv(R2E_ROOT = root)                      # Round2E 代码把 R2E_ROOT 当作"本轮根目录"
})
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2e_local.R'), local = globalenv())

.envpath <- function(k, default) { v <- Sys.getenv(k, ''); if (nzchar(v)) v else default }
ROOT <- normalizePath(Sys.getenv('R2F_ROOT'), winslash = '/', mustWork = TRUE)
C2F <- rj(file.path(ROOT, 'contracts/RUN_CONTRACT_2F.json'))
R2D <- .envpath('R2F_R2D', C2F$paths_default$R2F_R2D)
R2C <- .envpath('R2F_R2C', C2F$paths_default$R2F_R2C)
R2E <- .envpath('R2F_R2E', C2F$paths_default$R2F_R2E)
PY <- .envpath('R2F_PY', PY)
MPLUS <- .envpath('R2F_MPLUS', MPLUS)
SUPPORT_SD <- unlist(C2F$support_points_SD)
r2e_model <- function(id) file.path(R2E, 'models', id)

# ---------------------------------------------------------------- 规格
# E1Fddd：E1 + sy@0.ddd。fixed_value 进入自由参数清单的排除项，但不进入 fixed_zero（PSI 应满秩）。
spec <- function(z, sp, ctrl = controls(z)) {
  m <- regmatches(sp, regexec('^E1F([0-9]{3})$', sp))[[1]]
  if (length(m)) {
    v <- as.integer(m[2]) / 1000; stopifnot(v > 0)
    si <- spec_info_r2e(z, 'E1', ctrl)
    si$model <- c(si$model, paste0('sy@', formatC(v, format = 'f', digits = 3), ';'))
    si$fixed_value <- c(SY = v)
    return(si)
  }
  stopifnot(sp %in% c('E0', 'E1', 'E0B', 'E1B'))
  si <- spec_info_r2e(z, sp, ctrl); si$fixed_value <- numeric(0); si
}
slots <- function(si) {
  fixed <- c(si$fixed_zero, names(si$fixed_value))
  rows <- list(); add <- function(op, lhs, rhs = '', init = 0) {
    rows[[length(rows) + 1L]] <<- data.frame(op = op, lhs = toupper(lhs), rhs = toupper(rhs), init = init)
  }
  for (j in 2:4) add('BY', 'SX', paste0('X', j), R2D_TIME[j])
  for (f in FAC_XY) add('MEAN', f)
  for (o in OBS_XY) add('VAR', o, init = .5)
  for (f in setdiff(FAC_XY, fixed)) add('VAR', f, init = .1)
  for (key in stmt_pairs(si$model)) {
    tk <- strsplit(toupper(key), ' ', fixed = TRUE)[[1]]
    add(tk[2], tk[1], tk[3])
  }
  ans <- do.call(rbind, rows)
  ans$key <- paste(ans$op, ans$lhs, ans$rhs, sep = ':')
  stopifnot(!anyDuplicated(ans$key))
  ans
}
# start_override：仅允许合同列出的键（VAR:SY）。用于从 sy@0 或固定正值来源回到自由 SY 时给出合法正起点，
# 绝不把来源中的 @ 固定值当作自由参数起点复制过来。
make_model <- function(si, source_dir = NULL, perturb = FALSE, start_override = NULL) {
  s <- slots(si); s$value <- s$init; s$source_value <- NA_real_; s$action <- 'new_start'; s$source_sha256 <- NA_character_
  ov <- unlist(start_override)
  if (length(ov)) {
    ok <- names(ov) %in% names(C2F$allowed_start_override) & ov > 0
    if (!all(ok)) stop('Start override not allowed: ', paste(names(ov)[!ok], collapse = ','))
    ov <- ov[names(ov) %in% sub(':$', '', s$key)]
  }
  okey <- sub(':$', '', s$key)
  if (!is.null(source_dir)) {
    m <- read_mplus_raw(source_dir)
    src <- rj(file.path(source_dir, 'receipt.json'))
    if (!is.null(src) && isTRUE(src$round %in% c('Round2E', 'Round2F'))) {
      if (!identical(src$status, 'USABLE')) stop('Start source not USABLE: ', basename(source_dir))
    } else {
      stopifnot(isTRUE(gate_r2e(m, list(kind = 'linear', fac = FAC_XY, obs = OBS_XY, fixed_zero = character(0)))$passed))
    }
    meas <- canonical_measurement(m, FAC_XY, OBS_XY)
    source_vars <- unique(c(m$spec$row, m$spec$column))
    for (i in seq_len(nrow(s))) {
      absent <- s$op[i] == 'ON' && !s$rhs[i] %in% source_vars
      v <- if (absent) NA_real_ else canonical_value(m, s$op[i], s$lhs[i], s$rhs[i], meas)
      if (okey[i] %in% names(ov)) { s$source_value[i] <- v; next }
      if (is.finite(v)) { s$value[i] <- v; s$source_value[i] <- v; s$action[i] <- 'mapped_high_precision' }
      else if (!absent) stop('Incomplete full start mapping: ', s$key[i])
    }
    s$source_sha256 <- hashf(file.path(source_dir, 'model.out'))
  }
  for (k in names(ov)) { j <- okey == k; s$value[j] <- ov[[k]]; s$action[j] <- 'contract_start_override' }
  if (!all(s$value[s$op == 'VAR'] > 0)) stop('Non-positive variance start: ', paste(s$key[s$op == 'VAR' & !(s$value > 0)], collapse = ','))
  if (perturb) {
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
  list(lines = c(si$model, lines), mapping = s, expected_free = nrow(s))
}

# ---------------------------------------------------------------- 输入文本
analysis_r2f <- function(kind, points = C2F$points, processors = 1L, conv = 'default', estimator = 'MLR', cluster = TRUE, seed = 26101001) {
  crit <- unlist(C2F$convergence[[conv]]); if (is.null(C2F$convergence[[conv]])) stop('Unknown convergence variant ', conv)
  if (kind == 'linear') {
    type <- if (cluster) 'COMPLEX' else 'GENERAL'
    return(paste0('TYPE=', type, '; ESTIMATOR=', estimator, '; PROCESSORS=', processors, '; COVERAGE=.005; ITERATIONS=2000;'))
  }
  c(paste0('TYPE=', if (cluster) 'COMPLEX RANDOM' else 'RANDOM', '; ESTIMATOR=', estimator, '; PROCESSORS=', processors, ';'),
    paste0('ALGORITHM=INTEGRATION; INTEGRATION=', points, ';'),
    paste0('MCSEED=', seed, '; COVERAGE=.005; ITERATIONS=2000; MITERATIONS=4000;'), crit)
}
# cluster=TRUE 时与 Round2E inp_text 逐字节相同（自检核对）。
inp_text_r2f <- function(title, usev, analysis, model, kind = 'linear', cluster = TRUE) {
  out <- paste(if (kind == 'linear') 'TECH1 TECH3 TECH4 SAMPSTAT RESIDUAL CINTERVAL' else 'TECH1 TECH3 TECH8 CINTERVAL', 'SVALUES')
  s <- c('TITLE:', title, 'DATA:', 'FILE = "data.dat";', 'VARIABLE:',
         wrap90(paste0('NAMES = ', paste(R2D_NAMES, collapse = ' '), ';')), ' MISSING=.;',
         wrap90(paste0(if (cluster) ' CLUSTER=fid;' else '', ' USEVARIABLES=', paste(usev, collapse = ' '), ';')))
  s <- c(s, 'ANALYSIS:', analysis, 'MODEL:', unlist(lapply(model, wrap90)))
  s <- c(s, 'OUTPUT:', paste0(out, ';'), 'SAVEDATA:', 'TECH3=tech3.dat; RESULTS=estimates.dat;')
  stopifnot(all(nchar(s) <= 90))
  s
}
cap_for <- function(sample, kind) {
  p <- C2F$budget$per_call_active_seconds
  if (sample == 'SYNTHETIC') p$synthetic else if (kind == 'linear') p$linear else p$observed_LMS
}

# ---------------------------------------------------------------- 预算与准入（引擎另行强制；此处只为不准入时不建目录、不中断队列）
budget_r2f <- function() {
  b <- rj(file.path(ROOT, 'runtime/budget_status.json'))
  w <- rj(file.path(ROOT, 'runtime/batch_window.json'))
  wall <- if (!is.null(w$start_epoch)) as.numeric(Sys.time()) - w$start_epoch else 0
  if (is.null(b)) return(list(calls = 0L, engine_seconds = 0, wall_seconds = wall, rows = list()))
  b$wall_seconds <- max(wall, b$wall_seconds); b
}
admission <- function(category, kind = 'lms_observed', sample = 'CFPS') {
  b <- budget_r2f(); B <- C2F$budget
  used <- sum(vapply(b$rows, function(r) identical(r$category, category), TRUE))
  need <- cap_for(sample, kind) * 0.1
  if (b$calls >= B$max_calls) return('NOT_RUN_CALL_CAP')
  if (is.null(B$categories[[category]]) || used >= B$categories[[category]]) return('NOT_RUN_CATEGORY_CAP')
  if (B$engine_seconds - b$engine_seconds < need || B$wall_seconds - b$wall_seconds < need) return('NOT_RUN_BUDGET')
  'ADMIT'
}

# ---------------------------------------------------------------- 输出读取的补充项
conv_info <- function(L) {
  g <- function(lab) {
    x <- grep(paste0('^\\s*', lab, '\\s+[0-9.]+D[-+][0-9]+\\s*$'), L, value = TRUE)
    if (length(x)) sub('^.*\\s([0-9.]+D[-+][0-9]+)\\s*$', '\\1', x[1]) else NA_character_
  }
  ans <- list(loglik_change = g('Loglikelihood change'), relative_change = g('Relative loglikelihood change'),
              derivative = g('Derivative'), iterations = NA_integer_, last_abs_change = NA_real_, algorithms = NA_character_)
  h <- grep('E STEP\\s+ITER\\s+LOGLIKELIHOOD', L)
  if (length(h)) {
    rows <- character(0); k <- h[1] + 1L
    while (k <= length(L) && (grepl('^\\s+[0-9]+\\s+-?[0-9.]+D[-+][0-9]+', L[k]) || !nzchar(trimws(L[k])) && !length(rows))) {
      if (nzchar(trimws(L[k]))) rows <- c(rows, L[k]); k <- k + 1L
    }
    if (length(rows)) {
      tk <- strsplit(trimws(rows), '\\s+')
      ans$iterations <- length(tk)
      ans$last_abs_change <- as.numeric(tk[[length(tk)]][3])
      ans$algorithms <- paste(names(table(vapply(tk, function(t) t[length(t)], ''))), collapse = '/')
    }
  }
  ans
}
exact_ll <- function(dest, out, diagnostic = FALSE, data = file.path(dest, 'data.dat')) {
  if (file.exists(out)) return(rj(out))
  args <- c(file.path(ROOT, 'code/r2f_exact_ll.py'), '--model-dir', dest, '--data', data, '--output', out)
  if (diagnostic) args <- c(args, '--diagnostic-allow-indefinite-latent')
  res <- tryCatch(processx::run(PY, args, error_on_status = FALSE, timeout = C2F$exact_ll$timeout_seconds),
                  error = function(e) list(status = -1L, stdout = '', stderr = conditionMessage(e)))
  if (!identical(as.integer(res$status), 0L) || !file.exists(out)) {
    e <- list(error = trimws(paste(res$stdout, res$stderr)), status = res$status)
    wj(e, sub('\\.json$', '_error.json', out)); return(e)
  }
  rj(out)
}

# ---------------------------------------------------------------- 准备、读取、运行
prepare_r2f <- function(sp, k, attempt, category, z = 'SD', points = C2F$points, conv = 'default', estimator = 'MLR',
                        cluster = TRUE, source_dir = NULL, start_override = NULL, sample = 'CFPS',
                        source_data = NULL, data_tag = 'Z0', ctrl = NULL) {
  if (is.null(ctrl)) ctrl <- if (sample == 'SYNTHETIC') C2F$data$synthetic_ctrl else controls(z)
  if (is.null(source_data)) source_data <- datpath(z, k)
  id <- paste(c(sample, z, sp, sprintf('%02d', k), if (data_tag != 'Z0') data_tag, attempt), collapse = '_')
  d <- file.path(ROOT, 'models', id); cf <- file.path(d, 'input_contract.json')
  if (file.exists(cf)) return(rj(cf))
  si <- spec(z, sp, ctrl); mm <- make_model(si, source_dir, FALSE, start_override)
  an <- analysis_r2f(si$kind, points, 1L, conv, estimator, cluster)
  inp <- inp_text_r2f(paste('Round2F', id), si$use, an, mm$lines, if (si$kind == 'linear') 'linear' else 'lms', cluster)
  dir.create(d, recursive = TRUE, showWarnings = FALSE)
  dd <- file.path(d, 'data.dat')
  if (file.exists(dd)) stopifnot(identical(hashf(dd), hashf(source_data))) else stopifnot(file.copy(source_data, dd))
  writeLines(inp, file.path(d, 'model.inp')); csv(mm$mapping, file.path(d, 'start_mapping.csv'))
  dt <- read_dat(source_data, R2D_NAMES)
  signature <- digest(list(spec = sp, ctrl = ctrl, slots = mm$mapping$key, fixed = si$fixed_zero, fixed_value = si$fixed_value,
                           estimator = estimator, cluster = cluster, data_tag = data_tag, sample = sample), algo = 'sha256')
  spz <- if (sample == 'CFPS' && z == 'SD') SUPPORT_SD[c('raw_zero', 'positive_median', 'P90')] else numeric(0)
  job <- list(id = id, round = 'Round2F', z = z, spec = sp, member = k, attempt = attempt, category = category, sample = sample,
    data_tag = data_tag, points = if (si$kind == 'linear') 0L else as.integer(points), processors = 1L, conv = conv,
    estimator = estimator, cluster = cluster, start_override = as.list(unlist(start_override)), dest = d, ctrl = ctrl,
    N = nrow(dt), households = length(unique(dt$fid)), data_sha256 = hashf(source_data),
    input_sha256 = hashf(file.path(d, 'model.inp')), source_data = source_data, source_start = source_dir,
    expected_free = mm$expected_free, structural_signature = signature,
    support_points = unname(unique(c(min(dt$z0, na.rm = TRUE), spz, max(dt$z0, na.rm = TRUE)))),
    cap_seconds = cap_for(sample, si$kind), mplus = MPLUS, root = ROOT)
  wj(job, cf); job
}
read_result_r2f <- function(job) {
  d <- job$dest; er <- rj(file.path(d, 'engine_receipt.json'))
  keep <- c('id', 'z', 'spec', 'member', 'attempt', 'category', 'sample', 'data_tag', 'points', 'processors', 'conv', 'estimator',
            'cluster', 'dest', 'expected_free', 'structural_signature', 'N', 'households', 'source_start')
  r <- c(job[intersect(keep, names(job))], list(round = 'Round2F', seconds = er$seconds, wall_seconds = er$wall_seconds,
    gap_seconds = er$gap_seconds, suspend_affected = isTRUE(er$suspend_affected), keep_awake = er$keep_awake,
    engine_status = er$status, status = er$status, usable = FALSE))
  f <- file.path(d, 'model.out')
  L <- if (file.exists(f)) readLines(f, warn = FALSE, encoding = 'latin1') else character(0)
  if (length(L)) r$output_sha256 <- hashf(f)
  r$normal <- any(grepl('THE MODEL ESTIMATION TERMINATED NORMALLY', L, fixed = TRUE))
  r$convergence <- conv_info(L)
  r$ill_conditioned <- any(grepl('ILL-CONDITIONED', L, fixed = TRUE))
  if (!is.null(er$test_hook) && identical(job$sample, 'CFPS')) r$status <- 'TEST_HOOK_REFUSED'
  if (!identical(r$status, 'EXITED')) { wj(r, file.path(d, 'receipt.json')); return(r) }
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
    r$LL <- m$extra[['H0 Loglikelihood']]
    if (is.null(r$LL)) { ll <- grep('H0 Value', L, value = TRUE); r$LL <- as.numeric(sub('.*H0 Value\\s+(-?[0-9.]+).*', '\\1', ll[1])) }
    r$scaling <- m$extra[['H0 Scaling Correction Factor for MLR']]
    r$condition_number <- m$extra[['Condition Number']]
    r$parameters <- m$P; r$negative <- gt$negative; r$warnings <- gt$flags$warnings
    r$sy <- mval(m, 'PSI', 'SY', 'SY')
    dims <- grep('Dimensions of numerical integration', L, value = TRUE)
    r$integration_dimensions <- if (length(dims)) as.integer(sub('.*?([0-9]+)\\s*$', '\\1', dims[1])) else 0L
    if (si$kind == 'lms_observed' && !identical(r$integration_dimensions, 1L)) r$status <- 'INTEGRATION_DIMENSION_MISMATCH'
    if (!identical(job$conv, 'default')) {
      want <- C2F$expected_printed_criteria[[job$conv]]
      got <- list(`Loglikelihood change` = r$convergence$loglik_change, `Relative loglikelihood change` = r$convergence$relative_change)
      r$criteria_as_requested <- all(vapply(names(want), function(n) identical(got[[n]], want[[n]]), TRUE))
      if (!r$criteria_as_requested) r$status <- 'CRITERIA_NOT_APPLIED'
    }
  }, error = function(e) { r$status <<- 'EXTRACTION_FAILED'; r$error <<- conditionMessage(e) })
  if (file.exists(file.path(d, 'matrix_values.csv')) && !identical(r$status, 'EXTRACTION_FAILED')) {
    ex <- exact_ll(d, file.path(d, 'exact_ll.json'), diagnostic = !identical(r$status, 'USABLE'))
    r$exact_LL <- ex$exact_LL; r$exact_LL_difference <- ex$difference
    r$exact_LL_n_match <- ex$n_matches_mplus; r$exact_LL_error <- ex$error
  }
  r$usable <- identical(r$status, 'USABLE')
  wj(r, file.path(d, 'receipt.json')); r
}
# 不准入时返回 NOT_RUN_*，不建目录、不中断队列；已有回执直接返回（断点续跑幂等）。
run_r2f <- function(sp, k, attempt, category, ...) {
  a <- list(...); z <- if (is.null(a$z)) 'SD' else a$z; sample <- if (is.null(a$sample)) 'CFPS' else a$sample
  tag <- if (is.null(a$data_tag)) 'Z0' else a$data_tag
  id <- paste(c(sample, z, sp, sprintf('%02d', k), if (tag != 'Z0') tag, attempt), collapse = '_')
  rf <- file.path(ROOT, 'models', id, 'receipt.json'); if (file.exists(rf)) return(rj(rf))
  if (!file.exists(file.path(ROOT, 'models', id, 'input_contract.json'))) {
    kind <- spec(z, sp, if (sample == 'SYNTHETIC') C2F$data$synthetic_ctrl else controls(z))$kind
    adm <- admission(category, kind, sample)
    if (adm != 'ADMIT') { progress('not_admitted', paste(id, adm)); return(list(id = id, spec = sp, member = k, attempt = attempt, category = category, status = adm, usable = FALSE)) }
  }
  job <- prepare_r2f(sp, k, attempt, category, ...)
  progress('estimate_start', job$id)
  pp <- processx::process$new(PY, c(file.path(ROOT, 'code/r2f_engine.py'), file.path(job$dest, 'input_contract.json')),
      stdout = file.path(job$dest, 'engine_console.log'), stderr = '2>&1', cleanup = TRUE)
  last <- 0
  while (pp$is_alive()) {
    pp$wait(1000L); now <- as.numeric(Sys.time())
    if (now - last >= 25) {
      hb <- rj(file.path(job$dest, 'engine_progress.json'))
      progress(if (is.null(hb$stage)) 'engine_starting' else hb$stage, paste(job$id, if (is.null(hb$message)) '' else hb$message)); last <- now
    }
  }
  if (!file.exists(file.path(job$dest, 'engine_receipt.json'))) {
    msg <- paste(readLines(file.path(job$dest, 'engine_console.log'), warn = FALSE), collapse = '\n')
    if (grepl('CALL_CAP|BUDGET_EXHAUSTED|RESOURCE_WAIT_LIMIT', msg)) {
      st <- regmatches(msg, regexpr('CALL_CAP|BUDGET_EXHAUSTED|RESOURCE_WAIT_LIMIT', msg))
      r <- list(id = job$id, spec = sp, member = k, attempt = attempt, category = category, status = paste0('NOT_RUN_', st), usable = FALSE, dest = job$dest)
      wj(r, file.path(job$dest, 'not_run.json')); return(r)
    }
    stop('Engine stopped before receipt: ', msg)
  }
  r <- read_result_r2f(job); progress('estimate_done', paste(job$id, r$status, round(r$seconds), 'seconds')); r
}
usable <- function(r) !is.null(r) && identical(r$status, 'USABLE')
