# 云端全流程演练（不调用Mplus、无CFPS数据）：合成私有成员 → 冻结合同 → 以模拟的 run_model 驱动全部阶段 → 合并 → 回传包。
# 模拟器只替换"调用Mplus并读回"这一步：照常登记调用（检验上限与预算）、照常生成输入（检验SVALUES拼接链），
# 回执状态与关键路径按情景设定；输出文件取 Round2D 真实输出的副本，使起点拼接走真实路径。
# 用法：Rscript r2e_mockflow.R <code目录> <Round2D包的models目录> <新的空工作目录> <情景: all_usable|boundary_mix|budget_stop|dryrun>
args <- commandArgs(TRUE); code <- normalizePath(args[1], winslash = '/'); r2dmodels <- normalizePath(args[2], winslash = '/'); work <- args[3]; scen <- args[4]
stopifnot(!dir.exists(work)); dir.create(work, recursive = TRUE); work <- normalizePath(work, winslash = '/')
R2D_F <- file.path(work, 'R2D'); R2E_F <- file.path(work, 'R2E'); dir.create(R2E_F); for (d in c('code', 'audit', 'runtime')) dir.create(file.path(R2D_F, d), recursive = TRUE)
file.copy(file.path(code, 'r2e_upstream_math.R'), file.path(R2D_F, 'code', '00_upstream_math.R'))
writeLines('{"terminal": true, "note": "mock"}', file.path(R2D_F, 'runtime', 'queue_terminal.json'))
for (z in c('SD', 'SEXGAP', 'OLDEST', 'SONGAP')) for (k in 1:2) { s <- file.path(r2dmodels, z, sprintf('D0_Z0_MI%02d', k), 'base'); if (!dir.exists(s)) next
  d <- file.path(R2D_F, 'models', z, sprintf('D0_Z0_MI%02d', k), 'base'); dir.create(d, recursive = TRUE)
  for (f in c('model.out', 'estimates.dat', 'tech3.dat', 'receipt.json')) file.copy(file.path(s, f), d) }
source(file.path(code, 'r2e_upstream_math.R')); suppressPackageStartupMessages({ library(jsonlite); library(digest) })
# ---------------- 合成私有成员（结构与Round2D相同；数值无意义）
set.seed(20261010); n <- 240; fid <- rep(1:120, each = 2)
zc <- list(samples = list(), z = list(SD = list(raw_prefix = 'wfd_s', orientation = 1, shape = 'free', ref_mean = 4.85780660460734, ref_sd = 10.2070583983168),
                                       SEXGAP = list(raw_prefix = 'wfd_d', orientation = -1, shape = 'linear', ref_mean = -0.95221936, ref_sd = 15.02112869),
                                       OLDEST = list(raw_prefix = 'wfd_d1', orientation = -1, shape = 'linear', ref_mean = -0.83039811, ref_sd = 14.56841288),
                                       SONGAP = list(raw_prefix = 'wfd_d4', orientation = -1, shape = 'linear', ref_mean = -0.86581374, ref_sd = 15.37117485)))
