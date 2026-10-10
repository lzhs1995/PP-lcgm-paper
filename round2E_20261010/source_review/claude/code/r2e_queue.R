# Round2E 队列：观测基期路线优先、分支轮转、不按P值调度；廉价模型十份全跑以如实记录成员失败数。
# 阶段：A=四分支MI01与数值核查+D0B诊断；B=其余成员；B2=触发时的SY边界家族；D=敏感性；C=两次潜路线小试（最低优先）；H4=资源组批次。
source(file.path(Sys.getenv('R2E_CODE'), 'r2e_engine.R'))
XW_E <- c('sxz | sx XWITH z0;', 'sy ON sxz*0 (dc);')
XW_D <- c('sxiz | sx XWITH iz;', 'sy ON sxiz*0 (dc);')
h4_add <- function(g) { gg <- R2E_G[[g]]
  c(if (!gg$in_controls) paste0('ix sx iy sy ON ', gg$col, '*0;'), 'ix sx ON zg*0;', 'iy ON zg*0 (gizg);', 'sy ON zg*0 (gszg);',
    paste0('sxg | sx XWITH ', gg$col, ';'), 'sxzg | sx XWITH zg;', 'sy ON sxg*0 (bxg);', 'sy ON sxzg*0 (dcg);') }
state_file <- function(n) file.path(R2E, 'runtime', paste0(n, '.json'))
save_state <- function(x, n) { wj(x, state_file(n)); x }
load_state <- function(n) if (file.exists(state_file(n))) fromJSON(state_file(n), simplifyVector = FALSE) else NULL
has_out <- function(a) !is.null(a) && file.exists(file.path(a$dest, 'model.out'))
procs <- function() { s <- load_state('processors_decision'); if (is.null(s)) 1L else as.integer(s$adopted) }
is_lms <- function(spec) spec %in% c('E1', 'E1B', 'D1L', 'D1B') || grepl('^H4', spec)
repair_left <- function(batch, cat = 'REPAIR') { if (DRYRUN) return(FALSE); tab <- if (file.exists(REG)) utils::read.csv(REG) else data.frame()
  n <- if (nrow(tab)) sum(tab$batch == batch & tab$category == cat) else 0; n < contract()$caps[[batch]][[cat]] }
r2d_out <- function(z, spec = 'D0', k = 1, att = 'base') file.path(R2D, 'models', z, sprintf('%s_Z0_MI%02d', spec, k), att)
slim <- function(x) x[setdiff(names(x), 'paths')]

# 起点核查（预登记的结果类别）：AGREE=与采用解在start容差内一致；ALT_LOWER=另一起点收敛到LL更低（>.01）的解，保留采用解并标注；
# ALT_FAILED=默认起点未得到可用/边界解（不构成反证，标注"起点未复现"）；BEATEN=另一起点LL更高（>.01）→ 不通过；
# RIDGE=LL差≤.01但路径超出容差（似然脊/弱识别）→ 不通过。
start_outcome <- function(adopted, st) {
  if (is.null(adopted$key)) return(list(outcome = 'NO_ADOPTED_SOLUTION', passed = FALSE))
  if (is.null(st) || is.null(st$key)) return(list(outcome = 'ALT_FAILED', passed = TRUE, alt_status = if (is.null(st)) 'NOT_RUN' else st$receipt$status))
  # 默认起点用规格语法生成，采用解来自SVALUES拼接：自由参数个数不同即结构不一致，不通过
  if (!is.null(adopted$receipt$parameters) && !is.null(st$receipt$parameters) && !identical(as.integer(adopted$receipt$parameters), as.integer(st$receipt$parameters)))
    return(list(outcome = 'STRUCTURE_MISMATCH', passed = FALSE, adopted_parameters = adopted$receipt$parameters, alt_parameters = st$receipt$parameters))
  cmp <- compare_numeric(adopted, st, 'start'); dLL <- as.numeric(st$receipt$LL) - as.numeric(adopted$receipt$LL)
  th <- contract()$numerics$start_LL
  oc <- if (isTRUE(cmp$passed)) 'AGREE' else if (is.finite(dLL) && dLL > th) 'BEATEN' else if (is.finite(dLL) && dLL < -th) 'ALT_LOWER' else 'RIDGE'
  c(list(outcome = oc, passed = oc %in% c('AGREE', 'ALT_LOWER'), alt_minus_adopted_LL = dLL), slim(cmp))
}
# 预算分配（只用MI01实际耗时，不看估计值）：E0九份先扣除；E1九份×1.25按所需时间从小到大依次纳入，累计不超过剩余预算。
# 这样在预算内完成的家族数最多；被排除的只能是耗时最长者，并如实记为 NOT_ESTIMATED_WITHIN_BUDGET。
waterfill <- function(need, total) {
  ok <- setNames(rep(FALSE, length(need)), names(need)); left <- total
  for (z in names(sort(need[is.finite(need)]))) if (need[[z]] <= left) { ok[[z]] <- TRUE; left <- left - need[[z]] }
  ok
}

