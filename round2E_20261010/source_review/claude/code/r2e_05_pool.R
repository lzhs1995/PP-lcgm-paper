# Round2E 合并与汇总：只读回执与已保存参数/协方差；不调用Mplus。可单独重复运行。
# 用法：Rscript r2e_05_pool.R   （也由 r2e_run.R 最后自动调用）
if (!exists('phase_A')) { local({ a <- commandArgs(FALSE); f <- sub('^--file=', '', a[grep('^--file=', a)]); f <- f[basename(f) == 'r2e_05_pool.R']
  if (length(f)) Sys.setenv(R2E_CODE = dirname(normalizePath(f))) }); source(file.path(Sys.getenv('R2E_CODE'), 'r2e_queue.R')) }
RES <- file.path(R2E, 'results'); dir.create(RES, showWarnings = FALSE)
wcsv <- function(x, n) { if (is.null(x) || !nrow(x)) x <- data.frame(note = 'no rows'); utils::write.csv(x, file.path(RES, n), row.names = FALSE, na = ''); x }
nz <- function(x, d = NA) if (is.null(x) || !length(x)) d else x
ct <- contract(); NUM <- ct$numerics

# ---------------------------------------------------------------- 1. 执行总表（全部回执，含失败、超时、DRYRUN）
rcp <- list.files(file.path(R2E, 'models'), pattern = '^receipt\\.json$', recursive = TRUE, full.names = TRUE)
exe <- do.call(rbind, lapply(rcp, function(f) { r <- fromJSON(f, simplifyVector = FALSE)
  data.frame(id = nz(r$id), batch = nz(r$batch), z = nz(r$z), spec = nz(r$spec), sample = nz(r$sample), member = nz(r$member), attempt = nz(r$attempt),
             category = nz(r$category), kind = nz(r$kind), status = nz(r$status), usable = isTRUE(r$usable), boundary = isTRUE(r$boundary),
             points = nz(r$settings$points), processors = nz(r$settings$processors), seconds = nz(r$seconds), mplus_seconds = nz(r$mplus_seconds),
             iterations = nz(r$iterations), median_iteration_seconds = nz(r$median_iteration_seconds), slow_iteration_share = nz(r$share_time_in_slow_iterations),
             integration_dimensions = nz(r$integration_dimensions), LL = nz(r$LL), parameters = nz(r$parameters),
             psi_SY = nz(r$psi_SY), psi_SY_se = nz(r$psi_SY_se), psi_SY_z = nz(r$psi_SY_z), negative = paste(unlist(r$negative), collapse = ';'),
             warm_from = sub(paste0('^', R2E, '/?'), '', nz(r$warm_from, '')), failure_detail = nz(r$failure_detail, ''), printed_match = nz(r$printed_match),
             stringsAsFactors = FALSE) }))
wcsv(exe, 'MODEL_EXECUTION_2E.csv')
lg <- ledger(); bud <- if (nrow(lg)) stats::aggregate(cbind(calls, seconds) ~ batch + category, data = transform(lg, calls = 1, seconds = ifelse(is.na(seconds), 0, seconds)), FUN = sum) else data.frame()
wcsv(bud, 'BUDGET_2E.csv')

# ---------------------------------------------------------------- 2. 家族状态
A <- load_state('phase_A'); B <- load_state('phase_B'); B2 <- load_state('phase_B2'); H <- load_state('phase_H4')
# 批次因预算停止时，已完成的资源组仍按同一规则判定（部分状态逐组保存）；未完成的组记为 NOT_ESTIMATED_WITHIN_BUDGET
H4STOP <- load_state('H4_stopped'); if (is.null(H)) H <- load_state('phase_H4_partial')
fam <- list()
for (z in R2E_ZS) for (sp in c('E0', 'E1', 'E0B', 'E1B')) {
  if (grepl('B$', sp) && is.null(B2[[paste(z, sp)]])) next
  f <- if (is.null(A)) list(class = 'NOT_RUN', statuses = rep('NOT_RUN', 10), numeric_ok = NA) else family_class(z, sp)
  cls <- if (!is.null(B[[paste(z, sp)]]$class) && B[[paste(z, sp)]]$class == 'NOT_ESTIMATED_WITHIN_BUDGET') 'NOT_ESTIMATED_WITHIN_BUDGET' else f$class
  fam[[length(fam) + 1]] <- data.frame(z = z, spec = sp, class = cls, numeric_ok = nz(f$numeric_ok), n_usable = sum(f$statuses == 'USABLE'),
                                       n_boundary = sum(f$statuses == 'BOUNDARY_SY'), statuses = paste(f$statuses, collapse = ' '))
}
if (!is.null(H) && !isTRUE(H$skipped)) for (g in names(R2E_G)) if (!is.null(H[[g]]))
  fam[[length(fam) + 1]] <- data.frame(z = 'SD', spec = H[[g]]$spec, class = H[[g]]$class, numeric_ok = H[[g]]$numeric_ok,
                                       n_usable = sum(unlist(H[[g]]$statuses) == 'USABLE'), n_boundary = sum(unlist(H[[g]]$statuses) == 'BOUNDARY_SY'),
                                       statuses = paste(unlist(H[[g]]$statuses), collapse = ' '))
