# Round2E 自检（不调用Mplus、不读CFPS个人数据、不写Round2D目录）：
# 用 Round2D 已保存的真实输出检验 读回/门槛/边界分类/SVALUES拼接/输入生成/判定表/合并对比。
# 用法：Rscript r2e_selftest.R <Round2D根目录> <新的空工作目录>
args <- commandArgs(TRUE); r2d <- normalizePath(args[1], winslash = '/'); work <- args[2]
stopifnot(dir.exists(file.path(r2d, 'models')), !dir.exists(work)); dir.create(work, recursive = TRUE); work <- normalizePath(work, winslash = '/')
code <- local({ a <- commandArgs(FALSE); f <- sub('^--file=', '', a[grep('^--file=', a)]); dirname(normalizePath(f)) })
Sys.setenv(R2E_ROOT = work, R2D_ROOT = r2d, R2E_CODE = code, R2E_DRYRUN = '1', R2E_RESOURCE_GATE = '0')
source(file.path(code, 'r2e_engine.R'))
res <- list(); rec <- function(nm, ok, note = '') { res[[length(res) + 1]] <<- data.frame(test = nm, passed = isTRUE(ok), note = substr(paste(note, collapse = ' '), 1, 300)); if (!isTRUE(ok)) message('FAIL ', nm, ' ', paste(note, collapse = ' ')) }
# 最小合同（只供读回使用；支持点为示意值，不来自CFPS）
sp <- list(point = list('raw_zero', 'median_above_zero', 'P90'), z = list(-0.4759262086, 0.9, 1.6), min_z = -0.4759262086, max_z = 8.761, N = 3274)
wj(list(round = 'SELFTEST', numerics = list(start_LL = .01, start_path_abs = .001, start_path_se = .01, integration_path_se = .05, se_rel = .05, mcse_over_se_flag = .05, processors_candidate = 4),
        support = list(SD = sp, SEXGAP = sp, OLDEST = sp, SONGAP = sp), per_call_seconds = list(linear = 600, lms_observed = 1800, lms_latent = 1200),
        caps = list(SELFTEST = list(TEST = 100, TOTAL = 100)), budgets = list(SELFTEST = list(engine_hours = 1, wall_hours = 1))), file.path(work, 'contracts', 'RUN_CONTRACT_2E.json'))

# ---------------- 1. 上游数学与Round2D逐字节一致
rec('upstream_math_identical_to_round2D', hashf(file.path(code, 'r2e_upstream_math.R')) == hashf(file.path(r2d, 'code', '00_upstream_math.R')))

# ---------------- 2. 对Round2D真实D0/D1输出复跑读回（复制到工作目录，规格D0=自由SY线性、D1L=自由SY潜交互）
rb <- function(z, spec, k, att, src_spec) {
  src <- file.path(r2d, 'models', z, sprintf('%s_Z0_MI%02d', src_spec, k), att); if (!dir.exists(src)) return(NULL)
  dest <- file.path(work, 'readback', z, paste(src_spec, k, att, sep = '_')); dir.create(dest, recursive = TRUE)
  for (f in c('model.inp', 'model.out', 'estimates.dat', 'tech3.dat', 'mplus_console.log', 'receipt.json')) if (file.exists(file.path(src, f))) file.copy(file.path(src, f), dest)
  old <- fromJSON(file.path(src, 'receipt.json'))
  row <- list(id = paste(z, spec, k, att, sep = '_'), z = z, spec = spec, member = k, attempt = att, category = 'TEST', batch = 'SELFTEST',
              kind = spec_info_r2e(z, spec, ctrl_of(z), zshape_of(z))$kind, sample = 'Z0', N = old$N, households = old$households, settings = list(), dest = dest)
  r <- readback_model(row, NA_real_, NA_integer_, identical(old$status, 'TIMEOUT'))
  data.frame(z = z, round2D = paste(src_spec, k, att), round2D_status = old$status, r2e_status = r$status, psi_SY = nz0(r$psi_SY), psi_SY_z = nz0(r$psi_SY_z),
             negative = paste(unlist(r$negative), collapse = ';'))
}
nz0 <- function(x) if (is.null(x) || !length(x)) NA else x
tab <- list()
for (k in 1:6) for (att in c('base', 'repair_start')) tab[[length(tab) + 1]] <- rb('OLDEST', 'D0', k, att, 'D0')
for (z in c('SD', 'SEXGAP', 'SONGAP')) for (att in c('base', 'repair_start')) tab[[length(tab) + 1]] <- rb(z, 'D0', 1, att, 'D0')
for (z in R2E_ZS) for (att in c('base', 'repair_start', 'repair_em')) tab[[length(tab) + 1]] <- rb(z, 'D1L', 1, att, 'D1')
tab <- do.call(rbind, tab); print(tab, row.names = FALSE); utils::write.csv(tab, file.path(work, 'selftest_round2D_readback.csv'), row.names = FALSE)
d0 <- tab[grepl('^D0', tab$round2D), ]; d1 <- tab[grepl('^D1', tab$round2D), ]
rec('usable_set_equals_round2D', identical(d0$round2D_status == 'USABLE', d0$r2e_status == 'USABLE') && identical(d1$round2D_status == 'USABLE', d1$r2e_status == 'USABLE'),
    paste(tab$round2D, tab$round2D_status, tab$r2e_status, collapse = '; '))
