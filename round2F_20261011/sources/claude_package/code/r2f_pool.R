# Round2F 汇总：只有十份同规格、同固定值、同数值精度且全部 USABLE 的家族才合并；其余保留显式状态。
# 公开输出只有模型参数、参数协方差与汇总量，无逐人记录、无插补对象。
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())
val <- function(x, default = NA) if (is.null(x) || !length(x)) default else x
bind <- function(xs, note) if (length(xs)) do.call(rbind, xs) else data.frame(note = note)

single_model <- function(r) {
  # 单个模型的关键路径与条件斜率（SE 取该模型参数协方差的二次型；不是 MI 合并结果）
  if (is.null(r$dest) || !file.exists(file.path(r$dest, 'key_paths.csv'))) return(NULL)
  kp <- utils::read.csv(file.path(r$dest, 'key_paths.csv'))
  V <- as.matrix(utils::read.csv(file.path(r$dest, 'parameter_covariance.csv'), header = FALSE))
  g <- function(l) if (l %in% kp$label) kp[kp$label == l, ] else NULL
  out <- data.frame(id = r$id, spec = r$spec, status = r$status, data_tag = val(r$data_tag, 'Z0'), estimator = val(r$estimator, 'MLR'),
                    cluster = val(r$cluster, TRUE), LL = val(r$LL), scaling = val(r$scaling), SY = val(r$sy),
                    exact_LL_difference = val(r$exact_LL_difference), N = val(r$N), households = val(r$households))
  for (l in c('bss', 'gs0', 'gi0', 'dc')) { k <- g(l); out[[paste0(l, '_est')]] <- if (is.null(k)) NA else k$estimate; out[[paste0(l, '_se')]] <- if (is.null(k)) NA else k$se }
  if (!is.null(g('dc'))) {
    i <- c(g('bss')$parameter, g('dc')$parameter); Vi <- V[i, i]
    for (p in c('raw_zero', 'positive_median', 'P90')) {
      a <- c(1, SUPPORT_SD[[p]]); out[[paste0('slope_', p)]] <- sum(a * c(g('bss')$estimate, g('dc')$estimate))
      out[[paste0('slope_', p, '_se')]] <- sqrt(drop(t(a) %*% Vi %*% a))
    }
  }
  out
}

