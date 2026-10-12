# Round2F 队列（SD 分支）：F1 E1B 同节点双起点 → F2 自由E1 同节点双起点 → 按合同决定 A/A1/B/C →
# 完成目标家族 → 诊断（N2 SE 分解、F5 固定正残差、F6 完整控制、O1 顶端截尾）。不按P值挑选任何步骤。
source(file.path(Sys.getenv('R2F_ROOT'), 'code/r2f_local.R'), local = globalenv())
SEL2F <- file.path(ROOT, 'runtime/selection_2f.json')
save_sel <- function(S) wj(S, SEL2F)
e0_2e <- function(k) r2e_model(sprintf('CFPS_SD_E0_%02d_base', k))
better <- function(a, b) if (usable(a) && (!usable(b) || a$LL >= b$LL)) a else if (usable(b)) b else NULL
ll_gap_ok <- function(r) usable(r) && is.finite(r$exact_LL_difference) && abs(r$exact_LL_difference) <= C2F$exact_ll$model_tolerance && isTRUE(r$exact_LL_n_match)

# 同节点双起点检查。q30 仅在最佳解精确LL差 > 合同阈值时运行一次（NUMERIC 预留额度）。
pair_check <- function(S, step, sp, a, b, conv) {
  chk <- numeric_check(a, b, 'start'); best <- better(a, b); q30 <- NULL; ig <- list(passed = NA, outcome = 'NOT_NEEDED')
  if (!is.null(best) && !ll_gap_ok(best)) {
    q30 <- run_r2f(sp, 1L, paste0(step, '_q30'), 'NUMERIC', conv = conv, points = C2F$q30_points, source_dir = best$dest)
    ig <- numeric_check(best, q30, 'integration')
  }
  pass <- usable(a) && usable(b) && isTRUE(chk$passed) && (ll_gap_ok(best) || isTRUE(ig$passed))
  S[[step]] <- list(a = a, b = b, start_check = chk, best = if (is.null(best)) NULL else best$id, best_dest = if (is.null(best)) NULL else best$dest,
                    q30 = q30, integration_check = ig, passed = pass)
  S
}
run_family <- function(S, fam, sp, mi01, conv) {
  F <- list(spec = sp, members = list(`1` = mi01), status = 'RUNNING')
  b <- budget_r2f(); B <- C2F$budget
  projected <- 9 * B$family_projection_factor * mi01$seconds
  slots_left <- B$categories$TARGET - sum(vapply(b$rows, function(r) identical(r$category, 'TARGET'), TRUE))
  if (projected > min(B$engine_seconds - b$engine_seconds, B$wall_seconds - b$wall_seconds) || slots_left < 9L) {
    F$status <- 'NOT_ESTIMATED_WITHIN_BUDGET'; F$projected_seconds <- projected; S$families[[fam]] <- F; save_sel(S); return(S)
  }
  for (k in 2:10) {
    r <- run_r2f(sp, k, 'fam', 'TARGET', conv = conv, source_dir = mi01$dest)
    if (!usable(r) && !grepl('^NOT_RUN', r$status)) {
      rr <- run_r2f(sp, k, 'famrep', 'REPAIR', conv = conv, source_dir = e0_2e(k))
      F$repairs[[as.character(k)]] <- rr; if (usable(rr)) r <- rr
    }
    F$members[[as.character(k)]] <- r; S$families[[fam]] <- F; save_sel(S)
    if (!usable(r)) { F$status <- if (grepl('^NOT_RUN', r$status)) 'NOT_ESTIMATED_WITHIN_BUDGET' else 'MEMBER_FAILED'; break }
  }
  if (identical(F$status, 'RUNNING')) F$status <- 'COMPLETE_10_USABLE'
  S$families[[fam]] <- F; save_sel(S); S
}