rec('OLDEST_MI06_is_boundary_SY', all(d0$r2e_status[d0$z == 'OLDEST' & grepl(' 6 ', d0$round2D)] == 'BOUNDARY_SY'))
rec('SD_SONGAP_D0_boundary_SY', all(d0$r2e_status[d0$z %in% c('SD', 'SONGAP')] == 'BOUNDARY_SY'))
rec('SEXGAP_D0_not_boundary', all(d0$r2e_status[d0$z == 'SEXGAP'] == 'INADMISSIBLE'))
rec('D1_none_usable_or_boundary', !any(d1$r2e_status %in% c('USABLE', 'BOUNDARY_SY')), paste(d1$round2D, d1$r2e_status))

# ---------------- 3. 合成E1与H4输出（Round2D接口测试的真实Mplus输出）读回
syn <- function(dirname, spec) {
  src <- file.path(r2d, 'models', 'SD', dirname, 'synthetic'); dest <- file.path(work, 'readback', 'SD', dirname); dir.create(dest, recursive = TRUE)
  for (f in c('model.inp', 'model.out', 'estimates.dat', 'tech3.dat')) file.copy(file.path(src, f), dest)
  si <- spec_info_r2e('SD', spec, 'c1-c3'); m <- read_mplus_raw(dest); gt <- gate_r2e(m, si, support_z('SD')); kp <- key_paths_r2e(m, si$key)
  list(gate = gt, key = kp, class = classify_member(m, si, gt, support_z('SD'))$status, m = m, dest = dest)
}
e1 <- syn('E1_SYNTHETIC_MI00', 'E1'); h4 <- syn('H4_EDU_SYNTHETIC_MI00', 'H4_EDU')
rec('synthetic_E1_usable_with_dc', e1$class == 'USABLE' && 'dc' %in% e1$key$label && abs(e1$key$estimate[e1$key$label == 'dc'] - 0.13131) < 1e-4)
rec('synthetic_H4_usable_with_dcg', h4$class == 'USABLE' && all(c('dc', 'bxg', 'dcg') %in% h4$key$label) && abs(h4$key$estimate[h4$key$label == 'dcg'] - 0.098278954) < 1e-6)
rec('E1_geometry_at_support_points', isTRUE(e1$gate$geometry$passed) && length(grep('^COND_', names(e1$gate$geometry$checks))) == length(support_z('SD')))
sx <- svalues_splice(file.path(e1$dest, 'model.out'), character(0), character(0))
rec('splice_check_flags_structure_mismatch', splice_check(sx$model, spec_info_r2e('SD', 'E1', 'c1-c3'))$ok && !splice_check(sx$model, spec_info_r2e('SD', 'E1', 'c1-c24'))$ok &&
    !splice_check(sx$model, spec_info_r2e('SD', 'D1L', 'c1-c3'))$ok)