if (!is.null(H4STOP) && !isTRUE(H$skipped)) for (g in names(R2E_G)) if (is.null(H[[g]]))
  fam[[length(fam) + 1]] <- data.frame(z = 'SD', spec = paste0('H4_', g), class = 'NOT_ESTIMATED_WITHIN_BUDGET', numeric_ok = NA, n_usable = NA, n_boundary = NA, statuses = H4STOP$message)
fam <- wcsv(if (length(fam)) do.call(rbind, fam) else NULL, 'FAMILY_STATUS_2E.csv')

# ---------------------------------------------------------------- 3. Rubin 合并（只合并 ADOPT 家族；十份成员各取终态尝试）
member_QU <- function(a, labels) {
  kp <- utils::read.csv(file.path(a$dest, 'key_paths.csv')); V <- as.matrix(utils::read.csv(file.path(a$dest, 'parameter_covariance.csv'), row.names = 1))
  i <- match(labels, kp$label); stopifnot(!anyNA(i)); id <- kp$parameter[i]
  U <- unname(V[id, id, drop = FALSE]); dimnames(U) <- list(labels, labels)
  list(Q = kp$estimate[i], U = U, hh = a$receipt$households)
}
pool_family <- function(z, spec, ms) {
  si <- spec_info_r2e(z, spec, ctrl_of(z), zshape_of(z)); lab <- si$key$label
  qu <- lapply(ms, member_QU, labels = lab); Q <- do.call(rbind, lapply(qu, `[[`, 'Q')); colnames(Q) <- lab; U <- lapply(qu, `[[`, 'U')
  hh <- as.numeric(qu[[1]]$hh); pr <- rubin_pool(Q, U); br <- rubin_pool(Q, U, nu_com = hh - 1)
  tab <- data.frame(z = z, spec = spec, label = lab, pr$table, p_barnard_rubin = br$table$p, df_barnard_rubin = br$table$df,
                    mcse_flag = pr$table$MCSE_over_SE > NUM$mcse_over_se_flag, mde80 = mde80(pr$table$se), row.names = NULL)
  list(table = tab, Q = Q, U = U, T = pr$T, hh = hh)
}
POOL <- list(); ptab <- list()
for (i in seq_len(nrow(fam))) {
  x <- fam[i, ]; if (!identical(x$class, 'ADOPT')) next
  ms <- if (grepl('^H4', x$spec)) lapply(1:10, function(k) { if (k == 1) read_member('SD', x$spec, 1, 'q20') else { r <- read_member('SD', x$spec, k, 'repair'); if (is.null(r)) read_member('SD', x$spec, k, 'base') else r } })
        else lapply(1:10, function(k) member_final(x$z, x$spec, k))
  POOL[[paste(x$z, x$spec)]] <- pool_family(x$z, x$spec, ms); ptab[[length(ptab) + 1]] <- POOL[[paste(x$z, x$spec)]]$table
}
wcsv(if (length(ptab)) do.call(rbind, ptab) else NULL, 'POOLED_KEY_PATHS_2E.csv')

