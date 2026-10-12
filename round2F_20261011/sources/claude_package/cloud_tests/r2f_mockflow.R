# 云端队列与汇总演练：用假 run_r2f（从 Round2E 已有输出复制关键路径与参数协方差、按情景给定状态）替代引擎，
# 检查决定 A/B/C、家族准入与修复、预算停止、诊断次数、汇总表。不调用 Mplus。
# 用法：Rscript r2f_mockflow.R <R2F_ROOT 模板> <工作目录>；环境变量同自检（R2F_R2E、R2F_R2D、R2F_PY）。
args <- commandArgs(TRUE); template <- normalizePath(args[1]); work <- args[2]
library(jsonlite); library(digest)
results <- list(); chk <- function(sc, name, ok, detail = '') results[[length(results) + 1L]] <<- data.frame(scenario = sc, test = name, result = if (isTRUE(ok)) 'PASS' else 'FAIL', detail = paste(detail, collapse = ' '))

scenario <- function(sc, rule, setup = NULL) {
  root <- file.path(work, sc); unlink(root, recursive = TRUE); dir.create(root, recursive = TRUE)
  for (d in c('code', 'contracts')) { dir.create(file.path(root, d)); file.copy(list.files(file.path(template, d), full.names = TRUE), file.path(root, d)) }
  for (d in c('models', 'runtime', 'audit', 'results', 'private/SD')) dir.create(file.path(root, d), recursive = TRUE, showWarnings = FALSE)
  Sys.setenv(R2F_ROOT = root)
  env <- new.env()
  local({
    source(file.path(root, 'code/r2f_queue.R'), local = globalenv())
    source(file.path(root, 'code/r2f_pool.R'), local = globalenv())
  })
  wj(list(passed = TRUE), file.path(ROOT, 'audit/P0_STATUS_2F.json')); wj(list(passed = TRUE, convergence_choice = 'tight'), file.path(ROOT, 'audit/SMOKE_2F.json'))
  wj(list(start_epoch = as.numeric(Sys.time())), file.path(ROOT, 'runtime/batch_window.json'))
  writeLines('x', file.path(ROOT, 'private/SD/CC_member_01.dat')); writeLines('x', file.path(ROOT, 'private/SD/Z0TOP99_member_01.dat'))
  wj(list(passed = TRUE, N = 2830, households = 2105), file.path(ROOT, 'audit/CC_SAMPLE_2F.json'))
  if (!is.null(setup)) setup()
  tmpl <- list(E1B = r2e_model(C2F$round2E_inputs$SD_E1B_01$id), E1 = r2e_model(C2F$round2E_inputs$SD_E1_q15$id), E0 = r2e_model(C2F$round2E_inputs$SD_E0$ids[[1]]))
  ledger <- list()
  # 假 run_r2f：与真实版本相同的准入与幂等；状态由情景规则决定
  assign('run_r2f', function(sp, k, attempt, category, ...) {
    a <- list(...); tag <- if (is.null(a$data_tag)) 'Z0' else a$data_tag
    id <- paste(c('CFPS', 'SD', sp, sprintf('%02d', k), if (tag != 'Z0') tag, attempt), collapse = '_')
    d <- file.path(ROOT, 'models', id); rf <- file.path(d, 'receipt.json'); if (file.exists(rf)) return(rj(rf))
    kind <- if (sp %in% c('E0', 'E0B')) 'linear' else 'lms_observed'
    adm <- admission(category, kind); if (adm != 'ADMIT') return(list(id = id, spec = sp, member = k, attempt = attempt, category = category, status = adm, usable = FALSE))
    o <- rule(sp, k, attempt, category, a)
    src <- tmpl[[if (sp == 'E0') 'E0' else if (sp == 'E1') 'E1' else 'E1B']]
    dir.create(d, recursive = TRUE)
    kp <- utils::read.csv(file.path(src, 'key_paths.csv')); kp$estimate <- kp$estimate + o$shift * kp$se
    utils::write.csv(kp, file.path(d, 'key_paths.csv'), row.names = FALSE)
    file.copy(file.path(src, 'parameter_covariance.csv'), file.path(d, 'parameter_covariance.csv'))
    r <- list(id = id, round = 'Round2F', z = 'SD', spec = sp, member = k, attempt = attempt, category = category, sample = 'CFPS', data_tag = tag,
              conv = if (is.null(a$conv)) 'default' else a$conv, estimator = if (is.null(a$estimator)) 'MLR' else a$estimator,
              cluster = if (is.null(a$cluster)) TRUE else a$cluster, points = if (kind == 'linear') 0L else 20L, dest = d,
              structural_signature = paste(sp, tag, a$estimator, a$cluster), status = o$status, usable = identical(o$status, 'USABLE'),
              seconds = o$seconds, LL = o$LL, sy = o$sy, scaling = 1.18, parameters = if (sp == 'E1') 135L else if (sp == 'E0') 134L else 134L,
              exact_LL_difference = o$exact, exact_LL_n_match = TRUE, convergence = list(iterations = 60L, last_abs_change = 9e-6))
    wj(r, rf)
    b <- budget_r2f(); b$rows[[length(b$rows) + 1L]] <- list(id = id, category = category, state = 'EXITED', seconds = o$seconds)
    b$calls <- length(b$rows); b$engine_seconds <- sum(vapply(b$rows, function(x) x$seconds, 0)); b$updated_utc <- format(Sys.time(), tz = 'UTC', usetz = TRUE)
    wj(b, file.path(ROOT, 'runtime/budget_status.json')); r
  }, envir = globalenv())
  S <- run_queue_2f(); build_results_2f()
  b <- rj(file.path(ROOT, 'runtime/budget_status.json'))
  cats <- table(vapply(b$rows, function(x) x$category, ''))
  list(S = S, cats = cats, fam = utils::read.csv(file.path(ROOT, 'results/FAMILY_STATUS_2F.csv')),
       pooled = utils::read.csv(file.path(ROOT, 'results/POOLED_KEY_PATHS_2F.csv')), slopes = utils::read.csv(file.path(ROOT, 'results/CONDITIONAL_SLOPES_2F.csv')),
       mult = utils::read.csv(file.path(ROOT, 'results/MULTIPLICITY_2F.csv')), sens = utils::read.csv(file.path(ROOT, 'results/SENSITIVITY_2F.csv')),
       se = utils::read.csv(file.path(ROOT, 'results/SE_DECOMPOSITION_2F.csv')), num = utils::read.csv(file.path(ROOT, 'results/NUMERIC_CHECKS_2F.csv')))
}
ok <- function(status = 'USABLE', LL = -27658.0, shift = 0, seconds = 120, sy = .01, exact = 1e-4) list(status = status, LL = LL, shift = shift, seconds = seconds, sy = sy, exact = exact)
cat_n <- function(x, c) if (c %in% names(x$cats)) as.integer(x$cats[[c]]) else 0L