# ---------------- 4. SVALUES 跨规格拼接
XW_E <- c('sxz | sx XWITH z0;', 'sy ON sxz*0 (dc);'); XW_D <- c('sxiz | sx XWITH iz;', 'sy ON sxiz*0 (dc);')
o_old <- file.path(work, 'readback', 'OLDEST', 'D0_1_base', 'model.out')
s1 <- svalues_splice(o_old, XW_D, character(0))
rec('D0_to_D1L_splice', !any(grepl('^@', s1$model)) && all(XW_D %in% s1$model) && !length(svalues_coverage(o_old, s1$model)) && sum(s1$log$action == 'added_new_statement') == 2)
o_sd <- file.path(work, 'readback', 'SD', 'D0_1_base', 'model.out')
s2 <- svalues_splice(o_sd, character(0), 'SY')
rec('D0_to_D0B_drops_negative_SY', 'sy@0;' %in% s2$model && !any(grepl('^sy\\*', s2$model)) && any(s2$log$action == 'dropped_for_fixed_zero'))
o_sx <- file.path(work, 'readback', 'SEXGAP', 'D0_1_base', 'model.out')
s3 <- svalues_splice(o_sx, XW_D, character(0))
rec('negative_SX_start_sanitized', any(grepl('negative_variance_start_replaced', s3$log$action)) && 'sx*0.01;' %in% s3$model && !any(grepl('^s[xy]\\*-', s3$model)))
o_e1 <- file.path(e1$dest, 'model.out')
s4 <- svalues_splice(o_e1, character(0), 'SY')
rec('E1_to_E1B', 'sy@0;' %in% s4$model && !any(grepl('^sy\\*', s4$model)) && 'sxz | sx XWITH z0;' %in% s4$model)
h4add <- c('ix sx iy sy ON ginc*0;', 'ix sx ON zg*0;', 'iy ON zg*0 (gizg);', 'sy ON zg*0 (gszg);', 'sxg | sx XWITH ginc;', 'sxzg | sx XWITH zg;', 'sy ON sxg*0 (bxg);', 'sy ON sxzg*0 (dcg);')
s5 <- svalues_splice(o_e1, c(XW_E, h4add), character(0))
rec('E1_to_H4_INC_with_dedupe', all(h4add %in% s5$model) && sum(s5$log$action == 'not_added_statement_already_in_source') == 2 && sum(grepl('^sy ON sxz\\*', s5$model)) == 1 && !any(grepl('^@', s5$model)))
rec('stmt_key', identical(stmt_key(c('sy ON sxz*0.13131 (dc);', 'sy@0;', 'sy*-0.132;', 'sxz | sx XWITH z0;')), c('sy ON sxz', 'sy', 'sy', 'sxz | sx XWITH z0')))

# ---------------- 5. 输入生成（DRYRUN，合成数据，不调用Mplus）
set.seed(7); n <- 300; dat <- as.data.frame(matrix(round(rnorm(n * length(R2D_NAMES)), 4), n)); names(dat) <- R2D_NAMES
dat$fid <- rep(1:150, each = 2); for (v in c('c2', 'c3', 'ginc')) dat[[v]] <- rbinom(n, 1, .4); dat$z1 <- dat$z0
syn_f <- file.path(work, 'synthetic_member.dat'); write_dat(dat, syn_f)
mk <- function(z, spec, att, warm = NULL, points = 15L, processors = 1L) {
  row <- prepare_model(z, spec, 1, att, 'TEST', 'SELFTEST', 'Z0', points, processors, 26101001L, warm, syn_f); paste(readLines(file.path(row$dest, 'model.inp')), collapse = '\n') }
txt <- list(
  E0 = mk('SD', 'E0', 't'), E1 = mk('SD', 'E1', 't', list(from = e1$dest)), E1B = mk('SD', 'E1B', 't', list(from = e1$dest), 20L, 4L),
  E0B = mk('SEXGAP', 'E0B', 't'), H4_INC = mk('SD', 'H4_INC', 't', list(from = e1$dest, add = h4add)),
  H4B_EDU = mk('SD', 'H4B_EDU', 't', list(from = file.path(e1$dest), add = c('ix sx ON zg*0;', 'iy ON zg*0 (gizg);', 'sy ON zg*0 (gszg);', 'sxg | sx XWITH c2;', 'sxzg | sx XWITH zg;', 'sy ON sxg*0 (bxg);', 'sy ON sxzg*0 (dcg);'))),
  D0B = mk('SD', 'D0B', 't', list(from = dirname(o_sd))), D1L = mk('OLDEST', 'D1L', 't', list(from = dirname(o_old), add = XW_D)),
  D1B = mk('SEXGAP', 'D1B', 't', list(from = dirname(o_sx), add = XW_D)))