# ---------------------------------------------------------------- 4. 多重性（Holm，族大小固定为4；未得到合法家族的检验保持缺失，不缩小族）
pick <- function(z, base, lab) { sp <- adopted_E(z, base); if (is.null(sp)) return(NULL); t <- POOL[[paste(z, sp)]]$table; if (is.null(t)) NULL else cbind(spec = sp, t[t$label == lab, c('estimate', 'se', 'lower', 'upper', 'p')]) }
mult <- list()
for (fam_def in list(c('E1', 'dc'), c('E0', 'gi0'), c('E0', 'gs0'))) {
  rows <- lapply(R2E_ZS, function(z) { r <- pick(z, fam_def[1], fam_def[2]); if (is.null(r)) data.frame(z = z, family = paste(fam_def, collapse = ':'), spec = NA, estimate = NA, se = NA, lower = NA, upper = NA, p = NA) else data.frame(z = z, family = paste(fam_def, collapse = ':'), r) })
  r <- do.call(rbind, rows); ok <- is.finite(r$p); r$p_holm4 <- NA; if (any(ok)) r$p_holm4[ok] <- stats::p.adjust(r$p[ok], 'holm', n = 4)
  r$tests_available <- sum(ok); mult[[length(mult) + 1]] <- r
}
wcsv(do.call(rbind, mult), 'MULTIPLICITY_2E.csv')

# ---------------------------------------------------------------- 5. 条件斜率（真实支持点；呈现用，不改变连续交互）与 Johnson–Neyman 区域（限观测范围内）
cs <- list(); jn <- list()
for (z in R2E_ZS) { sp <- adopted_E(z, 'E1'); if (is.null(sp)) next
  P <- POOL[[paste(z, sp)]]; lab <- colnames(P$Q); sup <- ct$support[[z]]
  pts <- data.frame(point = c(unlist(sup$point), 'observed_min', 'observed_max'), z = c(unlist(sup$z), sup$min_z, sup$max_z))
  for (j in seq_len(nrow(pts))) { a <- setNames(rep(0, length(lab)), lab); a['bss'] <- 1; a['dc'] <- pts$z[j]
    cs[[length(cs) + 1]] <- data.frame(z_branch = z, spec = sp, quantity = 'slope SX->SY', point = pts$point[j], z = pts$z[j], pool_contrast(P$Q, P$U, a)) }
  r0 <- pts$z[pts$point == 'raw_zero']
  for (j in which(!pts$point %in% c('raw_zero'))) { a <- setNames(rep(0, length(lab)), lab); a['dc'] <- pts$z[j] - r0
    cs[[length(cs) + 1]] <- data.frame(z_branch = z, spec = sp, quantity = 'slope difference vs raw_zero', point = pts$point[j], z = pts$z[j], pool_contrast(P$Q, P$U, a)) }
  b <- mean(P$Q[, 'bss']); d <- mean(P$Q[, 'dc']); Tm <- P$T[c('bss', 'dc'), c('bss', 'dc')]; q <- 1.96^2
  co <- c(d^2 - q * Tm[2, 2], 2 * (b * d - q * Tm[1, 2]), b^2 - q * Tm[1, 1]); rt <- if (abs(co[1]) > 1e-12) Re(polyroot(rev(co))[abs(Im(polyroot(rev(co)))) < 1e-9]) else -co[3] / co[2]
  rt <- sort(rt[rt >= sup$min_z & rt <= sup$max_z])
  jn[[length(jn) + 1]] <- data.frame(z_branch = z, spec = sp, boundaries_within_observed_range = if (length(rt)) paste(round(rt, 4), collapse = ';') else 'none',
                                     min_z = sup$min_z, max_z = sup$max_z, note = 'pooled T, normal 1.96; descriptive only, not a test')
}
wcsv(if (length(cs)) do.call(rbind, cs) else NULL, 'CONDITIONAL_SLOPES_2E.csv'); wcsv(if (length(jn)) do.call(rbind, jn) else NULL, 'JOHNSON_NEYMAN_2E.csv')