build_results_2f <- function() {
  S <- rj(file.path(ROOT, 'runtime/selection_2f.json')); RES <- file.path(ROOT, 'results'); dir.create(RES, showWarnings = FALSE)
  rf <- list.files(file.path(ROOT, 'models'), pattern = '^(receipt|not_run)\\.json$', recursive = TRUE, full.names = TRUE)
  rr <- lapply(rf, rj)
  exe <- bind(lapply(rr, function(r) data.frame(id = r$id, spec = val(r$spec, ''), member = val(r$member), attempt = val(r$attempt, ''),
    category = val(r$category, ''), sample = val(r$sample, ''), data_tag = val(r$data_tag, ''), conv = val(r$conv, ''), estimator = val(r$estimator, ''),
    cluster = val(r$cluster), points = val(r$points), status = r$status, seconds = val(r$seconds), wall_seconds = val(r$wall_seconds),
    gap_seconds = val(r$gap_seconds), keep_awake = val(r$keep_awake, ''), LL = val(r$LL), SY = val(r$sy), scaling = val(r$scaling),
    iterations = val(r$convergence$iterations), last_abs_change = val(r$convergence$last_abs_change),
    criteria = paste(val(r$convergence$loglik_change, ''), val(r$convergence$relative_change, '')), ill_conditioned = val(r$ill_conditioned),
    exact_LL = val(r$exact_LL), exact_LL_difference = val(r$exact_LL_difference), exact_LL_n_match = val(r$exact_LL_n_match),
    negative = paste(unlist(r$negative), collapse = ';'), error = val(r$error, ''))), 'no receipts')
  csv(exe, file.path(RES, 'MODEL_EXECUTION_2F.csv'))
  csv(exe[, intersect(c('id', 'status', 'exact_LL', 'LL', 'exact_LL_difference', 'exact_LL_n_match'), names(exe))], file.path(RES, 'EXACT_LL_2F.csv'))
  # 数值检查
  nc <- list()
  for (st in c('F1', 'F2')) if (!is.null(S[[st]])) {
    s <- S[[st]]; ck <- s$start_check; ig <- s$integration_check
    nc[[length(nc) + 1L]] <- data.frame(step = st, a = val(s$a$id, ''), a_status = val(s$a$status, ''), b = val(s$b$id, ''), b_status = val(s$b$status, ''),
      start_outcome = val(ck$outcome, ''), delta_LL = val(ck$delta_LL), max_path_over_SE = val(ck$max_path_over_SE), max_SE_relative = val(ck$max_SE_relative),
      best = val(s$best, ''), q30 = val(s$q30$id, ''), integration_outcome = val(ig$outcome, ''), passed = isTRUE(s$passed))
  }
  csv(bind(nc, 'numeric steps not run'), file.path(RES, 'NUMERIC_CHECKS_2F.csv'))
  # 严格收敛相对 Round2E 默认收敛的变化（只作记录）
  tv <- list(); r2 <- function(id) rj(file.path(r2e_model(id), 'receipt.json'))
  pairs <- list(c('F1', 'a', C2F$round2E_inputs$SD_E1B_01$id), c('F2', 'b', C2F$round2E_inputs$SD_E1_q15$id))
  for (p in pairs) { s <- S[[p[1]]][[p[2]]]; o <- r2(p[3])
    if (!is.null(s$LL)) tv[[length(tv) + 1L]] <- data.frame(round2F = s$id, round2E = p[3], LL_2F = s$LL, LL_2E = o$LL, delta_LL = s$LL - o$LL,
      SY_2F = val(s$sy), SY_2E = val(o$sy), iterations_2F = val(s$convergence$iterations), status_2F = s$status, status_2E = o$status) }
  csv(bind(tv, 'not run'), file.path(RES, 'TIGHT_VS_DEFAULT_2F.csv'))
  # 家族与合并
  fam <- paths <- slopes <- mats <- list()
  for (f in names(S$families)) {
    F <- S$families[[f]]; st <- vapply(as.character(1:10), function(k) val(F$members[[k]]$status, 'NOT_RUN'), '')
    complete <- all(st == 'USABLE')
    role <- if (identical(f, S[['primary']])) 'PRIMARY' else 'SENSITIVITY_STRONG_CONSTRAINT'
    if (identical(f, 'E1B') && identical(S$decision, 'B')) role <- 'STRONG_CONSTRAINT_SY0_ONLY_FAMILY'
    fam[[length(fam) + 1L]] <- data.frame(family = f, role = role, status = if (complete) 'POOLED' else F$status, n_usable = sum(st == 'USABLE'),
      member_statuses = paste(st, collapse = ';'), repairs = length(F$repairs))
    if (!complete) next
    labels <- spec('SD', F$spec)$key$label
    Q <- matrix(NA_real_, 10, length(labels), dimnames = list(sprintf('MI%02d', 1:10), labels)); U <- list()
    for (k in 1:10) {
      m <- F$members[[as.character(k)]]; key <- utils::read.csv(file.path(m$dest, 'key_paths.csv')); key <- key[match(labels, key$label), ]
      v <- as.matrix(utils::read.csv(file.path(m$dest, 'parameter_covariance.csv'), header = FALSE))
      Q[k, ] <- key$estimate; U[[k]] <- v[key$parameter, key$parameter, drop = FALSE]
    }
    pooled <- pool_ten(Q, U); tb <- pooled$table
    tb$FMI <- ((1 + 1/10) * diag(pooled$B) / diag(pooled$W) + 2 / (tb$df + 3)) / ((1 + 1/10) * diag(pooled$B) / diag(pooled$W) + 1)
    tb$CI_width <- tb$upper - tb$lower; tb$label <- labels; tb$family <- f; tb$role <- role
    paths[[length(paths) + 1L]] <- tb; mats[[f]] <- list(Q = Q, U = U, W = pooled$W, B = pooled$B, T = pooled$T)
    for (p in c('raw_zero', 'positive_median', 'P90')) {
      a <- setNames(rep(0, length(labels)), labels); a['bss'] <- 1; a['dc'] <- SUPPORT_SD[[p]]
      slopes[[length(slopes) + 1L]] <- cbind(family = f, role = role, point = p, z = SUPPORT_SD[[p]], pool_contrast(Q, U, a))
    }
    a <- setNames(rep(0, length(labels)), labels); a['dc'] <- SUPPORT_SD[['P90']] - SUPPORT_SD[['raw_zero']]
    slopes[[length(slopes) + 1L]] <- cbind(family = f, role = role, point = 'P90_minus_raw_zero (same test as dc)',
                                           z = SUPPORT_SD[['P90']] - SUPPORT_SD[['raw_zero']], pool_contrast(Q, U, a))
  }
  ff <- bind(fam, 'no family run'); pt <- bind(paths, 'No complete admissible family; no pooled estimate')
  csv(ff, file.path(RES, 'FAMILY_STATUS_2F.csv')); csv(pt, file.path(RES, 'POOLED_KEY_PATHS_2F.csv'))
  csv(bind(slopes, 'no pooled family'), file.path(RES, 'CONDITIONAL_SLOPES_2F.csv'))
  wj(mats, file.path(RES, 'MI_PARAMETER_MATRICES_2F.json'))
  # 多重性：dc 沿用 Round2E 四分支固定家族（Holm, n=4）；只有主规格进入家族
  p <- rep(NA_real_, 4)
  if ('label' %in% names(pt) && !is.null(S[['primary']])) { h <- pt$family == S[['primary']] & pt$label == 'dc' & pt$role == 'PRIMARY'; if (any(h)) p[1] <- pt$p[h] }
  csv(data.frame(z = c('SD', 'SEXGAP', 'OLDEST', 'SONGAP'), label = 'dc', p = p, holm = fixed_holm(p, 4), family_size = 4,
                 note = 'only the primary (free-SY) family enters; E1B rows are labelled sensitivity'), file.path(RES, 'MULTIPLICITY_2F.csv'))
  # 敏感性与诊断（单份模型，不是 MI 合并）
  D <- S$diagnostics; diag_rows <- list()
  ref <- if (!is.null(D$N2$reference)) Filter(function(r) identical(r$id, D$N2$reference), rr) else list()
  for (r in c(ref, list(D$N2$ml, D$N2$mlr), D$F5, list(D$F6$E0, D$F6$E1x, D$O1), list(S$F1$a, S$F1$b, S$F2$a, S$F2$b))) {
    if (is.null(r$id)) next
    x <- single_model(r); if (is.null(x)) x <- data.frame(id = r$id, spec = val(r$spec, ''), status = r$status)
    diag_rows[[length(diag_rows) + 1L]] <- x
  }
  if (length(diag_rows)) { nm <- unique(unlist(lapply(diag_rows, names)))
    diag_rows <- lapply(diag_rows, function(x) { for (n in setdiff(nm, names(x))) x[[n]] <- NA; x[, nm] }) }
  sens <- bind(diag_rows, 'no diagnostics'); sens <- sens[!duplicated(sens$id), , drop = FALSE]
  csv(sens, file.path(RES, 'SENSITIVITY_2F.csv'))
  # SE 分解与朴素LR（只作解释；Round2E 已示 SB2001 缩放差的 cd ≤ 0，不能据此作缩放检验）
  se <- list()
  if (!is.null(D$N2$reference) && 'dc_se' %in% names(sens)) {
    for (id in c(D$N2$reference, val(D$N2$ml$id, ''), val(D$N2$mlr$id, ''))) { h <- sens[sens$id == id, ]
      if (nrow(h)) se[[length(se) + 1L]] <- data.frame(id = id, estimator = h$estimator, cluster = h$cluster, dc = h$dc_est, dc_se = h$dc_se, wald_z2 = (h$dc_est / h$dc_se)^2, LL = h$LL) }
    nested <- if (identical(S[['primary']], 'E1')) C2F$round2E_inputs$SD_E0$ids[[1]] else C2F$round2E_inputs$SD_E0B_01$id
    m0 <- read_mplus_raw(r2e_model(nested)); L0 <- m0$extra[['H0 Loglikelihood']]; c0 <- m0$extra[['H0 Scaling Correction Factor for MLR']]
    rf1 <- Filter(function(r) identical(r$id, D$N2$reference), rr)[[1]]
    lr <- data.frame(id = paste('naive LR vs', nested), estimator = 'LR', cluster = NA, dc = NA, dc_se = NA, wald_z2 = 2 * (rf1$LL - L0), LL = L0)
    sb <- sb_test(L0, c0, m0$P, rf1$LL, val(rf1$scaling), rf1$parameters)
    lr$note <- if (is.finite(sb$cd) && sb$cd > 0) paste('SB2001 cd =', signif(sb$cd, 4), 'TRd =', signif(sb$TRd, 4), '(descriptive only; the pre-specified test is the Wald test of dc)')
               else paste('SB2001 cd =', signif(sb$cd, 4), '(not computable; the pre-specified test is the Wald test of dc)')
    se <- lapply(se, function(x) { x$note <- ''; x }); se[[length(se) + 1L]] <- lr
  }
  csv(bind(se, 'N2 not run'), file.path(RES, 'SE_DECOMPOSITION_2F.csv'))
  # 电源与挂起
  ka <- rj(file.path(ROOT, 'runtime/keep_awake_2f.json'))
  pw <- exe[, intersect(c('id', 'seconds', 'wall_seconds', 'gap_seconds', 'keep_awake'), names(exe)), drop = FALSE]
  csv(pw, file.path(RES, 'POWER_2F.csv'))
  dec <- list(decision = S$decision, primary = S[['primary']], primary_label = S$primary_label, convergence = S$convergence,
              F1_passed = isTRUE(S$F1$passed), F2_passed = isTRUE(S$F2$passed), families = ff, terminal = S$terminal,
              budget = rj(file.path(ROOT, 'runtime/budget_status.json'))[c('calls', 'engine_seconds', 'wall_seconds')],
              keep_awake = ka[c('state', 'end_reason', 'suspend_gaps')], p0 = rj(file.path(ROOT, 'audit/P0_STATUS_2F.json')),
              smoke = rj(file.path(ROOT, 'audit/SMOKE_2F.json')),
              inference = paste('Conditional on the household-person MI and the fixed SW working model; observed Z0 is not latent IZ;',
                                'E1B fixes the SY residual at zero and its intervals do not include uncertainty about choosing that constraint;',
                                'single-model diagnostics are not MI-pooled evidence.'))
  wj(dec, file.path(RES, 'DECISION_2F.json'))
  progress('results_2f_written', paste('decision', val(S$decision, 'NA')))
  invisible(dec)
}
if (sys.nframe() == 0L || identical(Sys.getenv('R2F_RUN_MAIN'), '1')) build_results_2f()