has <- function(s, ...) all(vapply(c(...), function(p) grepl(p, s, fixed = TRUE), TRUE))
rec('E0_linear_no_xwith', has(txt$E0, 'TYPE=COMPLEX;', 'ix sx ON z0;', 'iy ON z0 (gi0);', 'x1 y1 ON z0;') && !grepl('XWITH', txt$E0))
rec('E1_lms_1dim_svalues', has(txt$E1, 'TYPE=COMPLEX RANDOM;', 'INTEGRATION=15;', 'sxz | sx XWITH z0;', '(dc)') && !grepl('sxiz', txt$E1))
rec('E1B_boundary_q20_p4', has(txt$E1B, 'sy@0;', 'INTEGRATION=20;', 'PROCESSORS=4;'))
rec('E0B_default_starts_has_sy0', has(txt$E0B, 'sy@0;', 'c1-c7 c10-c24'))
rec('H4_INC_define_usev_main', has(txt$H4_INC, 'DEFINE:', 'zg=z0*ginc;', 'sxzg | sx XWITH zg;', '(dcg)', 'ix sx iy sy ON ginc') &&
      grepl('USEVARIABLES=[^;]*ginc[^;]*zg;', gsub('\n', ' ', txt$H4_INC)))
rec('H4B_EDU_control_column_and_sy0', has(txt$H4B_EDU, 'zg=z0*c2;', 'sxg | sx XWITH c2;', 'sy@0;') && !grepl('ix sx iy sy ON c2', txt$H4B_EDU, fixed = TRUE))
rec('D0B_from_round2D_D0', has(txt$D0B, 'sy@0;', 'iz sz |') && !grepl('\nsy\\*', txt$D0B))
rec('D1L_from_legal_D0_full_starts', has(txt$D1L, 'sxiz | sx XWITH iz;', 'TYPE=COMPLEX RANDOM;') && !grepl('sy@0', txt$D1L, fixed = TRUE))
rec('D1B_sanitized_and_sy0', has(txt$D1B, 'sy@0;', 'sx*0.01;', 'sxiz | sx XWITH iz;'))
rec('all_inputs_width_90', all(vapply(txt, function(s) all(nchar(strsplit(s, '\n')[[1]]) <= 90), TRUE)))
mp <- utils::read.csv(file.path(model_dir('SEXGAP', 'D1B', 1, 't'), 'start_mapping.csv'))
rec('start_mapping_written', any(grepl('negative_variance', mp$action)) && any(mp$action == 'dropped_for_fixed_zero'))

# ---------------- 6. 边界分类：同一解若 SY 的 z ≤ −1.96 则不合格
m6 <- read_mplus_raw(dirname(o_sd)); si6 <- spec_info_r2e('SD', 'D0', 'c1-c24', 'free'); g6 <- gate_r2e(m6, si6)
rec('classify_SD_D0_boundary', classify_member(m6, si6, g6)$status == 'BOUNDARY_SY')
m6b <- m6; j <- m6b$par$matrix == 'psi' & m6b$par$row == 'SY' & m6b$par$column == 'SY'; m6b$par$se[j] <- 0.05
rec('classify_large_negative_inadmissible', classify_member(m6b, si6, g6)$status == 'INADMISSIBLE')

# ---------------- 7. 支持点（合成，模拟SD：75.6%在原始零点）
set.seed(3); zz <- c(rep(-0.4759262086, 756), -0.4759262086 + abs(rnorm(244, 1.2, .8)))
spt <- support_points(zz, -0.4759262086)
rec('support_points_rules', spt$point[1] == 'raw_zero' && 'median_above_zero' %in% spt$point && !'median_below_zero' %in% spt$point &&
      !'P10' %in% spt$point && 'P90' %in% spt$point && all(spt$z >= min(zz)), paste(spt$point, round(spt$z, 3)))