# ---------------------------------------------------------------- 6. H4：δ0、δ1、δG（九项Bonferroni同时区间；δG Holm/3；成分判定表）
h4c <- list(); h4d <- list(); h4s <- list()
if (!is.null(H) && !isTRUE(H$skipped)) {
  crit_q <- 1 - .05 / (2 * 9)
  for (g in names(R2E_G)) { x <- H[[g]]
    if (is.null(x)) { if (!is.null(H4STOP)) h4d[[length(h4d) + 1]] <- data.frame(G = g, spec = NA, class = 'NOT_ESTIMATED_WITHIN_BUDGET', decision = 'NOT_ESTIMATED', text = paste('批次停止：', H4STOP$message), component = NA, p_deltaG = NA, p_deltaG_holm3 = NA); next }
    P <- POOL[[paste('SD', x$spec)]]
    if (is.null(P)) { h4d[[length(h4d) + 1]] <- data.frame(G = g, spec = x$spec, class = x$class, decision = 'NOT_ESTIMATED', text = '家族未采用，不作判定', component = NA, p_deltaG = NA, p_deltaG_holm3 = NA); next }
    lab <- colnames(P$Q); e <- function(...) { a <- setNames(rep(0, length(lab)), lab); v <- list(...); for (n in names(v)) a[n] <- v[[n]]; a }
    cons <- list(delta0 = e(dc = 1), delta1 = e(dc = 1, dcg = 1), deltaG = e(dcg = 1))
    for (cn in names(cons)) { t <- pool_contrast(P$Q, P$U, cons[[cn]]); cr <- stats::qt(crit_q, t$df)
      h4c[[length(h4c) + 1]] <- data.frame(G = g, spec = x$spec, contrast = cn, t, lo_bonf9 = t$estimate - cr * t$se, hi_bonf9 = t$estimate + cr * t$se) }
    sup <- ct$support$SD; for (gg in 0:1) for (j in seq_along(sup$z)) { a <- e(bss = 1, dc = sup$z[[j]], bxg = gg, dcg = gg * sup$z[[j]])
      h4s[[length(h4s) + 1]] <- data.frame(G = g, group = gg, point = sup$point[[j]], z = sup$z[[j]], pool_contrast(P$Q, P$U, a)) }
  }
  hc <- if (length(h4c)) do.call(rbind, h4c) else NULL
  if (!is.null(hc)) { dG <- hc$contrast == 'deltaG'; hc$p_holm3 <- NA; hc$p_holm3[dG] <- stats::p.adjust(hc$p[dG], 'holm', n = 3)
    for (g in unique(hc$G)) { s <- hc[hc$G == g, ]; iv <- function(cn) list(lo = s$lo_bonf9[s$contrast == cn], hi = s$hi_bonf9[s$contrast == cn])
      d <- h4_decide(iv('delta0'), iv('delta1'), iv('deltaG'))
      h4d[[length(h4d) + 1]] <- data.frame(G = g, spec = s$spec[1], class = 'ADOPT', decision = d$label, text = d$text, component = nz(d$component),
                                           p_deltaG = s$p[s$contrast == 'deltaG'], p_deltaG_holm3 = s$p_holm3[s$contrast == 'deltaG']) } }
  wcsv(hc, 'H4_CONTRASTS_2E.csv')
}
wcsv(if (length(h4d)) do.call(rbind, h4d) else data.frame(note = if (!is.null(H4STOP)) paste('H4 batch stopped:', H4STOP$message) else if (is.null(H)) 'H4 batch not run' else nz(H$reason, 'no H4 family')), 'H4_DECISION_2E.csv')
wcsv(if (length(h4s)) do.call(rbind, h4s) else NULL, 'H4_CONDITIONAL_SLOPES_2E.csv')

# ---------------------------------------------------------------- 7. 数值核查、诊断与敏感性（描述性，不合并、不检验）
nc <- list(); if (!is.null(A)) for (z in R2E_ZS) { d <- A$decisions[[z]]
  nc[[length(nc) + 1]] <- data.frame(z = z, spec = 'E1', e1_q15 = nz(d$e1_q15_status), adopted = nz(d$e1_adopted_attempt), adopted_status = nz(d$e1_adopted_status), points = nz(d$points),
    integration_passed = nz(d$integration$passed), integration_max_path_over_SE = nz(d$integration$max_path_over_SE), integration_max_SE_rel = nz(d$integration$max_SE_relative),
    start_outcome = nz(d$start$outcome), start_dLL = nz(d$start$alt_minus_adopted_LL), numeric_ok = nz(d$numeric_ok), run_members = nz(d$run_e1_members),
    within_budget = nz(d$within_budget_share), projected_e1_seconds = nz(d$projected_e1_seconds)) }