# A：自由E1与E1B都稳定 → 自由E1为主、E1B为敏感性；诊断全做
A <- scenario('A', function(sp, k, attempt, category, a) ok(shift = .002 * k, LL = -27658 - .001 * (attempt == 'F1b')))
chk('A', 'decision', identical(A$S$decision, 'A'), A$S$decision)
chk('A', 'two_families_pooled', all(A$fam$status == 'POOLED') && nrow(A$fam) == 2L)
chk('A', 'call_counts', cat_n(A, 'NUMERIC') == 4L && cat_n(A, 'TARGET') == 18L && cat_n(A, 'DIAG') == 8L && cat_n(A, 'REPAIR') == 0L, paste(names(A$cats), A$cats))
chk('A', 'pooled_rows', nrow(A$pooled) == 14L && all(c('FMI', 'CI_width', 'MCSE_over_SE') %in% names(A$pooled)))
chk('A', 'slopes_rows', nrow(A$slopes) == 8L)
chk('A', 'primary_in_holm_only', is.finite(A$mult$p[1]) && all(is.na(A$mult$p[2:4])))
chk('A', 'diag_rows', all(c('CFPS_SD_E1_01_N2ml', 'CFPS_SD_E1_01_N2mlr', 'CFPS_SD_E1F020_01_F5', 'CFPS_SD_E1F034_01_F5', 'CFPS_SD_E1F080_01_F5',
                            'CFPS_SD_E0_01_CC_F6', 'CFPS_SD_E1_01_CC_F6', 'CFPS_SD_E1_01_TOP99_O1') %in% A$sens$id))
chk('A', 'se_decomposition', nrow(A$se) == 4L && any(grepl('naive LR', A$se$id)))
chk('A', 'F2a_override_recorded', identical(A$S$F2$a$id, 'CFPS_SD_E1_01_F2a'))

# B：自由E1 不合法（SY负）→ 只完成 E1B 强约束家族；E1B 不进入 Holm 家族
B <- scenario('B', function(sp, k, attempt, category, a) if (sp == 'E1') ok('INADMISSIBLE_SY_ONLY', sy = -.01) else ok(shift = .002 * k))
chk('B', 'decision', identical(B$S$decision, 'B'), B$S$decision)
chk('B', 'only_E1B_family', nrow(B$fam) == 1L && B$fam$family == 'E1B' && B$fam$role == 'STRONG_CONSTRAINT_SY0_ONLY_FAMILY' && B$fam$status == 'POOLED')
chk('B', 'E1B_not_in_holm', all(is.na(B$mult$p)))
chk('B', 'N2_on_E1B', 'CFPS_SD_E1B_01_N2ml' %in% B$sens$id)
chk('B', 'free_E1_kept_as_diagnostic', all(c('CFPS_SD_E1_01_F2a', 'CFPS_SD_E1_01_F2b') %in% B$sens$id))

