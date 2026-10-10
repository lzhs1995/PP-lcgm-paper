# Round2E 本机 Mplus 冒烟测试：只用合成数据，不读取任何 CFPS 文件；在正式合同之前运行一次。
# 检验：各类新输入被 Mplus 9 接受并正常读回；SVALUES 拼接链（E0→E1、E1→E1B、E1→H4、E1B→H4B、D0→D1L、D0B→D1B）；
#       sy@0 在输出中确为固定值；PROCESSORS=4 与单核数值一致并记录耗时；默认起点与拼接起点一致；
#       合成数据中已知交互大致恢复；积分维数（E1/H4 为1，D1 为2）。
# 用法：Rscript r2e_smoke_mplus.R <新的空目录>
#       需要 R2E_MPLUS（Mplus.exe）与 R2E_PYTHON；R2E_SMOKE_SKIP_LATENT=1 可跳过四个潜路线调用（D0、D0B、D1L、D1B）。
# 输出：<目录>/R2E/results/SMOKE_RESULTS.csv 与 SMOKE_SUMMARY.json；目录内全部为合成数据，可整体回传。
SMOKE_TRUTH <- c(dc = -.25, dcg = -.20)        # 生成模型：SY 含 dc·SX·Z0 + dcg·SX·Z0·c2；ginc 无调节作用

smoke_code_dir <- function() { a <- commandArgs(FALSE); f <- sub('^--file=', '', a[grep('^--file=', a)]); f <- f[basename(f) == 'r2e_smoke_mplus.R']
  if (length(f)) dirname(normalizePath(f, winslash = '/')) else normalizePath(Sys.getenv('R2E_CODE', '.'), winslash = '/') }

# ---------------- 合成 Round2D 式目录（结构与真实目录相同；数值来自已知生成模型）
smoke_build_r2d <- function(R2D_F, code, n = 2000) {
  for (d in c('code', 'audit', 'runtime')) dir.create(file.path(R2D_F, d), recursive = TRUE)
  file.copy(file.path(code, 'r2e_upstream_math.R'), file.path(R2D_F, 'code', '00_upstream_math.R'))
  writeLines('{"terminal": true, "note": "smoke test, synthetic"}', file.path(R2D_F, 'runtime', 'queue_terminal.json'))
  set.seed(26101077); fid <- rep(seq_len(n / 2), each = 2); C <- matrix(rbinom(n * 24, 1, .4), n); ginc <- rbinom(n, 1, .5)
  ix <- rnorm(n, 0, .8) + .1 * C[, 1]; sx <- .15 * ix + rnorm(n, 0, .6)
  iz <- .3 * ix + rnorm(n, 0, .8); sz <- .1 * sx + rnorm(n, 0, .5)
  X <- Y <- Z <- matrix(0, n, 5)
  for (w in 1:5) { e <- matrix(rnorm(n * 3), n) %*% chol(matrix(c(.4, .04, .03, .04, .4, .04, .03, .04, .4), 3))
    X[, w] <- ix + c(0, .65, .7, .95, 1)[w] * sx + e[, 1]; Z[, w] <- iz + c(0, .45, .6, .85, 1)[w] * sz + e[, 3] }
  z0 <- Z[, 1]
  iy <- -.35 * ix + .15 * z0 + .1 * sx + rnorm(n, 0, .8)
  sy <- .1 * ix - .3 * sx + .2 * iy + .1 * z0 + SMOKE_TRUTH[['dc']] * sx * z0 + SMOKE_TRUTH[['dcg']] * sx * z0 * C[, 2] + rnorm(n, 0, .2)
  for (w in 1:5) Y[, w] <- iy + R2D_TIME[w] * sy + .2 * (X[, w] - ix - c(0, .65, .7, .95, 1)[w] * sx) + rnorm(n, 0, .55)
  d <- data.frame(fid, X, Y, Z, z0, C[, 2], C[, 3], ginc, C); names(d) <- R2D_NAMES
  zc <- list(samples = list(), z = list(SD = list(raw_prefix = 'wfd_s', orientation = 1, shape = 'free', ref_mean = 4.85780660460734, ref_sd = 10.2070583983168),
                                         SEXGAP = list(raw_prefix = 'wfd_d', orientation = -1, shape = 'linear', ref_mean = -0.95221936, ref_sd = 15.02112869),
                                         OLDEST = list(raw_prefix = 'wfd_d1', orientation = -1, shape = 'linear', ref_mean = -0.83039811, ref_sd = 14.56841288),
                                         SONGAP = list(raw_prefix = 'wfd_d4', orientation = -1, shape = 'linear', ref_mean = -0.86581374, ref_sd = 15.37117485)))
  ctrl <- c(SD = 'c1-c24', SEXGAP = 'c1-c7 c10-c24', OLDEST = 'c1-c24', SONGAP = 'c1-c8 c10-c24')
  for (z in names(ctrl)) { dir.create(file.path(R2D_F, 'private', z), recursive = TRUE); hs <- character(0)
    for (k in 1:10) { f <- file.path(R2D_F, 'private', z, sprintf('Z0_member_%02d.dat', k)); write_dat(d, f); hs <- c(hs, digest::digest(file = f, algo = 'sha256')) }
    zc$samples[[paste0(z, '_Z0')]] <- list(N = n, households = n / 2, ctrl_term = ctrl[[z]], data_sha256 = as.list(hs)) }
  fcc <- file.path(R2D_F, 'private', 'SD', 'CC_member_01.dat'); write_dat(d[seq_len(floor(.85 * n)), ], fcc)
  zc$samples$SD_CC <- list(N = floor(.85 * n), households = length(unique(fid[seq_len(floor(.85 * n))])), ctrl_term = 'c1-c24', data_sha256 = digest::digest(file = fcc, algo = 'sha256'))
  jsonlite::write_json(zc, file.path(R2D_F, 'audit', 'Z_CONTRACT.json'), auto_unbox = TRUE, pretty = TRUE, digits = NA)
  list(mean_c2 = mean(C[, 2]), n = n)
}

