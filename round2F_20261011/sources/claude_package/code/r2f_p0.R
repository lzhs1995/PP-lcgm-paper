# Round2F P0：零次 Mplus 调用。绑定输入哈希；用 Round2E 已有输出校准精确LL核对器；准备完整控制与顶端截尾数据。
# 任何必需核对不通过即写 audit/P0_STATUS_2F.json（passed=false）并停止；队列不会在 P0 未通过时启动。
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())

p0_run <- function() {
  dir.create(file.path(ROOT, 'audit/exact_ll_calibration'), recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(ROOT, 'results'), showWarnings = FALSE)
  checks <- list(); add <- function(name, passed, detail = '') checks[[length(checks) + 1L]] <<- data.frame(check = name, passed = isTRUE(passed), detail = paste(detail, collapse = '; '))
  w <- rj(file.path(ROOT, 'runtime/batch_window.json'))
  if (is.null(w)) wj(list(start_utc = format(Sys.time(), '%Y-%m-%dT%H:%M:%SZ', tz = 'UTC'), start_epoch = as.numeric(Sys.time())), file.path(ROOT, 'runtime/batch_window.json'))
  # 1 复用代码与冻结清单
  for (f in names(C2F$reused_round2E_code_sha256)) add(paste('reused_code', f), identical(hashf(file.path(ROOT, 'code', f)), C2F$reused_round2E_code_sha256[[f]]))
  fz <- rj(file.path(ROOT, 'contracts/FROZEN_CODE_2F.json'))
  add('frozen_code_manifest', !is.null(fz) && all(vapply(names(fz), function(f) identical(hashf(file.path(ROOT, 'code', f)), fz[[f]]), TRUE)))
  # 2 Round2E 输出（只读）
  ids <- c(unlist(C2F$round2E_inputs$SD_E0$ids)); shas <- unlist(C2F$round2E_inputs$SD_E0$output_sha256)
  for (nm in setdiff(names(C2F$round2E_inputs), 'SD_E0')) { ids <- c(ids, C2F$round2E_inputs[[nm]]$id); shas <- c(shas, C2F$round2E_inputs[[nm]]$output_sha256) }
  for (i in seq_along(ids)) {
    d <- r2e_model(ids[i]); ok <- file.exists(file.path(d, 'model.out')) && identical(hashf(file.path(d, 'model.out')), shas[i])
    ic <- rj(file.path(d, 'input_contract.json'))
    dok <- !is.null(ic) && file.exists(file.path(d, 'data.dat')) && identical(hashf(file.path(d, 'data.dat')), ic$data_sha256)
    add(paste('round2E_output', ids[i]), ok && dok, if (!ok) 'model.out hash mismatch or missing' else if (!dok) 'data.dat hash mismatch or missing' else '')
  }
  # 3 私有数据成员与支持点
  for (k in 1:10) add(sprintf('SD_member_%02d', k), identical(hashf(datpath('SD', k)), C2F$data$SD_member_sha256[[k]]))
  sp <- utils::read.csv(file.path(R2E, 'contracts/SUPPORT_POINTS.csv')); sp <- sp[sp$z == 'SD', ]
  add('support_points_equal_round2E', isTRUE(all(abs(sp$value - SUPPORT_SD[sp$point]) < 1e-9)) && nrow(sp) == 3L)
  # 4 精确LL校准（SD E0 十份为门槛；其余为记录）
  cal <- list()
  for (id in ids) {
    d <- r2e_model(id); rc <- rj(file.path(d, 'receipt.json'))
    diag <- !identical(rc$status, 'USABLE')
    ex <- exact_ll(d, file.path(ROOT, 'audit/exact_ll_calibration', paste0(id, '.json')), diagnostic = diag)
    cal[[length(cal) + 1L]] <- data.frame(id = id, round2E_status = rc$status, gate = id %in% unlist(C2F$round2E_inputs$SD_E0$ids),
      exact_LL = if (is.null(ex$exact_LL)) NA else ex$exact_LL, printed_LL = if (is.null(ex$mplus_printed_LL)) NA else ex$mplus_printed_LL,
      difference = if (is.null(ex$difference)) NA else ex$difference, n_used = if (is.null(ex$n_used)) NA else ex$n_used,
      mplus_n = if (is.null(ex$mplus_n)) NA else ex$mplus_n, diagnostic_only = isTRUE(ex$diagnostic_only),
      error = if (is.null(ex$error)) '' else substr(ex$error, 1, 300))
  }
  cal <- do.call(rbind, cal); csv(cal, file.path(ROOT, 'results/EXACT_LL_CALIBRATION_2F.csv'))
  g <- cal[cal$gate, ]
  add('exact_ll_calibration_SD_E0', all(is.finite(g$difference)) && max(abs(g$difference)) <= C2F$exact_ll$calibration_tolerance && all(g$n_used == g$mplus_n),
      paste('max |diff| =', signif(max(abs(g$difference)), 3)))
  # 5 完整控制样本：按 Round2D 合同哈希在 R2D 下查找；找不到则 F6 记为未运行，不阻塞。
  ccf <- file.path(ROOT, 'private/SD/CC_member_01.dat'); dir.create(dirname(ccf), recursive = TRUE, showWarnings = FALSE)
  if (!file.exists(ccf)) {
    cand <- list.files(R2D, pattern = '\\.dat$', recursive = TRUE, full.names = TRUE)
    cand <- cand[file.info(cand)$size < 2 * file.info(datpath('SD', 1))$size]
    hit <- Filter(function(f) identical(hashf(f), C2F$data$CC$sha256), cand)
    if (length(hit)) file.copy(hit[[1]], ccf)
  }
  cc <- if (file.exists(ccf)) { x <- read_dat(ccf, R2D_NAMES); list(available = identical(hashf(ccf), C2F$data$CC$sha256), N = nrow(x), households = length(unique(x$fid))) } else list(available = FALSE)
  cc$expected <- C2F$data$CC[c('N', 'households')]; cc$passed <- isTRUE(cc$available) && cc$N == C2F$data$CC$N && cc$households == C2F$data$CC$households
  wj(cc, file.path(ROOT, 'audit/CC_SAMPLE_2F.json'))
  # 6 Z0 顶端截尾（P99，type 7）：只改 z0 一列，成员01；只作可选诊断
  tf <- file.path(ROOT, 'private/SD/Z0TOP99_member_01.dat')
  base <- read_dat(datpath('SD', 1), R2D_NAMES); q <- stats::quantile(base$z0, C2F$data$topcode$quantile, type = 7, na.rm = TRUE, names = FALSE)
  if (!file.exists(tf)) { tc <- base; tc$z0 <- pmin(tc$z0, q); write_dat(tc, tf) }
  tc <- read_dat(tf, R2D_NAMES)
  top <- list(p99 = q, n_changed = sum(abs(tc$z0 - base$z0) > 1e-12, na.rm = TRUE), max_before = max(base$z0, na.rm = TRUE), max_after = max(tc$z0, na.rm = TRUE),
              other_columns_identical = isTRUE(all.equal(as.matrix(tc[, setdiff(R2D_NAMES, 'z0')]), as.matrix(base[, setdiff(R2D_NAMES, 'z0')]), check.attributes = FALSE)),
              sha256 = hashf(tf))
  wj(top, file.path(ROOT, 'audit/TOPCODE_2F.json'))
  add('topcode_data', top$other_columns_identical && top$max_after <= q + 1e-12)
  # 7 Python 依赖
  py <- tryCatch(processx::run(PY, c('-c', 'import numpy, psutil; print(numpy.__version__, psutil.__version__)'), error_on_status = FALSE), error = function(e) list(status = 1, stdout = conditionMessage(e)))
  add('python_numpy_psutil', identical(as.integer(py$status), 0L), trimws(py$stdout))
  ck <- do.call(rbind, checks); csv(ck, file.path(ROOT, 'audit/P0_CHECKS_2F.csv'))
  st <- list(passed = all(ck$passed), failed = ck$check[!ck$passed], cc_available = isTRUE(cc$passed), utc = format(Sys.time(), tz = 'UTC', usetz = TRUE))
  wj(st, file.path(ROOT, 'audit/P0_STATUS_2F.json')); progress('p0_done', paste('passed =', st$passed)); invisible(st)
}
if (sys.nframe() == 0L || identical(Sys.getenv('R2F_RUN_MAIN'), '1')) p0_run()
