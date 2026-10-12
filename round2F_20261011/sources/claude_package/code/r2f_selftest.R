# Round2F 自检：零次 Mplus 调用，只读 Round2E 已有输出。需要私有数据的项在无数据环境（云端）记为 SKIPPED。
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())
selftest_2f <- function() {
  rows <- list()
  add <- function(name, expr) {
    res <- tryCatch({ v <- eval.parent(substitute(expr)); if (identical(v, 'SKIPPED')) 'SKIPPED' else if (isTRUE(v)) 'PASS' else 'FAIL' },
                    error = function(e) paste('ERROR:', conditionMessage(e)))
    rows[[length(rows) + 1L]] <<- data.frame(test = name, result = res)
  }
  e1b <- r2e_model(C2F$round2E_inputs$SD_E1B_01$id); e0 <- r2e_model(C2F$round2E_inputs$SD_E0$ids[[1]])
  ctrl <- 'c1-c24'
  # 1 合同自洽
  add('contract_category_sum', sum(unlist(C2F$budget$categories)) == C2F$budget$max_calls)
  add('reused_code_hashes', all(vapply(names(C2F$reused_round2E_code_sha256), function(f) identical(hashf(file.path(ROOT, 'code', f)), C2F$reused_round2E_code_sha256[[f]]), TRUE)))
  # 2 规格与自由参数清单
  sF <- spec('SD', 'E1F034', ctrl); sB <- spec('SD', 'E1B', ctrl); s1 <- spec('SD', 'E1', ctrl)
  add('E1F_syntax', 'sy@0.034;' %in% sF$model && !'sy@0;' %in% sF$model && length(sF$fixed_zero) == 0L)
  add('E1F_slots_equal_E1B', identical(slots(sF)$key, slots(sB)$key))
  add('E1_slots_E1B_plus_VAR_SY', setequal(setdiff(slots(s1)$key, slots(sB)$key), 'VAR:SY:') && nrow(slots(s1)) == nrow(slots(sB)) + 1L)
  add('E1F_grid_names', all(vapply(c('E1F020', 'E1F034', 'E1F080'), function(x) abs(spec('SD', x, ctrl)$fixed_value[['SY']] - as.integer(substr(x, 4, 6)) / 1000) < 1e-12, TRUE)))
  # 3 输入文本
  mmB <- make_model(sB, e1b)
  add('inp_cluster_identical_to_round2E', identical(inp_text_r2f('t', sB$use, analysis_r2e('lms_observed', 20, 1), mmB$lines, 'lms', TRUE),
                                                    inp_text('t', sB$use, analysis_r2e('lms_observed', 20, 1), mmB$lines, kind = 'lms')))
  add('analysis_default_identical_to_round2E', identical(analysis_r2f('lms_observed', 20, 1, 'default'), analysis_r2e('lms_observed', 20, 1)) &&
        identical(analysis_r2f('linear', 20, 1, 'default'), analysis_r2e('linear', 20, 1)))
  tl <- analysis_r2f('lms_observed', 20, 1, 'tight')
  add('analysis_tight_lines', any(grepl('LOGCRITERION=0.00001;', tl, fixed = TRUE)) && any(grepl('RLOGCRITERION=0.000000001;', tl, fixed = TRUE)))
  nc <- inp_text_r2f('t', sB$use, analysis_r2f('lms_observed', 20, 1, 'tight', 'ML', FALSE), mmB$lines, 'lms', FALSE)
  add('inp_nocluster_ml', !any(grepl('CLUSTER', nc)) && any(grepl('TYPE=RANDOM; ESTIMATOR=ML; PROCESSORS=1;', nc, fixed = TRUE)) && all(nchar(nc) <= 90))
  # 4 起点映射
  add('E1B_to_E1_without_override_stops', inherits(tryCatch(make_model(s1, e1b), error = function(e) e), 'error'))
  mm1 <- make_model(s1, e1b, start_override = C2F$allowed_start_override)
  mp <- mm1$mapping; m <- read_mplus_raw(e1b); kp <- key_paths_r2e(m, sB$key)
  add('E1B_to_E1_override_VAR_SY', mp$value[mp$key == 'VAR:SY:'] == 0.02 && mp$action[mp$key == 'VAR:SY:'] == 'contract_start_override' &&
        any(grepl('^sy\\*0.02;$', mm1$lines)))
  add('E1B_to_E1_all_other_mapped', all(mp$action[mp$key != 'VAR:SY:'] == 'mapped_high_precision'))
  add('E1B_to_E1_dc_start_equals_E1B_dc', abs(mp$value[mp$key == 'ON:SY:SXZ'] - kp$estimate[kp$label == 'dc']) < 1e-12)
  add('override_key_not_in_contract_rejected', inherits(tryCatch(make_model(s1, e1b, start_override = list(`VAR:IX` = .1)), error = function(e) e), 'error'))
  mmF <- make_model(sF, e1b)
  add('E1B_to_E1F_free_count', mmF$expected_free == m$P && !any(mmF$mapping$key == 'VAR:SY:') && any(grepl('^sy@0.034;$', mmF$lines)))
  mm0 <- make_model(sB, e0)
  add('E0_to_E1B_new_product_start', mm0$mapping$action[mm0$mapping$key == 'ON:SY:SXZ'] == 'new_start' && mm0$mapping$value[mm0$mapping$key == 'ON:SY:SXZ'] == 0)
  add('E1B_free_count_matches_round2E', m$P == rj(file.path(e1b, 'receipt.json'))$parameters)
  # 5 输出读取
  ci <- conv_info(readLines(file.path(e1b, 'model.out'), warn = FALSE, encoding = 'latin1'))
  add('conv_info_round2E_E1B', identical(ci$loglik_change, '0.100D-02') && identical(ci$relative_change, '0.100D-05') && identical(ci$derivative, '0.100D-02') &&
        ci$iterations == 43L && abs(ci$last_abs_change - 0.0009629) < 1e-9)
  add('LL_extra_equals_receipt', abs(m$extra[['H0 Loglikelihood']] - rj(file.path(e1b, 'receipt.json'))$LL) < 1e-9)
  # 6 合并复现 Round2E SD E0
  labels <- spec('SD', 'E0', ctrl)$key$label; Q <- matrix(NA_real_, 10, length(labels), dimnames = list(NULL, labels)); U <- list()
  for (k in 1:10) {
    d <- r2e_model(C2F$round2E_inputs$SD_E0$ids[[k]]); key <- utils::read.csv(file.path(d, 'key_paths.csv')); key <- key[match(labels, key$label), ]
    v <- as.matrix(utils::read.csv(file.path(d, 'parameter_covariance.csv'), header = FALSE)); Q[k, ] <- key$estimate; U[[k]] <- v[key$parameter, key$parameter, drop = FALSE]
  }
  pr <- pool_ten(Q, U)$table; old <- utils::read.csv(file.path(R2E, 'results/POOLED_KEY_PATHS.csv')); old <- old[old$z == 'SD' & old$spec == 'E0', ]
  old <- old[match(labels, old$label), ]
  add('pool_reproduces_round2E_SD_E0', max(abs(pr$estimate - old$estimate)) < 1e-8 && max(abs(pr$se - old$se)) < 1e-8)
  # 7 条件斜率对比代数：zH−zL 对比与 dc 同一检验
  set.seed(26101010); lab <- c('bss', 'dc'); Qs <- matrix(rnorm(20, c(-.3, .1), .05), 10, 2, byrow = TRUE, dimnames = list(NULL, lab))
  Us <- lapply(1:10, function(i) { a <- matrix(c(.04, -.01, -.01, .02), 2); a * (1 + i / 50) })
  t1 <- pool_contrast(Qs, Us, c(0, SUPPORT_SD[['P90']] - SUPPORT_SD[['raw_zero']])); t2 <- pool_contrast(Qs, Us, c(0, 1))
  add('slope_difference_same_test_as_dc', abs(t1$estimate / t1$se - t2$estimate / t2$se) < 1e-10 && abs(t1$p - t2$p) < 1e-12)
  a <- c(1, SUPPORT_SD[['positive_median']]); q <- Qs %*% a; T <- pool_ten(Qs, Us)$T
  add('slope_contrast_matches_quadratic_form', abs(pool_contrast(Qs, Us, a)$se - sqrt(drop(t(a) %*% T %*% a))) < 1e-10 && abs(mean(q) - pool_contrast(Qs, Us, a)$estimate) < 1e-12)
  add('holm_fixed_family', isTRUE(all.equal(fixed_holm(c(.01, NA, NA, NA), 4), c(.04, NA, NA, NA))))
  # 8 数值检查复现 Round2E 合成冒烟（起点）
  syn <- function(id) { r <- rj(file.path(r2e_model(id), 'receipt.json')); r$dest <- r2e_model(id); r }
  ck <- numeric_check(syn(C2F$round2E_inputs$SYN_E1$id), syn(C2F$round2E_inputs$SYN_E1_start$id), 'start')
  add('numeric_check_reproduces_round2E_smoke', isTRUE(ck$passed) && abs(ck$max_path_over_SE - 0.000120377113291281) < 1e-9)
  # 9 精确LL核对器（需要数据文件；Round2E 合成数据在本机 Round2E 冒烟目录中）
  for (nm in c('SYN_E0', 'SYN_E1', 'SYN_E1B')) {
    d <- r2e_model(C2F$round2E_inputs[[nm]]$id)
    add(paste('exact_ll', nm), if (!file.exists(file.path(d, 'data.dat'))) 'SKIPPED' else {
      out <- file.path(tempdir(), paste0(nm, '_exact.json')); unlink(out); ex <- exact_ll(d, out)
      is.finite(ex$difference) && abs(ex$difference) <= 1e-3 && isTRUE(ex$n_matches_mplus) })
  }
  cfps <- file.exists(file.path(e0, 'data.dat'))
  add('exact_ll_CFPS_SD_E0_01', if (!cfps) 'SKIPPED' else { out <- file.path(tempdir(), 'e0_exact.json'); unlink(out); ex <- exact_ll(e0, out); abs(ex$difference) <= C2F$exact_ll$calibration_tolerance })
  # 10 Python 依赖
  py <- tryCatch(processx::run(PY, c('-c', 'import numpy, psutil'), error_on_status = FALSE)$status, error = function(e) 1L)
  add('python_numpy_psutil', identical(as.integer(py), 0L))
  out <- do.call(rbind, rows); dir.create(file.path(ROOT, 'audit'), showWarnings = FALSE)
  csv(out, file.path(ROOT, 'audit/SELFTEST_2F.csv'))
  cat(sprintf('%-45s %s\n', out$test, out$result), sep = '')
  cat('SELFTEST_2F', if (any(grepl('FAIL|ERROR', out$result))) 'FAILED' else 'PASSED', sum(out$result == 'PASS'), 'pass', sum(out$result == 'SKIPPED'), 'skipped\n')
  invisible(out)
}
if (sys.nframe() == 0L || identical(Sys.getenv('R2F_RUN_MAIN'), '1')) selftest_2f()