# ---------------------------------------------------------------- A：四分支 MI01（每步跨分支轮转）
phase_A <- function() {
  if (!is.null(load_state('phase_A'))) return(load_state('phase_A'))
  P <- list(); for (z in R2E_ZS) P[[z]] <- list()
  for (z in R2E_ZS) P[[z]]$e0 <- run_one(z, 'E0', 1, 'base', 'PILOT', 'B1')
  for (z in R2E_ZS) P[[z]]$e1 <- run_one(z, 'E1', 1, 'q15', 'PILOT', 'B1', points = 15, processors = 1,
                                          warm = if (has_out(P[[z]]$e0)) list(from = P[[z]]$e0$dest, add = XW_E))
  # 处理器：只做一次 SD 配对（同输入、同起点、同积分点），不跑短探针
  sd <- P$SD$e1; pd <- list(adopted = 1L, reason = 'SD E1 MI01 not usable/boundary; stay single-core')
  if (ok_member(sd) || bnd_member(sd)) {
    p4 <- run_one('SD', 'E1', 1, 'q15p4', 'CHECK', 'B1', points = 15, processors = contract()$numerics$processors_candidate,
                  warm = if (has_out(P$SD$e0)) list(from = P$SD$e0$dest, add = XW_E))
    cmp <- compare_numeric(sd, p4, 'processors'); t1 <- as.numeric(sd$receipt$seconds); t4 <- if (is.null(p4)) NA else as.numeric(p4$receipt$seconds)
    faster <- isTRUE(is.finite(t4) && t4 <= .8 * t1)
    pd <- list(adopted = if (isTRUE(cmp$passed) && faster) as.integer(contract()$numerics$processors_candidate) else 1L,
               seconds_1 = t1, seconds_candidate = t4, numeric = slim(cmp), faster_by_20pct = faster)
  }
  save_state(pd, 'processors_decision')
  for (z in R2E_ZS) {
    a <- P[[z]]$e1; from_e1 <- ok_member(a) || bnd_member(a)
    src <- if (from_e1) a$dest else if (has_out(P[[z]]$e0)) P[[z]]$e0$dest else NULL
    P[[z]]$e1h <- run_one(z, 'E1', 1, 'q20', 'CHECK', 'B1', points = 20, processors = procs(),
                          warm = if (!is.null(src)) list(from = src, add = if (from_e1) character(0) else XW_E))
    # q20失败时的一次修复：若刚才从E1起，则改从E0+乘积项起；否则用默认起点
    if (!ok_member(P[[z]]$e1h) && !bnd_member(P[[z]]$e1h) && !interface_error(P[[z]]$e1h) && repair_left('B1'))
      P[[z]]$e1h <- run_one(z, 'E1', 1, 'q20r', 'REPAIR', 'B1', points = 20, processors = procs(),
                            warm = if (from_e1 && has_out(P[[z]]$e0)) list(from = P[[z]]$e0$dest, add = XW_E) else NULL)
  }
  dec <- list()
  for (z in R2E_ZS) {
    lo <- P[[z]]$e1; hi <- P[[z]]$e1h; ig <- compare_numeric(lo, hi, 'integration'); adopted <- hi; pts <- 20L
    if (!isTRUE(ig$passed) && (ok_member(hi) || bnd_member(hi)) && repair_left('B1')) {
      r30 <- run_one(z, 'E1', 1, 'q30', 'REPAIR', 'B1', points = 30, processors = procs(), warm = list(from = hi$dest))
      ig <- compare_numeric(hi, r30, 'integration'); adopted <- r30; pts <- 30L
    }
    st <- if (ok_member(adopted) || bnd_member(adopted)) run_one(z, 'E1', 1, 'start', 'CHECK', 'B1', points = pts, processors = procs()) else NULL
    so <- start_outcome(adopted, st)
    dec[[z]] <- list(z = z, e0_status = P[[z]]$e0$receipt$status, e1_q15_status = lo$receipt$status, e1_adopted_attempt = adopted$receipt$attempt,
                     e1_adopted_status = adopted$receipt$status, e1_adopted_boundary = bnd_member(adopted), points = pts,
                     integration = slim(ig), start = so, numeric_ok = isTRUE(ig$passed) && isTRUE(so$passed),
                     e0_seconds = as.numeric(P[[z]]$e0$receipt$seconds), e1_seconds = as.numeric(adopted$receipt$seconds))
  }
  for (z in R2E_ZS) { src <- r2d_out(z)
    dec[[z]]$d0b <- run_one(z, 'D0B', 1, 'base', 'PROBE', 'B1', warm = if (file.exists(file.path(src, 'model.out'))) list(from = src) else NULL)$receipt[c('status', 'psi_SY', 'psi_SY_se', 'negative', 'LL', 'seconds')] }
  # 预算预估（只用耗时）：E0九份先扣除；E1九份按注水分配
  bs <- budget_state('B1'); e0need <- sum(vapply(R2E_ZS, function(z) 9 * dec[[z]]$e0_seconds, 0), na.rm = TRUE)
  run_e1 <- vapply(R2E_ZS, function(z) isTRUE(dec[[z]]$numeric_ok) || isTRUE(dec[[z]]$e1_adopted_boundary), TRUE)
  need <- vapply(R2E_ZS, function(z) if (run_e1[[z]]) 9 * 1.25 * dec[[z]]$e1_seconds else NA_real_, 0)
  fit <- waterfill(need, bs$engine_left - e0need)
  for (z in R2E_ZS) { dec[[z]]$run_e1_members <- run_e1[[z]]; dec[[z]]$projected_e1_seconds <- need[[z]]; dec[[z]]$within_budget_share <- isTRUE(fit[[z]]) }
  save_state(list(decisions = dec, budget = bs, e0_projected_seconds = e0need, processors = procs(), finished_utc = format(Sys.time(), tz = 'UTC', usetz = TRUE)), 'phase_A')
}