ctrl <- c(SD = 'c1-c24', SEXGAP = 'c1-c7 c10-c24', OLDEST = 'c1-c24', SONGAP = 'c1-c8 c10-c24')
for (z in names(ctrl)) {
  r0 <- zc$z[[z]]$orientation * (0 - zc$z[[z]]$ref_mean) / zc$z[[z]]$ref_sd
  z0 <- ifelse(runif(n) < .75, r0, r0 + rnorm(n, 0, 1.2)); hs <- character(0); dir.create(file.path(R2D_F, 'private', z), recursive = TRUE)
  for (k in 1:10) { d <- as.data.frame(matrix(round(rnorm(n * length(R2D_NAMES)), 4), n)); names(d) <- R2D_NAMES; d$fid <- fid
    d$z0 <- z0; d$z1 <- z0; for (v in c('c2', 'c3', 'ginc')) d[[v]] <- rbinom(n, 1, .4)
    f <- file.path(R2D_F, 'private', z, sprintf('Z0_member_%02d.dat', k)); write_dat(d, f); hs <- c(hs, digest(file = f, algo = 'sha256'))
    if (z == 'SD' && k == 1) { fcc <- file.path(R2D_F, 'private', 'SD', 'CC_member_01.dat'); write_dat(d[1:200, ], fcc) } }
  zc$samples[[paste0(z, '_Z0')]] <- list(N = n, households = 120, ctrl_term = ctrl[[z]], data_sha256 = as.list(hs))
}
zc$samples$SD_CC <- list(N = 200, households = 100, ctrl_term = 'c1-c24', data_sha256 = digest(file = fcc, algo = 'sha256'))
write_json(zc, file.path(R2D_F, 'audit', 'Z_CONTRACT.json'), auto_unbox = TRUE, pretty = TRUE, digits = NA)
# ---------------- 冻结合同（真实脚本，独立进程）
env <- c(R2E_ROOT = R2E_F, R2D_ROOT = R2D_F, R2E_RESOURCE_GATE = '0', R2E_DRYRUN = if (scen == 'dryrun') '1' else '0', R2E_RUN_H4 = '1')
out <- suppressWarnings(system2('Rscript', file.path(code, 'r2e_00_contract.R'), stdout = TRUE, stderr = TRUE, env = paste0(names(env), '=', env)))
if (!any(grepl('CONTRACT FROZEN', out))) { cat(out, sep = '\n'); stop('contract step failed') }
do.call(Sys.setenv, as.list(env)); Sys.setenv(R2E_CODE = code, R2E_SOURCE_ONLY = '1')
source(file.path(code, 'r2e_run.R'))
# ---------------- 模拟 run_model（dryrun 情景不替换，走真实 DRYRUN 分支）
OUT_E <- file.path(r2dmodels, 'SD', 'E1_SYNTHETIC_MI00', 'synthetic'); OUT_H <- file.path(r2dmodels, 'SD', 'H4_EDU_SYNTHETIC_MI00', 'synthetic'); OUT_D <- file.path(r2dmodels, 'OLDEST', 'D0_Z0_MI01', 'base')
# 模拟输出：取真实输出副本，但把 SVALUES 段换成本次输入的 MODEL 行，使下一步起点拼接面对结构一致的源（与真实流程相同）
mock_out <- function(src, dest) {
  L <- readLines(file.path(src, 'model.out'), warn = FALSE, encoding = 'latin1'); a <- grep('MODEL COMMAND WITH FINAL ESTIMATES USED AS STARTING VALUES', L)[1]
  k <- a + 1L; while (k <= length(L) && !(nchar(trimws(L[k])) && !grepl('^\\s', L[k]))) k <- k + 1L
  I <- readLines(file.path(dest, 'model.inp')); m <- I[(which(I == 'MODEL:') + 1):(which(I == 'OUTPUT:') - 1)]
  c(L[1:a], '', paste0('     ', m), '', L[k:length(L)])
}
status_of <- function(row) {
  z <- row$z; sp <- row$spec; k <- row$member; a <- row$attempt
  if (scen == 'boundary_mix') {
    if (z == 'SEXGAP' && sp == 'E1' && k == 4) return('BOUNDARY_SY')
    if (z == 'OLDEST' && sp == 'E0' && k == 6) return('BOUNDARY_SY')
    if (z == 'SD' && sp == 'E1' && k == 3) return('INADMISSIBLE')
    if (z == 'SONGAP' && sp == 'E1' && k == 5 && a == 'base') return('NOT_CONVERGED')
    if (sp == 'D1L') return('INADMISSIBLE')
  }
  'USABLE'
}
seconds_of <- function(row) { if (scen != 'budget_stop') return(5)
  if (row$spec %in% c('E0', 'E0B', 'D0B')) return(2); if (row$spec == 'D1L') return(10000); 850 }   # 850s：恰好只有一个E1家族在预算内，且潜路线小试仍有准入余量
