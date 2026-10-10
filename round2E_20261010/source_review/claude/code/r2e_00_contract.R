# Round2E 第0步：在任何新估计之前冻结合同、绑定Round2D来源、计算真实支持点和Z0信度背景。不调用Mplus。
# 用法：Rscript r2e_00_contract.R            （环境变量 R2E_ROOT=新空目录，R2D_ROOT=Round2D目录）
local({ a <- commandArgs(FALSE); f <- sub('^--file=', '', a[grep('^--file=', a)]); f <- f[basename(f) == 'r2e_00_contract.R']
  Sys.setenv(R2E_CODE = if (length(f)) dirname(normalizePath(f)) else Sys.getenv('R2E_CODE', '.')) })
source(file.path(Sys.getenv('R2E_CODE'), 'r2e_engine.R'))
stopifnot(dir.exists(R2D), file.exists(file.path(R2D, 'audit', 'Z_CONTRACT.json')))
if (file.exists(file.path(R2E, 'contracts', 'RUN_CONTRACT_2E.json'))) stop('Contract already frozen; do not overwrite. Remove only if no Round2E call has been registered.')
for (d in c('contracts', 'audit', 'runtime', 'models', 'results', 'private')) dir.create(file.path(R2E, d), showWarnings = FALSE)
chk <- list()
# 1) 上游数学与Round2D逐字节一致
chk$upstream_identical <- hashf(file.path(.r2e_dir, 'r2e_upstream_math.R')) == hashf(file.path(R2D, 'code', '00_upstream_math.R'))
# 2) Round2D 已终止：存在终态文件；本机没有其他Mplus进程（由资源检查只读确认）
chk$r2d_queue_terminal <- file.exists(file.path(R2D, 'runtime', 'queue_terminal.json'))
if (!DRYRUN && !identical(Sys.getenv('R2E_RESOURCE_GATE'), '0')) {
  rr <- file.path(R2E, 'runtime', 'resource_at_contract.json')
  system2(PY, c(shQuote(file.path(.r2e_dir, 'r2e_resource_gate.py')), shQuote(rr), shQuote(file.path(R2E, 'runtime', 'PAUSE'))), stdout = FALSE)
  rg <- fromJSON(rr); chk$no_running_mplus <- rg$external_mplus_count == 0; chk$machine <- rg[c('physical_cores', 'logical_cores', 'total_physical_gib')]
}
# 3) 私有成员文件与 Z_CONTRACT 哈希一致；Z0 在十份间相同、等于z1、无缺失；资源列 0/1
zc <- zc2d(); bind <- list(); sup <- list(); grp <- list()
for (z in R2E_ZS) {
  s <- zc$samples[[paste0(z, '_Z0')]]; zs <- NULL
  for (k in 1:10) {
    f <- data_path(z, k); ok <- file.exists(f) && hashf(f) == s$data_sha256[[k]]
    bind[[length(bind) + 1]] <- data.frame(z = z, member = k, file = f, hash_matches_Z_CONTRACT = ok)
    if (!ok) next
    d <- read_dat(f, R2D_NAMES); stopifnot(nrow(d) == s$N, all(is.finite(d$z0)), max(abs(d$z0 - d$z1)) < 1e-10)
    if (is.null(zs)) zs <- d$z0 else stopifnot(max(abs(zs - d$z0)) < 1e-10)
    if (z == 'SD') for (g in c('c2', 'c3', 'ginc')) { v <- d[[g]]; stopifnot(all(v %in% c(0, 1)))
      grp[[length(grp) + 1]] <- data.frame(member = k, g = g, n1 = sum(v == 1), n0 = sum(v == 0)) }
  }
  zz <- zc$z[[z]]; raw0 <- zz$orientation * (0 - zz$ref_mean) / zz$ref_sd
  if (!is.null(zs)) sup[[z]] <- cbind(branch = z, support_points(zs, raw0))
}
cc <- data_path('SD', 1, 'CC'); chk$cc_file_matches <- file.exists(cc) && hashf(cc) == zc$samples$SD_CC$data_sha256
bind <- do.call(rbind, bind); chk$all_member_hashes_match <- all(bind$hash_matches_Z_CONTRACT)
utils::write.csv(bind, file.path(R2E, 'contracts', 'SOURCE_BINDING.csv'), row.names = FALSE)
supt <- do.call(rbind, sup); utils::write.csv(supt, file.path(R2E, 'contracts', 'SUPPORT_POINTS.csv'), row.names = FALSE)
if (length(grp)) utils::write.csv(do.call(rbind, grp), file.path(R2E, 'contracts', 'H4_GROUP_SIZES_BY_MEMBER.csv'), row.names = FALSE)
# 4) 尾部影响敏感性数据：各分支第1份，z0 按 P1/P99 缩尾（只放本机 private；z1—z5 不变，E1 只用 z0）
for (z in R2E_ZS) { f <- data_path(z, 1); if (!file.exists(f)) next
  d <- read_dat(f, R2D_NAMES); d$z0 <- winsorize(d$z0); dir.create(file.path(R2E, 'private', z), recursive = TRUE, showWarnings = FALSE)
  w <- data_path(z, 1, 'W'); if (!file.exists(w)) write_dat(d, w) }