# ---------------------------------------------------------------- 家族成员与分类
member_final <- function(z, spec, k, sample = 'Z0') {          # 每份MI的终态尝试：有修复取修复，否则取base（MI01取采用尝试）
  A <- load_state('phase_A')
  if (k == 1 && spec == 'E1') return(if (is.null(A)) NULL else read_member(z, 'E1', 1, A$decisions[[z]]$e1_adopted_attempt))
  if (k == 1 && spec == 'E1B') { s <- load_state(paste0('E1B_', z)); return(if (is.null(s)) NULL else read_member(z, 'E1B', 1, s$adopted_attempt)) }
  r <- read_member(z, spec, k, 'repair', sample); if (!is.null(r)) return(r)
  read_member(z, spec, k, 'base', sample)
}
family_class <- function(z, spec) {
  ms <- lapply(1:10, function(k) member_final(z, spec, k)); st <- vapply(ms, function(a) if (is.null(a)) 'NOT_RUN' else a$receipt$status, '')
  num_ok <- if (!is_lms(spec)) TRUE else if (spec == 'E1') isTRUE(load_state('phase_A')$decisions[[z]]$numeric_ok) else isTRUE(load_state(paste0('E1B_', z))$numeric_ok)
  cls <- if (all(st == 'USABLE') && num_ok) 'ADOPT' else
    if (all(st %in% c('USABLE', 'BOUNDARY_SY')) && any(st == 'BOUNDARY_SY') && !grepl('B$', spec)) 'NEED_BOUNDARY' else
    if (all(st == 'USABLE') && !num_ok) 'NUMERIC_CHECK_FAILED' else if (any(st == 'NOT_RUN')) 'INCOMPLETE' else 'NOT_POOLABLE'
  list(z = z, spec = spec, class = cls, statuses = st, numeric_ok = num_ok, members = ms)
}