for (z in R2E_ZS) { s <- load_state(paste0('E1B_', z)); if (is.null(s)) next
  nc[[length(nc) + 1]] <- data.frame(z = z, spec = 'E1B', e1_q15 = NA, adopted = s$adopted_attempt, adopted_status = NA, points = NA, integration_passed = nz(s$integration$passed),
    integration_max_path_over_SE = nz(s$integration$max_path_over_SE), integration_max_SE_rel = nz(s$integration$max_SE_relative), start_outcome = nz(s$start$outcome),
    start_dLL = nz(s$start$alt_minus_adopted_LL), numeric_ok = s$numeric_ok, run_members = NA, within_budget = NA, projected_e1_seconds = NA) }
if (!is.null(H) && !isTRUE(H$skipped)) for (g in names(R2E_G)) { x <- H[[g]]; if (is.null(x)) next
  nc[[length(nc) + 1]] <- data.frame(z = 'SD', spec = x$spec, e1_q15 = NA, adopted = 'q20', adopted_status = x$statuses[[1]], points = 20, integration_passed = nz(x$integration$passed),
    integration_max_path_over_SE = nz(x$integration$max_path_over_SE), integration_max_SE_rel = nz(x$integration$max_SE_relative), start_outcome = nz(x$start$outcome),
    start_dLL = nz(x$start$alt_minus_adopted_LL), numeric_ok = x$numeric_ok, run_members = NA, within_budget = NA, projected_e1_seconds = NA) }
wcsv(if (length(nc)) do.call(rbind, nc) else NULL, 'NUMERIC_CHECKS_2E.csv')
dg <- list()
for (z in R2E_ZS) { a <- read_member(z, 'D0B', 1, 'base'); r0 <- file.path(R2D, 'models', z, 'D0_Z0_MI01', 'base', 'receipt.json')
  ll0 <- if (file.exists(r0)) nz(fromJSON(r0)$LL) else NA
  dg[[length(dg) + 1]] <- data.frame(z = z, model = 'D0B (Round2D D0 + sy@0), MI01', status = nz(a$receipt$status, 'NOT_RUN'), LL = nz(a$receipt$LL), round2D_D0_LL = ll0,
    minus2_dLL_free_vs_boundary = if (is.null(a)) NA else -2 * (as.numeric(nz(a$receipt$LL)) - as.numeric(ll0)), seconds = nz(a$receipt$seconds),
    note = 'descriptive; boundary LR is a chi-bar-square mixture and MLR needs scaling: not a test') }
C <- load_state('phase_C'); if (is.null(C)) C <- load_state('phase_C_partial')
for (nm in c('L1', 'L2')) if (!is.null(C[[nm]])) dg[[length(dg) + 1]] <- data.frame(z = 'OLDEST', model = c(L1 = 'D1L: Round2D D1, full legal D0 start', L2 = 'D1B: D1 + sy@0, start from D0B')[[nm]],
  status = nz(C[[nm]]$status), LL = nz(C[[nm]]$LL), round2D_D0_LL = NA, minus2_dLL_free_vs_boundary = NA, seconds = nz(C[[nm]]$seconds),
  note = paste('iterations', nz(C[[nm]]$iterations), 'median s/iter', nz(C[[nm]]$median_iteration_seconds), 'negative', paste(unlist(C[[nm]]$negative), collapse = ';')))
B1STOP <- load_state('B1_stopped')
if (!is.null(B1STOP) && !isTRUE(C$skipped)) for (nm in c('L1', 'L2')) if (is.null(C[[nm]])) dg[[length(dg) + 1]] <- data.frame(z = 'OLDEST', model = c(L1 = 'D1L: Round2D D1, full legal D0 start', L2 = 'D1B: D1 + sy@0, start from D0B')[[nm]],
  status = 'NOT_ESTIMATED_WITHIN_BUDGET', LL = NA, round2D_D0_LL = NA, minus2_dLL_free_vs_boundary = NA, seconds = NA, note = B1STOP$message)