rec('winsorize_bounds', all(range(winsorize(zz)) == stats::quantile(zz, c(.01, .99), type = 7, names = FALSE)))

# ---------------- 8. H4 方向判定（复核意见的反例与对称情形）
iv <- function(e, h) list(lo = e - h, hi = e + h)
rec('h4_counterexample_is_buffering_not_weakening', h4_decide(iv(-.2, .1), iv(-.6, .1), iv(-.4, .1))$label == 'H4.2b_BUFFERING')
rec('h4_weakening_stronger', h4_decide(iv(.2, .1), iv(.6, .1), iv(.4, .1))$label == 'H4.2b_WEAKENING')
rec('h4_2a_mirror', h4_decide(iv(.6, .1), iv(.2, .1), iv(-.4, .1))$label == 'H4.2a_WEAKENING')
rec('h4_crossover', h4_decide(iv(.3, .1), iv(-.3, .1), iv(-.6, .1))$label == 'CROSSOVER')
rec('h4_deltaG_undetermined', h4_decide(iv(-.4, .1), iv(-.45, .1), iv(-.05, .2))$label == 'DIFFERENCE_UNDETERMINED')
rec('h4_d0_zero_d1_neg', h4_decide(iv(0, .1), iv(-.4, .1), iv(-.4, .1))$label == 'H4.2b_BUFFERING')
rec('h4_no_component', h4_decide(iv(-.1, .2), iv(.1, .2), iv(.2, .15))$label == 'DIFFERENCE_WITHOUT_COMPONENT')

# ---------------- 9. 数值比较、起点结果类别、预算注水、对比合并、Holm
mkm <- function(est, se, LL, id) list(key = data.frame(label = c('bss', 'dc'), estimate = est, se = se), receipt = list(LL = LL, id = id))
a <- mkm(c(-.3, .1), c(.2, .05), -1000, 'a')
rec('compare_start_agree', isTRUE(compare_numeric(a, mkm(c(-.3005, .1004), c(.2, .05), -1000.005, 'b'), 'start')$passed))
rec('compare_integration_fail', !isTRUE(compare_numeric(a, mkm(c(-.3, .11), c(.2, .05), -1000, 'b'), 'integration')$passed))
Sys.setenv(R2E_CODE = code); source(file.path(code, 'r2e_queue.R'))
rec('start_outcome_beaten', start_outcome(a, mkm(c(-.2, .2), c(.2, .05), -990, 'b'))$outcome == 'BEATEN')
rec('start_outcome_alt_lower', start_outcome(a, mkm(c(-.2, .2), c(.2, .05), -1010, 'b'))$outcome == 'ALT_LOWER')
rec('start_outcome_ridge', start_outcome(a, mkm(c(-.2, .2), c(.2, .05), -1000.001, 'b'))$outcome == 'RIDGE')
rec('start_outcome_alt_failed', start_outcome(a, NULL)$outcome == 'ALT_FAILED')
wf <- waterfill(c(SD = 100, SEXGAP = 500, OLDEST = 50, SONGAP = 2000), 1000)
rec('waterfill_redistributes', identical(unname(wf), c(TRUE, TRUE, TRUE, FALSE)))
set.seed(11); Q <- matrix(rnorm(20, c(-.3, .1), .02), 10, 2, byrow = TRUE); U <- replicate(10, matrix(c(.04, -.002, -.002, .0025), 2), simplify = FALSE)
pc <- pool_contrast(Q, U, c(1, .9)); T <- rubin_pool(Q, U)$T
rec('pool_contrast_equals_quadratic_form', abs(pc$se - sqrt(drop(t(c(1, .9)) %*% T %*% c(1, .9)))) < 1e-12)
rec('holm_fixed_family_4', all(abs(stats::p.adjust(c(.01, .04), 'holm', n = 4) - c(.04, .12)) < 1e-12))

out <- do.call(rbind, res); print(out, row.names = FALSE)
utils::write.csv(out, file.path(work, 'r2e_selftest.csv'), row.names = FALSE)
cat(if (all(out$passed)) 'SELFTEST PASSED:' else 'SELFTEST FAILED:', sum(out$passed), '/', nrow(out), '\n')
if (!all(out$passed)) quit(status = 1)