# ---------------------------------------------------------------- B：其余成员（E0 全部先跑，再 E1 轮转）
member_with_repair <- function(z, spec, k, category, batch, points = 15L, warm = NULL, repair_warm = NULL, sample = 'Z0') {
  pr <- if (is_lms(spec)) procs() else 1L
  a <- run_one(z, spec, k, 'base', category, batch, sample, points, pr, warm = warm)
  if (!ok_member(a) && !bnd_member(a) && !interface_error(a) && repair_left(batch))
    a <- run_one(z, spec, k, 'repair', 'REPAIR', batch, sample, points, pr, warm = repair_warm)
  a
}
phase_B <- function() {
  A <- load_state('phase_A'); stopifnot(!is.null(A))
  for (k in 2:10) for (z in R2E_ZS) {
    e01 <- read_member(z, 'E0', 1, 'base')
    member_with_repair(z, 'E0', k, 'MEMBER', 'B1', repair_warm = if (ok_member(e01) || bnd_member(e01)) list(from = e01$dest) else NULL)
  }
  for (k in 2:10) for (z in R2E_ZS) {
    d <- A$decisions[[z]]; if (!isTRUE(d$run_e1_members) || !isTRUE(d$within_budget_share)) next
    src <- read_member(z, 'E1', 1, d$e1_adopted_attempt); e0k <- member_final(z, 'E0', k)
    member_with_repair(z, 'E1', k, 'MEMBER', 'B1', points = d$points, warm = list(from = src$dest),
                       repair_warm = if (has_out(e0k)) list(from = e0k$dest, add = XW_E) else NULL)
  }
  out <- list(); for (z in R2E_ZS) for (sp in c('E0', 'E1')) { f <- family_class(z, sp); out[[paste(z, sp)]] <- f[c('z', 'spec', 'class', 'statuses', 'numeric_ok')] }
  for (z in R2E_ZS) { d <- A$decisions[[z]]
    if (isTRUE(d$run_e1_members) && !isTRUE(d$within_budget_share)) out[[paste(z, 'E1')]]$class <- 'NOT_ESTIMATED_WITHIN_BUDGET' }
  save_state(out, 'phase_B')
}
# ---------------------------------------------------------------- B2：触发时的 SY 边界家族（整族同规格，不混合、不删成员）
phase_B2 <- function() {
  B <- load_state('phase_B'); stopifnot(!is.null(B)); A <- load_state('phase_A'); res <- list()
  for (x in B) {
    if (x$class != 'NEED_BOUNDARY') next
    z <- x$z; sp <- paste0(x$spec, 'B')
    if (sp == 'E0B') {
      for (k in 1:10) { fr <- member_final(z, 'E0', k); member_with_repair(z, 'E0B', k, 'BOUNDARY', 'B1', warm = list(from = fr$dest)) }
    } else {
      fr1 <- member_final(z, 'E1', 1); pts <- A$decisions[[z]]$points
      h <- run_one(z, 'E1B', 1, paste0('q', pts), 'BOUNDARY', 'B1', points = pts, processors = procs(), warm = list(from = fr1$dest))
      l <- run_one(z, 'E1B', 1, 'q15', 'BOUNDARY', 'B1', points = 15, processors = procs(), warm = list(from = fr1$dest))
      s <- if (ok_member(h)) run_one(z, 'E1B', 1, 'start', 'BOUNDARY', 'B1', points = pts, processors = procs()) else NULL
      ig <- compare_numeric(l, h, 'integration'); so <- start_outcome(h, s)
      save_state(list(adopted_attempt = paste0('q', pts), numeric_ok = isTRUE(ig$passed) && isTRUE(so$passed), integration = slim(ig), start = so), paste0('E1B_', z))
      if (ok_member(h)) for (k in 2:10) { fr <- member_final(z, 'E1', k)
        member_with_repair(z, 'E1B', k, 'BOUNDARY', 'B1', points = pts, warm = list(from = h$dest),
                           repair_warm = if (has_out(fr)) list(from = fr$dest) else NULL) }
    }
    f <- family_class(z, sp); res[[paste(z, sp)]] <- f[c('z', 'spec', 'class', 'statuses', 'numeric_ok')]
  }
  save_state(res, 'phase_B2')
}
adopted_E <- function(z, spec) {            # 返回 'E1' / 'E1B' / NULL
  B <- load_state('phase_B'); B2 <- load_state('phase_B2')
  if (identical(B[[paste(z, spec)]]$class, 'ADOPT')) return(spec)
  if (!is.null(B2) && identical(B2[[paste(z, paste0(spec, 'B'))]]$class, 'ADOPT')) return(paste0(spec, 'B'))
  NULL
}
# ---------------------------------------------------------------- D：敏感性（只对已采用家族；描述性，不合并）
phase_D <- function() {
  A <- load_state('phase_A'); res <- list()
  for (z in R2E_ZS) { sp <- adopted_E(z, 'E1'); if (is.null(sp)) next
    src <- member_final(z, sp, 1)
    res[[paste(z, 'tail')]] <- run_one(z, sp, 1, 'winsor', 'SENS', 'B1', sample = 'W', points = A$decisions[[z]]$points, processors = procs(), warm = list(from = src$dest))$receipt[c('id', 'status', 'seconds')] }
  e0 <- adopted_E('SD', 'E0'); e1 <- adopted_E('SD', 'E1')
  if (!is.null(e0) && !is.null(e1)) {
    a <- run_one('SD', e0, 1, 'cc', 'SENS', 'B1', sample = 'CC')
    res$SD_cc_E0 <- a$receipt[c('id', 'status', 'seconds')]
    res$SD_cc_E1 <- run_one('SD', e1, 1, 'cc', 'SENS', 'B1', sample = 'CC', points = A$decisions$SD$points, processors = procs(),
                            warm = if (has_out(a)) list(from = a$dest, add = XW_E))$receipt[c('id', 'status', 'seconds')]
  }
  save_state(res, 'phase_D')
}
# ---------------------------------------------------------------- C：潜路线两次小试（诊断，不形成MI推断；最低优先）
phase_C <- function() {
  bs <- budget_state('B1'); res <- list(skipped = FALSE)
  if (bs$engine_left < 2 * contract()$per_call_seconds$lms_latent) return(save_state(list(skipped = TRUE, reason = 'insufficient remaining engine budget'), 'phase_C'))
  src <- r2d_out('OLDEST')
  res$L1 <- run_one('OLDEST', 'D1L', 1, 'from_r2d_d0', 'PROBE', 'B1', points = 15, processors = procs(), warm = list(from = src, add = XW_D))$receipt[c('status', 'psi_SY', 'psi_SY_se', 'negative', 'seconds', 'iterations', 'median_iteration_seconds', 'LL')]
  save_state(res, 'phase_C_partial')
  d0b <- read_member('OLDEST', 'D0B', 1, 'base')
  res$L2 <- if (ok_member(d0b)) run_one('OLDEST', 'D1B', 1, 'from_d0b', 'PROBE', 'B1', points = 15, processors = procs(), warm = list(from = d0b$dest, add = XW_D))$receipt[c('status', 'negative', 'seconds', 'iterations', 'median_iteration_seconds', 'LL')] else
    list(status = 'NOT_RUN', reason = 'OLDEST D0B MI01 not usable')
  save_state(res, 'phase_C')
}
# ---------------------------------------------------------------- H4：资源组（SD E1 家族采用后；继承其 SY 处理；不以dc显著为门槛）
phase_H4 <- function() {
  e1 <- adopted_E('SD', 'E1'); if (is.null(e1)) return(save_state(list(skipped = TRUE, reason = 'SD E1 family not adopted'), 'phase_H4'))
  if (!isTRUE(contract()$run_h4_after_batch1)) return(save_state(list(skipped = TRUE, reason = 'run_h4_after_batch1 = FALSE'), 'phase_H4'))
  src <- member_final('SD', e1, 1); res <- list(inherited = e1)
  for (g in names(R2E_G)) {
    sp <- paste0(if (e1 == 'E1B') 'H4B_' else 'H4_', g)
    l <- run_one('SD', sp, 1, 'q15', 'PILOT', 'H4', points = 15, processors = procs(), warm = list(from = src$dest, add = h4_add(g)))
    h <- run_one('SD', sp, 1, 'q20', 'CHECK', 'H4', points = 20, processors = procs(),
                 warm = if (ok_member(l) || bnd_member(l)) list(from = l$dest) else list(from = src$dest, add = h4_add(g)))
    ig <- compare_numeric(l, h, 'integration')
    s <- if (ok_member(h)) run_one('SD', sp, 1, 'start', 'CHECK', 'H4', points = 20, processors = procs()) else NULL
    so <- start_outcome(h, s); nok <- isTRUE(ig$passed) && isTRUE(so$passed)
    st <- c(h$receipt$status)
    if (nok && ok_member(h)) for (k in 2:10) {
      a <- run_one('SD', sp, k, 'base', 'MEMBER', 'H4', points = 20, processors = procs(), warm = list(from = h$dest))
      if (!ok_member(a) && !bnd_member(a) && !interface_error(a) && repair_left('H4'))
        a <- run_one('SD', sp, k, 'repair', 'REPAIR', 'H4', points = 20, processors = procs(), warm = list(from = member_final('SD', e1, k)$dest, add = h4_add(g)))
      st <- c(st, a$receipt$status) }
    cls <- if (!nok) 'NUMERIC_CHECK_FAILED' else if (length(st) == 10 && all(st == 'USABLE')) 'ADOPT' else
      if (length(st) == 10 && all(st %in% c('USABLE', 'BOUNDARY_SY'))) 'NEED_BOUNDARY_NOT_RUN' else 'NOT_POOLABLE'
    res[[g]] <- list(spec = sp, numeric_ok = nok, integration = slim(ig), start = so, statuses = st, class = cls, adopted = cls == 'ADOPT')
    save_state(res, 'phase_H4_partial')
  }
  save_state(res, 'phase_H4')
}