run_queue_2f <- function() {
  stopifnot(isTRUE(rj(file.path(ROOT, 'audit/P0_STATUS_2F.json'))$passed))
  sm <- rj(file.path(ROOT, 'audit/SMOKE_2F.json')); stopifnot(isTRUE(sm$passed))
  conv <- sm$convergence_choice
  S <- rj(SEL2F); if (is.null(S)) S <- list(convergence = conv, families = list(), diagnostics = list())
  tryCatch({
    e1b_2e <- r2e_model(C2F$round2E_inputs$SD_E1B_01$id)
    # F1：E1B 同节点（20点、严格收敛）两套完整起点
    if (is.null(S$F1)) {
      a <- run_r2f('E1B', 1L, 'F1a', 'NUMERIC', conv = conv, source_dir = e1b_2e)
      b <- run_r2f('E1B', 1L, 'F1b', 'NUMERIC', conv = conv, source_dir = e0_2e(1))
      S <- pair_check(S, 'F1', 'E1B', a, b, conv); save_sel(S)
    }
    # F2：自由E1 同节点两套起点；从 E1B 来源回到自由 SY 时，VAR:SY 用合同正起点 0.02
    if (is.null(S$F2)) {
      src <- if (!is.null(S$F1$best_dest)) S$F1$best_dest else NULL
      a <- if (!is.null(src)) run_r2f('E1', 1L, 'F2a', 'NUMERIC', conv = conv, source_dir = src,
                                      start_override = C2F$allowed_start_override) else list(id = 'F2a', status = 'NOT_RUN_NO_E1B_SOURCE', usable = FALSE)
      b <- run_r2f('E1', 1L, 'F2b', 'NUMERIC', conv = conv, source_dir = e0_2e(1))
      S <- pair_check(S, 'F2', 'E1', a, b, conv); save_sel(S)
    }
    f1 <- isTRUE(S$F1$passed); f2 <- isTRUE(S$F2$passed)
    S$decision <- if (f1 && f2) 'A' else if (f2) 'A1' else if (f1) 'B' else 'C'
    S[['primary']] <- switch(S$decision, A = 'E1', A1 = 'E1', B = 'E1B', C = NULL)
    S$primary_label <- switch(S$decision, A = 'free SY (primary); E1B strong-constraint sensitivity', A1 = 'free SY (primary); E1B numerically unstable',
                              B = 'E1B strong constraint SY@0 (sensitivity, not unconstrained moderation inference); free E1 diagnostic only', C = 'no admissible stable MI01; no family')
    save_sel(S); progress('decision_2f', S$decision)
    mi01 <- function(step) { st <- S[[step]]; if (identical(st$best, st$a$id)) st$a else st$b }
    # 目标家族
    if (S$decision %in% c('A', 'A1') && is.null(S$families$E1)) S <- run_family(S, 'E1', 'E1', mi01('F2'), conv)
    if (S$decision %in% c('A', 'B') && is.null(S$families$E1B)) S <- run_family(S, 'E1B', 'E1B', mi01('F1'), conv)
    # 诊断：主规格不存在时（C）只做 F5（以 F1 最佳或 Round2E E1B_01 为来源）与 F6 的 E0
    psp <- S[['primary']]; pref <- if (!is.null(psp)) (if (psp == 'E1') mi01('F2') else mi01('F1')) else NULL
    D <- S$diagnostics
    if (!is.null(pref) && is.null(D$N2)) {
      D$N2 <- list(ml = run_r2f(psp, 1L, 'N2ml', 'DIAG', conv = conv, estimator = 'ML', cluster = FALSE, source_dir = pref$dest),
                   mlr = run_r2f(psp, 1L, 'N2mlr', 'DIAG', conv = conv, estimator = 'MLR', cluster = FALSE, source_dir = pref$dest),
                   reference = pref$id)
      S$diagnostics <- D; save_sel(S)
    }
    if (is.null(D$F5)) {
      src <- if (!is.null(S$F1$best_dest)) S$F1$best_dest else e1b_2e
      D$F5 <- lapply(unlist(C2F$sy_fixed_grid), function(v) {
        sp <- sprintf('E1F%03d', round(v * 1000)); run_r2f(sp, 1L, 'F5', 'DIAG', conv = conv, source_dir = src) })
      S$diagnostics <- D; save_sel(S)
    }
    cc <- rj(file.path(ROOT, 'audit/CC_SAMPLE_2F.json'))
    if (is.null(D$F6)) {
      ccf <- file.path(ROOT, 'private/SD/CC_member_01.dat')
      D$F6 <- if (!isTRUE(cc$passed)) list(status = 'NOT_RUN_CC_SAMPLE_UNAVAILABLE') else list(
        E0 = run_r2f('E0', 1L, 'F6', 'DIAG', source_dir = e0_2e(1), source_data = ccf, data_tag = 'CC'),
        E1x = if (!is.null(pref)) run_r2f(psp, 1L, 'F6', 'DIAG', conv = conv, source_dir = pref$dest, source_data = ccf, data_tag = 'CC') else list(status = 'NOT_RUN_NO_PRIMARY'))
      S$diagnostics <- D; save_sel(S)
    }
    if (is.null(D$O1)) {
      tf <- file.path(ROOT, 'private/SD/Z0TOP99_member_01.dat')
      D$O1 <- if (!is.null(pref) && file.exists(tf)) run_r2f(psp, 1L, 'O1', 'DIAG', conv = conv, source_dir = pref$dest, source_data = tf, data_tag = 'TOP99')
              else list(status = 'NOT_RUN_NO_PRIMARY')
      S$diagnostics <- D; save_sel(S)
    }
    S$terminal <- list(status = 'FINISHED', utc = format(Sys.time(), tz = 'UTC', usetz = TRUE))
  }, error = function(e) {
    S$terminal <<- list(status = 'STOPPED_WITH_REASON', reason = conditionMessage(e), utc = format(Sys.time(), tz = 'UTC', usetz = TRUE))
  })
  save_sel(S); progress('queue_terminal', S$terminal$status)
  invisible(S)
}
if (sys.nframe() == 0L || identical(Sys.getenv('R2F_RUN_MAIN'), '1')) run_queue_2f()