if (isTRUE(C$skipped)) dg[[length(dg) + 1]] <- data.frame(z = 'OLDEST', model = 'latent probes', status = 'SKIPPED', LL = NA, round2D_D0_LL = NA, minus2_dLL_free_vs_boundary = NA, seconds = NA, note = C$reason)
wcsv(do.call(rbind, dg), 'DIAGNOSTICS_D0B_LATENT_2E.csv')
sens <- list(); keyrow <- function(a, lab) { if (is.null(a) || is.null(a$key)) return(c(NA, NA)); k <- a$key[a$key$label == lab, ]; if (nrow(k)) c(k$estimate, k$se) else c(NA, NA) }
for (z in R2E_ZS) { sp <- adopted_E(z, 'E1'); if (is.null(sp)) next; ref <- member_final(z, sp, 1); w <- read_member(z, sp, 1, 'winsor', 'W')
  for (lab in c('dc', 'bss', 'gs0')) { r <- keyrow(ref, lab); s <- keyrow(w, lab)
    sens[[length(sens) + 1]] <- data.frame(z = z, check = 'tail: Z0 winsorized P1/P99, MI01', spec = sp, label = lab, status = nz(w$receipt$status, 'NOT_RUN'),
      reference = r[1], reference_se = r[2], sensitivity = s[1], sensitivity_se = s[2], difference_over_reference_se = (s[1] - r[1]) / r[2]) } }
for (base in c('E0', 'E1')) { sp <- adopted_E('SD', base); if (is.null(sp)) next; ref <- member_final('SD', sp, 1); cc <- read_member('SD', sp, 1, 'cc', 'CC')
  for (lab in if (base == 'E1') c('dc', 'bss') else c('gi0', 'gs0', 'bss')) { r <- keyrow(ref, lab); s <- keyrow(cc, lab)
    sens[[length(sens) + 1]] <- data.frame(z = 'SD', check = 'complete cases (diagnostic, not MI-congeniality proof)', spec = sp, label = lab, status = nz(cc$receipt$status, 'NOT_RUN'),
      reference = r[1], reference_se = r[2], sensitivity = s[1], sensitivity_se = s[2], difference_over_reference_se = (s[1] - r[1]) / r[2]) } }
wcsv(if (length(sens)) do.call(rbind, sens) else NULL, 'SENSITIVITY_TAIL_CC_2E.csv')
rel <- file.path(R2E, 'contracts', 'Z0_RELIABILITY_FROM_ROUND2D_D0.csv'); if (file.exists(rel)) file.copy(rel, file.path(RES, 'Z0_RELIABILITY_CONTEXT_2E.csv'), overwrite = TRUE)

# ---------------------------------------------------------------- 8. 摘要
stops <- lapply(c('B1', 'H4'), function(b) load_state(paste0(b, '_stopped'))); names(stops) <- c('B1', 'H4')
summ <- list(round = 'Round2E', generated_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE), dryrun = DRYRUN,
             calls = nrow(exe), calls_by_status = as.list(table(exe$status)), engine_seconds_by_batch = if (nrow(lg)) as.list(tapply(lg$seconds, lg$batch, sum, na.rm = TRUE)) else list(),
             processors = load_state('processors_decision'), families = split(fam[, c('spec', 'class', 'n_usable', 'n_boundary')], fam$z),
             batch_stops = stops, phase_states = lapply(setNames(nm = c('phase_A', 'phase_B', 'phase_B2', 'phase_D', 'phase_C', 'phase_H4')), function(n) !is.null(load_state(n))),
             reading_rules = c('Only ADOPT families are pooled; NOT_POOLABLE / INCOMPLETE / NOT_ESTIMATED_WITHIN_BUDGET are execution results, not null findings.',
                               'Z0 is the observed 2012 configuration; moderation by Z0 is not moderation by latent IZ (see Z0_RELIABILITY_CONTEXT_2E.csv).',
                               'Free (E1) and boundary (E1B) members are never mixed; a family is adopted in one specification only.',
                               'H4 decisions use nine Bonferroni simultaneous intervals and the component-specific table; the sign of deltaG alone is never mapped to H4.2a/b.'))
wj(summ, file.path(RES, 'SUMMARY_2E.json'))
cat('POOL DONE:', nrow(exe), 'receipts;', sum(fam$class == 'ADOPT'), 'adopted families\n')