# 5) Z0 对潜在 IZ 的信度背景：只读 Round2D 已保存 D0 输出（状态照录）
rel <- list()
for (z in R2E_ZS) for (k in 1:10) for (att in c('base')) {
  d <- file.path(R2D, 'models', z, sprintf('D0_Z0_MI%02d', k), att); if (!file.exists(file.path(d, 'receipt.json'))) next
  r <- fromJSON(file.path(d, 'receipt.json')); m <- tryCatch(read_mplus_raw(d), error = function(e) NULL); if (is.null(m)) next
  rel[[length(rel) + 1]] <- data.frame(z = z, member = k, attempt = att, round2D_status = r$status, t(z0_reliability(m)))
}
if (length(rel)) utils::write.csv(do.call(rbind, rel), file.path(R2E, 'contracts', 'Z0_RELIABILITY_FROM_ROUND2D_D0.csv'), row.names = FALSE)
# 6) 合同（估计前冻结）
spl <- lapply(split(supt, supt$branch), function(x) list(point = x$point, z = x$z, min_z = x$min_z[1], max_z = x$max_z[1], N = x$N[1]))
ct <- list(
  round = 'Round2E', frozen_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE), dryrun = DRYRUN,
  sources = list(round2D_root = R2D, round2D_commit = 'cf5ab4fb9e1e59742462a7dadd85ff6fdbdb83b0', z_contract_sha256 = hashf(file.path(R2D, 'audit', 'Z_CONTRACT.json'))),
  checks = chk,
  scope = 'Observed-2012 Z0 moderation SX x Z0 -> SY for SD, SEXGAP, OLDEST, SONGAP (E0/E1); SY-boundary companion families only when triggered; D0B diagnostics; two bounded latent probes on OLDEST MI01; SD complete-case and tail-influence sensitivities; then SD resource-group H4 batch.',
  estimand_note = 'Z0 is the observed 2012 configuration conditioned on as a covariate (no distributional assumption on Z0). It is not the latent initial level IZ; as a proxy for IZ the moderation is attenuated (see Z0_RELIABILITY_FROM_ROUND2D_D0.csv).',
  specs = list(E0 = 'SW + ix sx ON z0; iy ON z0 (gi0); sy ON z0 (gs0); x1 y1 ON z0', E1 = 'E0 + sxz | sx XWITH z0; sy ON sxz (dc)',
               E0B_E1B = 'same as E0/E1 plus sy@0 (SY conditional residual fixed at the boundary), all ten members',
               H4 = 'E1 + G main (if not a control) + zg=z0*G + sx XWITH G + sx XWITH zg; dc=delta0, dcg=deltaG; inherits SD E1 SY treatment',
               D0B = 'Round2D D0 plus sy@0 (diagnostic only)', D1L = 'Round2D D1, starts spliced from legal Round2D OLDEST D0 MI01', D1B = 'D1 plus sy@0, starts from D0B'),
  boundary_rule = list(member = 'BOUNDARY_SY when the only violation is a negative PSI:SY with est/SE > -1.96 and the model is otherwise admissible after setting SY to 0',
                       family = 'free family adopted only if all 10 members USABLE (+ MI01 numeric checks for LMS); if all non-usable members are BOUNDARY_SY, run the B family (sy@0) for all 10 members and adopt it if all 10 are USABLE; otherwise not poolable',
                       never = 'no member deletion, no mixing free and boundary members, no p-value based choice'),
  numerics = list(points_initial = 15, points_check = 20, points_repair = 30, start_LL = .01, start_path_abs = .001, start_path_se = .01,
                  integration_path_se = .05, se_rel = .05, mcse_over_se_flag = .05, processors_candidate = 4,
                  processors_rule = 'SD E1 MI01 at 15 points run with 1 and 4 processors; adopt 4 only if LL/paths/SEs agree under the start tolerance and it is at least 20% faster'),
  support = spl, reference_rule = 'raw-zero point, medians of non-zero values on each side (>=5% share), P10/P90 if distinct; presentation only',
  h4 = list(groups = list(EDU = 'c2 = 1 junior high or above', URBAN = 'c3 = 1 urban NBS2012', INC = 'ginc = 1 positive personal income (not high income)'),
            test = 'deltaG two-sided; Holm over 3 resources; nine Bonferroni simultaneous 95% intervals (delta0, delta1, deltaG x 3)',
            direction = 'component-specific: weakening (delta>0) or buffering (delta<0); H4.2b needs the advantaged group delta1 established and deltaG in the same direction, delta0 not significantly opposite; H4.2a the mirror; crossover reported separately; sign of deltaG alone is never mapped'),
  multiplicity = list(E1_dc = 'Holm, family of 4 (missing tests stay missing)', E0_gi0_gs0 = 'Holm, family of 4 each', H4 = 'Holm, family of 3'),
  per_call_seconds = list(linear = 600, lms_observed = 1800, lms_latent = 3600),
  caps = list(B1 = list(PILOT = 8, CHECK = 9, PROBE = 6, MEMBER = 72, BOUNDARY = 88, SENS = 6, REPAIR = 12, TOTAL = 201),
              H4 = list(PILOT = 3, CHECK = 6, MEMBER = 27, REPAIR = 3, TOTAL = 39)),
  budgets = list(B1 = list(engine_hours = 8, wall_hours = 10), H4 = list(engine_hours = 5, wall_hours = 6)),
  run_h4_after_batch1 = !identical(Sys.getenv('R2E_RUN_H4'), '0'),
  parallel_models = 1,
  inference = 'conditional on fixed model and current household-person MI; MI01-only numeric checks; complete-data df infinity, Barnard-Rubin as sensitivity',
  code_sha256 = as.list(vapply(list.files(.r2e_dir, pattern = '\\.(R|py)$'), function(f) hashf(file.path(.r2e_dir, f)), character(1))))
wj(ct, file.path(R2E, 'contracts', 'RUN_CONTRACT_2E.json'))
print(chk[setdiff(names(chk), 'machine')]); print(supt, row.names = FALSE)
if (!isTRUE(chk$upstream_identical) || !isTRUE(chk$all_member_hashes_match) || isFALSE(chk$no_running_mplus))
  stop('CONTRACT CHECK FAILED: see contracts/RUN_CONTRACT_2E.json checks; do not start estimation')
cat('CONTRACT FROZEN\n')