mock_run_model <- function(row) {
  dest <- row$dest; rf <- file.path(dest, 'receipt.json'); if (file.exists(rf)) return(fromJSON(rf, simplifyVector = FALSE))
  stopifnot(hashf(file.path(dest, 'model.inp')) == row$input_sha256)
  bs <- register_call(row); st <- status_of(row); sec <- seconds_of(row)
  src <- if (grepl('^H4', row$spec)) OUT_H else if (grepl('^D', row$spec)) OUT_D else OUT_E
  if (st != 'TIMEOUT') writeLines(mock_out(src, dest), file.path(dest, 'model.out'), useBytes = TRUE)
  si <- spec_info_r2e(row$z, row$spec, ctrl_of(row$z), zshape_of(row$z)); lab <- si$key$label
  base <- c(bii = -.35, bis = .1, bss = -.25, bsyiy = .42, gi0 = .05, gs0 = .02, dc = if (row$z == 'SEXGAP') .12 else -.08, gii = .03, gis = .01, gss = .02,
            gizg = .01, gszg = 0, bxg = .03, dcg = if (row$z == 'SD') -.3 else 0)
  set.seed(row$member * 100 + match(row$z, R2E_ZS)); est <- unname(base[lab]) + rnorm(length(lab), 0, .01)
  se <- rep(.05, length(lab)); if (grepl('^H4', row$spec)) se[lab %in% c('dc', 'dcg')] <- .04
  if (st %in% c('USABLE', 'BOUNDARY_SY')) {
    utils::write.csv(data.frame(label = lab, parameter = seq_along(lab), row = si$key$row, column = si$key$column, estimate = est, se = se), file.path(dest, 'key_paths.csv'), row.names = FALSE)
    V <- diag(se^2, length(lab)); utils::write.csv(V, file.path(dest, 'parameter_covariance.csv'))
  }
  r <- c(row[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'batch', 'kind', 'sample', 'N', 'households', 'settings')],
         list(status = st, usable = st == 'USABLE', boundary = st == 'BOUNDARY_SY', seconds = sec, LL = -1000 - row$member / 10, parameters = 60L + length(lab),
              psi_SY = if (st == 'BOUNDARY_SY') -0.01 else NULL, psi_SY_se = if (st == 'BOUNDARY_SY') .1 else NULL, warm_from = row$warm_from))
  wj(r, rf); add_ledger(r, row$batch); r
}
`%||%` <- function(a, b) if (is.null(a)) b else a
if (scen != 'dryrun') run_model <- mock_run_model
run_all()
# ---------------- 检查
res <- list(); rec <- function(nm, ok, note = '') { res[[length(res) + 1]] <<- data.frame(scenario = scen, test = nm, passed = isTRUE(ok), note = substr(paste(note, collapse = ' '), 1, 250)); if (!isTRUE(ok)) message('FAIL ', nm, ' ', paste(note, collapse = ' ')) }
rd <- function(f) { p <- file.path(R2E_F, 'results', f); if (file.exists(p)) utils::read.csv(p, stringsAsFactors = FALSE) else data.frame() }
reg <- utils::read.csv(file.path(R2E_F, 'audit', 'CALL_REGISTER.csv'), stringsAsFactors = FALSE); ct <- contract()
caps_ok <- all(vapply(split(reg, reg$batch), function(b) nrow(b) <= ct$caps[[b$batch[1]]]$TOTAL && all(vapply(split(b, b$category), function(x) nrow(x) <= ct$caps[[b$batch[1]]][[x$category[1]]], TRUE)), TRUE))
rec('calls_within_caps', caps_ok, paste(names(table(paste(reg$batch, reg$category))), table(paste(reg$batch, reg$category)), collapse = '; '))
inps <- list.files(file.path(R2E_F, 'models'), pattern = '^model\\.inp$', recursive = TRUE, full.names = TRUE)
rec('inputs_width_and_no_bare_fix', all(vapply(inps, function(f) { L <- readLines(f); all(nchar(L) <= 90) && !any(grepl('^\\s*@', L)) }, TRUE)), paste(length(inps), 'inputs'))
rec('support_points_frozen', file.exists(file.path(R2E_F, 'contracts', 'SUPPORT_POINTS.csv')) && abs(subset(utils::read.csv(file.path(R2E_F, 'contracts', 'SUPPORT_POINTS.csv')), branch == 'SD' & point == 'raw_zero')$z + 0.4759262086) < 1e-8)
rec('first_calls_rotate_branches', identical(head(reg$z, 4), R2E_ZS) && all(head(reg$spec, 4) == 'E0'))
fam <- rd('FAMILY_STATUS_2E.csv'); cls <- function(z, sp) { x <- fam$class[fam$z == z & fam$spec == sp]; if (length(x)) x else 'ABSENT' }
pool <- rd('POOLED_KEY_PATHS_2E.csv'); mult <- rd('MULTIPLICITY_2E.csv'); h4d <- rd('H4_DECISION_2E.csv')
if (scen == 'all_usable') {
  rec('all_E_families_adopted', all(vapply(R2E_ZS, function(z) cls(z, 'E0') == 'ADOPT' && cls(z, 'E1') == 'ADOPT', TRUE)), paste(fam$z, fam$spec, fam$class))
  rec('no_boundary_family_run', !any(reg$category == 'BOUNDARY'))
  rec('pooled_dc_all_four', sum(pool$label == 'dc' & pool$spec == 'E1') == 4)
  rec('holm_family_4', all(mult$tests_available == 4) && nrow(mult) == 12)
  rec('h4_three_decisions', nrow(h4d) == 3 && all(h4d$class == 'ADOPT'), paste(h4d$G, h4d$decision))
  rec('h4_buffering_label', all(h4d$decision == 'H4.2b_BUFFERING'), paste(h4d$decision))
  rec('h4_calls_36_no_repair', sum(reg$batch == 'H4') == 36 && !any(reg$batch == 'H4' & reg$category == 'REPAIR'))
  rec('latent_probes_ran', all(c('D1L', 'D1B') %in% reg$spec))
  rec('sens_6_calls', sum(reg$category == 'SENS') == 6)
  cs <- rd('CONDITIONAL_SLOPES_2E.csv'); rec('conditional_slopes_at_support', nrow(cs) > 0 && all(c('raw_zero', 'observed_max') %in% cs$point))
  d1l <- file.path(R2E_F, 'models', 'OLDEST', 'D1L_Z0_MI01', 'from_r2d_d0', 'start_mapping.csv'); mp <- utils::read.csv(d1l)
  rec('D1L_warm_from_round2D_D0', sum(mp$action == 'added_new_statement') == 2 && sum(mp$action == 'copied_start') > 100)
  ex <- file.path(work, 'return.zip')
  o <- system2(Sys.which('python3'), c('-I', file.path(code, 'r2e_06_export.py'), R2E_F, ex, code), stdout = TRUE, stderr = TRUE)
  zl <- utils::unzip(ex, list = TRUE)$Name
  rec('export_excludes_private_data', file.exists(ex) && !any(grepl('private/|/data\\.dat$|W_member', zl)) && any(grepl('results/POOLED_KEY_PATHS_2E.csv', zl)), paste(length(zl), 'files'))
}
if (scen == 'boundary_mix') {
  rec('SEXGAP_E1_boundary_family', cls('SEXGAP', 'E1') == 'NEED_BOUNDARY' && cls('SEXGAP', 'E1B') == 'ADOPT', paste(cls('SEXGAP', 'E1'), cls('SEXGAP', 'E1B')))
  rec('OLDEST_E0_boundary_family', cls('OLDEST', 'E0') == 'NEED_BOUNDARY' && cls('OLDEST', 'E0B') == 'ADOPT')
  rec('SD_E1_not_poolable_H4_skipped', cls('SD', 'E1') == 'NOT_POOLABLE' && isTRUE(load_state('phase_H4')$skipped) && !any(reg$batch == 'H4'))
  rec('SONGAP_repair_member_used', cls('SONGAP', 'E1') == 'ADOPT' && any(reg$id == 'SONGAP_E1_Z0_5_repair'))
  rec('no_mixed_family_pool', !any(pool$spec == 'E1' & pool$z == 'SEXGAP') && any(pool$spec == 'E1B' & pool$z == 'SEXGAP'))
  m <- mult[mult$family == 'E1:dc', ]; rec('holm_n4_with_missing', all(m$tests_available == 3) && is.na(m$p[m$z == 'SD']))
  rec('boundary_inputs_have_sy0', all(vapply(grep('E1B_|E0B_', inps, value = TRUE), function(f) any(readLines(f) == 'sy@0;'), TRUE)))
  rec('latent_L1_inadmissible_recorded', identical(load_state('phase_C')$L1$status, 'INADMISSIBLE'))
}
if (scen == 'budget_stop') {
  A <- load_state('phase_A'); inb <- vapply(R2E_ZS, function(z) isTRUE(A$decisions[[z]]$within_budget_share), TRUE)
  rec('budget_projection_limits_E1', sum(inb) >= 1 && sum(inb) < 4, paste(R2E_ZS, inb))
  rec('not_estimated_within_budget_reported', sum(fam$class == 'NOT_ESTIMATED_WITHIN_BUDGET' & fam$spec == 'E1') == sum(!inb))
  rec('B1_stop_recorded', !is.null(load_state('B1_stopped')), load_state('B1_stopped')$reason)
  rec('H4_stop_recorded', !is.null(load_state('H4_stopped')), load_state('H4_stopped')$reason)
  rec('pool_ran_after_stop', file.exists(file.path(R2E_F, 'results', 'SUMMARY_2E.json')))
  rec('h4_completed_group_kept_after_stop', any(h4d$G == 'EDU' & h4d$class == 'ADOPT') && all(h4d$class[h4d$G != 'EDU'] == 'NOT_ESTIMATED_WITHIN_BUDGET'), paste(h4d$G, h4d$class))
  dg <- rd('DIAGNOSTICS_D0B_LATENT_2E.csv'); rec('latent_L1_kept_L2_marked', any(grepl('^D1L', dg$model) & dg$status == 'USABLE') && any(grepl('^D1B', dg$model) & dg$status == 'NOT_ESTIMATED_WITHIN_BUDGET'), paste(dg$model, dg$status))
}
if (scen == 'dryrun') {
  rec('dryrun_planned_status', all(rd('MODEL_EXECUTION_2E.csv')$status == 'DRYRUN_PLANNED'))
  rec('dryrun_phase_A_inputs', length(inps) >= 12, length(inps))
  rec('dryrun_no_repairs', !any(reg$category == 'REPAIR'))
}
out <- do.call(rbind, res); print(out, row.names = FALSE)
utils::write.csv(out, file.path(work, paste0('mockflow_', scen, '.csv')), row.names = FALSE)
cat(if (all(out$passed)) 'MOCKFLOW PASSED' else 'MOCKFLOW FAILED', scen, sum(out$passed), '/', nrow(out), '; calls', nrow(reg), '\n')
if (!all(out$passed)) quit(status = 1)
