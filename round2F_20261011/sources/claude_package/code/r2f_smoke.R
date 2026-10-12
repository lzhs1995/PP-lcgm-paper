# Round2F P1：合成数据 3 次调用（第一次被 Mplus 拒收时另加 1 次后备），核对新收敛准则确实生效、E1F 语法与无聚类 ML 输入可用、
# 精确LL与打印LL一致。合成数据即 Round2E 冒烟所用文件（哈希绑定）。
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())

smoke_run <- function() {
  stopifnot(isTRUE(rj(file.path(ROOT, 'audit/P0_STATUS_2F.json'))$passed))
  syn <- r2e_model(C2F$round2E_inputs$SYN_E1B$id); data <- file.path(syn, 'data.dat')
  stopifnot(identical(hashf(data), C2F$data$synthetic_sha256))
  ref <- rj(file.path(syn, 'receipt.json'))
  common <- list(z = 'SD', sample = 'SYNTHETIC', source_data = data, ctrl = C2F$data$synthetic_ctrl, points = 15L)
  call <- function(sp, attempt, conv, ...) do.call(run_r2f, c(list(sp, 1L, attempt, 'SMOKE', conv = conv, source_dir = syn), common, list(...)))
  conv <- 'tight'
  a <- call('E1B', 'smoke_tight', conv)
  if (identical(a$status, 'INPUT_REJECTED') || identical(a$status, 'CRITERIA_NOT_APPLIED')) { conv <- 'tight_log'; a <- call('E1B', 'smoke_tight_log', conv) }
  b <- call('E1F034', 'smoke_fixed', conv)
  c <- call('E1B', 'smoke_ml_nocluster', conv, estimator = 'ML', cluster = FALSE)
  rows <- list(); add <- function(name, ok, detail = '') rows[[length(rows) + 1L]] <<- data.frame(check = name, passed = isTRUE(ok), detail = paste(detail, collapse = '; '))
  add('tight_usable', usable(a), a$status)
  add('tight_criteria_printed', isTRUE(a$criteria_as_requested), paste(a$convergence$loglik_change, a$convergence$relative_change))
  add('tight_not_worse_than_default', usable(a) && a$LL >= ref$LL - 1e-3, paste(a$LL, 'vs', ref$LL))
  add('tight_exact_ll', usable(a) && is.finite(a$exact_LL_difference) && abs(a$exact_LL_difference) <= C2F$exact_ll$model_tolerance && isTRUE(a$exact_LL_n_match), a$exact_LL_difference)
  add('fixed_usable', usable(b), b$status)
  add('fixed_sy_value', usable(b) && abs(b$sy - 0.034) < 1e-9, b$sy)
  add('fixed_free_count', usable(b) && b$parameters == a$parameters, paste(b$parameters, a$parameters))
  add('fixed_exact_ll', usable(b) && is.finite(b$exact_LL_difference) && abs(b$exact_LL_difference) <= C2F$exact_ll$model_tolerance, b$exact_LL_difference)
  ok_c <- usable(c) && usable(a)
  inp <- if (!is.null(c$dest)) readLines(file.path(c$dest, 'model.inp')) else character(0)
  add('ml_nocluster_usable', usable(c), c$status)
  add('ml_nocluster_syntax', !any(grepl('CLUSTER', inp)) && any(grepl('TYPE=RANDOM; ESTIMATOR=ML;', inp, fixed = TRUE)))
  # 同一模型与数据：LL 与点估计应一致（只换SE口径）。
  if (ok_c) {
    ka <- utils::read.csv(file.path(a$dest, 'key_paths.csv')); kc <- utils::read.csv(file.path(c$dest, 'key_paths.csv'))
    kc <- kc[match(ka$label, kc$label), ]
    add('ml_same_LL', abs(a$LL - c$LL) <= C2F$numerics$start_LL, paste(a$LL, c$LL))
    add('ml_same_estimates', all(abs(ka$estimate - kc$estimate) <= pmax(C2F$numerics$start_path_absolute, C2F$numerics$start_path_SE * ka$se)))
  } else { add('ml_same_LL', FALSE); add('ml_same_estimates', FALSE) }
  ck <- do.call(rbind, rows); csv(ck, file.path(ROOT, 'audit/SMOKE_CHECKS_2F.csv'))
  st <- list(passed = all(ck$passed), convergence_choice = conv, failed = ck$check[!ck$passed],
             calls = vapply(list(a, b, c), function(x) x$id, ''), utc = format(Sys.time(), tz = 'UTC', usetz = TRUE))
  wj(st, file.path(ROOT, 'audit/SMOKE_2F.json')); progress('smoke_done', paste('passed =', st$passed, 'conv =', conv)); invisible(st)
}
if (sys.nframe() == 0L || identical(Sys.getenv('R2F_RUN_MAIN'), '1')) smoke_run()