# C：E1B 两起点不一致、自由E1 不合法 → 无家族；仍做 F5 与 F6 E0
C <- scenario('C', function(sp, k, attempt, category, a) if (sp == 'E1') ok('INADMISSIBLE_SY_ONLY', sy = -.01) else ok(LL = -27658 - .5 * (attempt == 'F1b')))
chk('C', 'decision', identical(C$S$decision, 'C'), C$S$decision)
chk('C', 'no_family', !('family' %in% names(C$fam)) || nrow(C$fam) == 0L)
chk('C', 'F5_and_F6_E0_only', cat_n(C, 'TARGET') == 0L && cat_n(C, 'DIAG') == 4L && all(c('CFPS_SD_E1F034_01_F5', 'CFPS_SD_E0_01_CC_F6') %in% C$sens$id), paste(names(C$cats), C$cats))
chk('C', 'start_check_not_replicated', identical(C$num$start_outcome[C$num$step == 'F1'], 'NOT_REPLICATED'))

# D：成员失败与修复——E1 第4份修复成功，第6份修复仍失败 → 家族停止、不删成员；E1B 家族照常
D <- scenario('D', function(sp, k, attempt, category, a) {
  if (sp == 'E1' && attempt == 'fam' && k %in% c(4, 6)) return(ok('INADMISSIBLE_SY_ONLY', sy = -.01))
  if (sp == 'E1' && attempt == 'famrep' && k == 6) return(ok('INADMISSIBLE_SY_ONLY', sy = -.01))
  ok(shift = .002 * k) })
fe1 <- D$fam[D$fam$family == 'E1', ]
chk('D', 'member_failed_stops_family', fe1$status == 'MEMBER_FAILED' && fe1$n_usable == 5L && fe1$repairs == 2L, paste(fe1$status, fe1$n_usable, fe1$repairs))
chk('D', 'no_pooling_of_incomplete', !any(D$pooled$family == 'E1'))
chk('D', 'E1B_family_still_pooled', any(D$fam$family == 'E1B' & D$fam$status == 'POOLED'))
chk('D', 'repair_count', cat_n(D, 'REPAIR') == 2L)

# E：预算——MI01 估计时长过长使家族预计成本超出剩余预算 → 不开始家族
E <- scenario('E', function(sp, k, attempt, category, a) ok(seconds = if (category == 'NUMERIC') 1500 else 100))
chk('E', 'family_not_started_budget', all(E$fam$status == 'NOT_ESTIMATED_WITHIN_BUDGET') && cat_n(E, 'TARGET') == 0L, paste(E$fam$status, collapse = ','))

# F：最佳解精确LL差 > 0.01 → 运行一次 q30，积分检查通过后仍判 F1 通过
F <- scenario('F', function(sp, k, attempt, category, a) ok(exact = if (attempt %in% c('F1a', 'F1b')) .05 else 1e-4, shift = .002 * k))
chk('F', 'q30_triggered', identical(F$S$F1$q30$id, 'CFPS_SD_E1B_01_F1_q30') && isTRUE(F$S$F1$passed) && cat_n(F, 'NUMERIC') == 5L)

# G：F1 与 F2 的最佳解精确LL差都 > 0.01 → 各运行一次 q30（NUMERIC 共 6 次，未触及类别上限），两步均通过
G <- scenario('G', function(sp, k, attempt, category, a) ok(exact = if (attempt %in% c('F1a', 'F1b', 'F2a', 'F2b')) .05 else 1e-4, shift = .002 * k))
chk('G', 'two_q30_within_cap', cat_n(G, 'NUMERIC') == 6L && isTRUE(G$S$F1$passed) && isTRUE(G$S$F2$passed) && identical(G$S$decision, 'A'), paste(names(G$cats), G$cats))

out <- do.call(rbind, results); dir.create(work, showWarnings = FALSE)
utils::write.csv(out, file.path(work, 'mockflow_results.csv'), row.names = FALSE)
cat(sprintf('%-3s %-34s %s %s\n', out$scenario, out$test, out$result, out$detail), sep = '')
cat('MOCKFLOW_2F', if (all(out$result == 'PASS')) 'PASSED' else 'FAILED', nrow(out), '\n')