smoke_main <- function(work, hook = NULL) {
  code <- smoke_code_dir(); stopifnot(file.exists(file.path(code, 'r2e_queue.R')))
  if (dir.exists(work) && length(list.files(work, all.files = TRUE, no.. = TRUE))) stop('Use a new empty directory: ', work)
  dir.create(work, recursive = TRUE, showWarnings = FALSE); work <- normalizePath(work, winslash = '/')
  R2D_F <- file.path(work, 'R2D'); R2E_F <- file.path(work, 'R2E'); dir.create(R2E_F)
  source(file.path(code, 'r2e_upstream_math.R')); suppressPackageStartupMessages({ library(jsonlite); library(digest) })
  info <- smoke_build_r2d(R2D_F, code)
  # 子进程继承本进程环境变量（Windows 上 system2 的 env 参数不可用）
  Sys.setenv(R2E_ROOT = R2E_F, R2D_ROOT = R2D_F, R2E_RUN_H4 = '1', R2E_DRYRUN = '0', R2E_CODE = code)
  rs <- file.path(R.home('bin'), if (.Platform$OS.type == 'windows') 'Rscript.exe' else 'Rscript')
  out <- suppressWarnings(system2(rs, shQuote(file.path(code, 'r2e_00_contract.R')), stdout = TRUE, stderr = TRUE))
  writeLines(out, file.path(work, 'smoke_contract_console.txt'))
  res <- list(); rec <- function(test, result, note = '') {
    res[[length(res) + 1]] <<- data.frame(test = test, result = result, note = substr(paste(note, collapse = ' '), 1, 300), stringsAsFactors = FALSE)
    cat(sprintf('%-34s %-5s %s\n', test, result, substr(paste(note, collapse = ' '), 1, 120))) }
  if (!any(grepl('CONTRACT FROZEN', out))) { cat(out, sep = '\n'); stop('smoke contract step failed; see smoke_contract_console.txt') }
  Sys.setenv(R2E_SOURCE_ONLY = '1'); source(file.path(code, 'r2e_run.R')); Sys.unsetenv('R2E_SOURCE_ONLY')
  if (is.function(hook)) hook()
  rec('contract_frozen', 'PASS', R2E_F)
  skip_lat <- identical(Sys.getenv('R2E_SMOKE_SKIP_LATENT'), '1'); z <- 'SD'
  IFACE <- c('INPUT_REJECTED', 'EXTRACTION_FAILED', 'KEY_PATH_ERROR', 'PRINTED_MISMATCH', 'NO_OUTPUT', 'ESTIMATION_FAILED')
  calls <- list(); keep <- function(nm, a) { calls[[nm]] <<- a; a }
  batch_clock('B1'); batch_clock('H4')
  # 顺序：线性 → 观测LMS → 边界 → H4 → 潜路线（最慢，放最后）
  e0 <- keep('E0', run_one(z, 'E0', 1, 'smoke', 'PILOT', 'B1'))
  e1 <- keep('E1_q15', run_one(z, 'E1', 1, 'smoke_q15', 'PILOT', 'B1', points = 15, warm = list(from = e0$dest, add = XW_E)))
  e1p <- keep('E1_q15_p4', run_one(z, 'E1', 1, 'smoke_q15p4', 'CHECK', 'B1', points = 15, processors = 4L, warm = list(from = e0$dest, add = XW_E)))
  e1s <- keep('E1_q15_default_start', run_one(z, 'E1', 1, 'smoke_start', 'CHECK', 'B1', points = 15))
  e0b <- keep('E0B', run_one(z, 'E0B', 1, 'smoke', 'BOUNDARY', 'B1', warm = list(from = e0$dest)))
  e1b <- keep('E1B_q15', run_one(z, 'E1B', 1, 'smoke_q15', 'BOUNDARY', 'B1', points = 15, warm = list(from = e1$dest)))
  h4e <- keep('H4_EDU_q15', run_one(z, 'H4_EDU', 1, 'smoke_q15', 'PILOT', 'H4', points = 15, warm = list(from = e1$dest, add = h4_add('EDU'))))
  h4i <- keep('H4_INC_q15', run_one(z, 'H4_INC', 1, 'smoke_q15', 'PILOT', 'H4', points = 15, warm = list(from = e1$dest, add = h4_add('INC'))))
  h4b <- keep('H4B_EDU_q15', run_one(z, 'H4B_EDU', 1, 'smoke_q15', 'PILOT', 'H4', points = 15, warm = list(from = e1b$dest, add = h4_add('EDU'))))
  if (!skip_lat) {
    d0 <- keep('D0', run_one(z, 'D0', 1, 'smoke', 'PROBE', 'B1'))
    d0b <- keep('D0B', run_one(z, 'D0B', 1, 'smoke', 'PROBE', 'B1', warm = list(from = d0$dest)))
    keep('D1L_q10', run_one(z, 'D1L', 1, 'smoke_q10', 'PROBE', 'B1', points = 10, warm = list(from = d0$dest, add = XW_D)))
    keep('D1B_q10', run_one(z, 'D1B', 1, 'smoke_q10', 'PROBE', 'B1', points = 10, warm = list(from = d0b$dest, add = XW_D)))
  }
  # ---- 1) 接口：每次调用正常结束且读回成功（D1 超时记 WARN：只说明合成数据上未在时限内结束）
  for (nm in names(calls)) { r <- calls[[nm]]$receipt
    ok <- !(r$status %in% IFACE) && isTRUE(r$normal)
    rec(paste0('call_', nm), if (ok) 'PASS' else if (grepl('^D1', nm) && r$status == 'TIMEOUT') 'WARN' else 'FAIL',
        c(r$status, 'normal', isTRUE(r$normal), 'seconds', round(as.numeric(nz0(r$seconds)), 1), 'iter', nz0(r$iterations), 'dims', nz0(r$integration_dimensions))) }
  # ---- 2) 起点拼接：源参数全部带入；预定新增语句全部加入且没有多余语句（边界规格另加 sy@0，若源中尚无）
  adds <- list(E1_q15 = XW_E, E1_q15_p4 = XW_E, E0B = character(0), E1B_q15 = character(0), H4_EDU_q15 = h4_add('EDU'), H4_INC_q15 = h4_add('INC'),
               H4B_EDU_q15 = h4_add('EDU'), D0B = character(0), D1L_q10 = XW_D, D1B_q10 = XW_D)
  for (nm in intersect(names(adds), names(calls))) { f <- file.path(calls[[nm]]$dest, 'start_mapping.csv')
    if (!file.exists(f)) { rec(paste0('splice_', nm), 'FAIL', 'start_mapping.csv missing'); next }
    mp <- utils::read.csv(f, stringsAsFactors = FALSE); al <- mp$line[mp$action == 'added_new_statement']; nc <- sum(mp$action == 'copied_start')
    ok <- nc > 0 && !any(grepl('mismatch|without SVALUES', mp$action)) && all(toupper(stmt_key(adds[[nm]])) %in% toupper(stmt_key(al))) && !length(setdiff(al, c(adds[[nm]], 'sy@0;')))
    rec(paste0('splice_', nm), if (ok) 'PASS' else 'FAIL', c('copied', nc, 'added', length(al), 'planned', length(adds[[nm]]), 'dropped_SY_start', sum(mp$action == 'dropped_for_fixed_zero'))) }
  # ---- 3) 边界规格：输入含 sy@0，输出中 SY 残差方差为固定 0（Mplus 以 999.000 标示固定参数）
  for (nm in grep('^(E0B|E1B|H4B|D0B|D1B)', names(calls), value = TRUE)) {
    inp <- readLines(file.path(calls[[nm]]$dest, 'model.inp'), warn = FALSE); of <- file.path(calls[[nm]]$dest, 'model.out')
    L <- if (file.exists(of)) readLines(of, warn = FALSE, encoding = 'latin1') else character(0)
    fixed <- any(grepl('^\\s+SY\\s+0\\.000\\s+0\\.000\\s+999\\.000\\s+999\\.000', L))
    rec(paste0('sy_fixed_', nm), if (any(trimws(inp) == 'sy@0;') && fixed) 'PASS' else 'FAIL', c('input_sy@0', any(trimws(inp) == 'sy@0;'), 'output_fixed_row', fixed)) }
  # ---- 4) 数值核查：4核与单核一致（合同容差）；默认起点与拼接起点一致；记录耗时比
  if (ok_member(e1) && ok_member(e1p)) { cmp <- compare_numeric(e1, e1p, 'processors')
    rat <- as.numeric(e1p$receipt$seconds) / as.numeric(e1$receipt$seconds)
    rec('processors_4_vs_1_numeric', if (isTRUE(cmp$passed)) 'PASS' else 'FAIL', c('dLL', signif(nz0(cmp$delta_LL), 3), 'max_path/SE', signif(nz0(cmp$max_path_over_SE), 3), 'time_ratio_4_over_1', round(rat, 3)))
  } else rec('processors_4_vs_1_numeric', 'FAIL', 'one of the two runs not USABLE')
  rec('processors_input_line', if (any(grepl('PROCESSORS=4;', readLines(file.path(e1p$dest, 'model.inp'))))) 'PASS' else 'FAIL')
  so <- start_outcome(e1, e1s); rec('start_default_vs_spliced', if (isTRUE(so$passed)) 'PASS' else 'WARN', c(so$outcome, 'dLL', signif(nz0(so$alt_minus_adopted_LL), 3)))
  # ---- 5) 合成数据恢复（宽容差：|估计−真值| ≤ max(4SE, .10)；E1 无G时的真值为边际 dc + dcg·P(c2=1)）
  kp <- function(a, lab) { if (is.null(a$key)) return(c(NA, NA)); k <- a$key[a$key$label == lab, ]; if (nrow(k)) c(k$estimate[1], k$se[1]) else c(NA, NA) }
  near <- function(nm, a, lab, truth) { v <- kp(a, lab); ok <- all(is.finite(v)) && abs(v[1] - truth) <= max(4 * v[2], .10)
    rec(nm, if (ok) 'PASS' else 'FAIL', c('estimate', signif(v[1], 3), 'se', signif(v[2], 3), 'truth', signif(truth, 3))) }
  near('recover_E1_dc_marginal', e1, 'dc', SMOKE_TRUTH[['dc']] + SMOKE_TRUTH[['dcg']] * info$mean_c2)
  near('recover_H4_EDU_delta0', h4e, 'dc', SMOKE_TRUTH[['dc']]); near('recover_H4_EDU_deltaG', h4e, 'dcg', SMOKE_TRUTH[['dcg']])
  near('recover_H4_INC_deltaG_null', h4i, 'dcg', 0)
  # ---- 6) 积分维数
  dims <- function(a) as.integer(nz0(a$receipt$integration_dimensions, NA))
  rec('integration_dims_E1_H4', if (identical(dims(e1), 1L) && identical(dims(h4e), 1L)) 'PASS' else 'FAIL', c(dims(e1), dims(h4e)))
  if (!skip_lat && !is.null(calls$D1L_q10)) rec('integration_dims_D1', if (identical(dims(calls$D1L_q10), 2L)) 'PASS' else 'WARN', dims(calls$D1L_q10))
  # ---- 汇总
  tab <- do.call(rbind, res); dir.create(file.path(R2E_F, 'results'), showWarnings = FALSE)
  utils::write.csv(tab, file.path(R2E_F, 'results', 'SMOKE_RESULTS.csv'), row.names = FALSE)
  tim <- vapply(calls, function(a) as.numeric(nz0(a$receipt$seconds, NA)), 0)
  wj(list(passed = !any(tab$result == 'FAIL'), n_pass = sum(tab$result == 'PASS'), n_warn = sum(tab$result == 'WARN'), n_fail = sum(tab$result == 'FAIL'),
          synthetic_N = info$n, seconds_by_call = as.list(tim), machine = Sys.info()[c('sysname', 'release', 'machine')], R = R.version.string,
          note = 'Synthetic data only. Timings indicate relative cost, not the CFPS run time.'), file.path(R2E_F, 'results', 'SMOKE_SUMMARY.json'))
  cat(if (any(tab$result == 'FAIL')) 'SMOKE FAILED' else 'SMOKE PASSED', sum(tab$result == 'PASS'), 'pass,', sum(tab$result == 'WARN'), 'warn,', sum(tab$result == 'FAIL'), 'fail\n')
  invisible(tab)
}
nz0 <- function(x, d = NA) if (is.null(x) || !length(x)) d else x
if (!identical(Sys.getenv('R2E_SMOKE_SOURCE_ONLY'), '1')) {
  a <- commandArgs(TRUE); if (length(a) != 1) stop('Usage: Rscript r2e_smoke_mplus.R <new empty directory>')
  tab <- smoke_main(a[1]); if (any(tab$result == 'FAIL')) quit(status = 1)
}
