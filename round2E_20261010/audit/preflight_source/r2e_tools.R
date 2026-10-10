# Round2E 纯函数工具（不调用Mplus、不写项目目录）。
# 1) 上游数学函数：r2e_upstream_math.R 与 Round2D code/00_upstream_math.R 逐字节相同（r2e_00_contract.R 核对哈希）。
# 2) 移植自 Round2D code/01_tools.R 的覆盖函数（canonical_measurement、几何、gate、key_paths、compare_numeric），
#    去掉写死的 C:/ 路径，并补上 SY 边界规格（fixed_zero）所需的参数。
# 3) Round2E 新增：E线/H4 语法（SX×Z0，可选 sy@0）、D0B/D1B 诊断语法、SVALUES 跨规格拼接与非法起点清洗、
#    边界分类、真实支持点、H4 方向判定表、Z0 对 IZ 信度。
.r2e_dir <- local({ f <- sys.frames(); p <- NULL
  for (i in rev(seq_along(f))) if (!is.null(f[[i]]$ofile)) { p <- dirname(normalizePath(f[[i]]$ofile)); break }
  if (is.null(p)) p <- Sys.getenv('R2E_CODE', getwd()); p })
source(file.path(.r2e_dir, 'r2e_upstream_math.R'), local = FALSE)

R2E_ZS <- c('SD', 'SEXGAP', 'OLDEST', 'SONGAP')          # 预定顺序，只用于排队，不代表优先级
FAC_XY <- c('IX', 'SX', 'IY', 'SY'); OBS_XY <- c(paste0('X', 1:5), paste0('Y', 1:5))
KEY_XY <- data.frame(label = c('bii', 'bis', 'bss', 'bsyiy'), row = c('IY', 'SY', 'SY', 'SY'), column = c('IX', 'IX', 'SX', 'IY'))
key_add <- function(label, row, column) data.frame(label = label, row = row, column = column)

# ---------------------------------------------------------------- 语法
# E线：SW + 观测2012 Z0。只估计 SX×Z0→SY（与Round2D用户确认范围一致，不加IX乘积）；boundary=TRUE 时 sy@0。
e_lines_r2e <- function(interaction = c('none', 'C'), ctrl = 'c1-c24', boundary = FALSE, yshape = 'linear') {
  interaction <- match.arg(interaction)
  m <- c(sw_lines(yshape = yshape, ctrl = ctrl), 'ix sx ON z0;', 'iy ON z0 (gi0);', 'sy ON z0 (gs0);', 'x1 y1 ON z0;')
  if (interaction == 'C') m <- c(m, 'sxz | sx XWITH z0;', 'sy ON sxz (dc);')
  if (boundary) m <- c(m, 'sy@0;')
  m
}
# H4：E1 + G主项（不在控制集时）+ Z0×G 主项 + SX×G + SX×Z0×G。g 为 0/1 列名；zg 在 DEFINE 中生成。
e2_lines_r2e <- function(g, g_in_controls, ctrl = 'c1-c24', boundary = FALSE) {
  m <- c(sw_lines(ctrl = ctrl), 'ix sx ON z0 zg;', 'iy ON z0 (gi0);', 'iy ON zg (gizg);',
         'sy ON z0 (gs0);', 'sy ON zg (gszg);', 'x1 y1 ON z0;')
  if (!g_in_controls) m <- c(m, paste0('ix sx iy sy ON ', g, ';'))
  m <- c(m, 'sxz | sx XWITH z0;', paste0('sxg | sx XWITH ', g, ';'), 'sxzg | sx XWITH zg;',
         'sy ON sxz (dc);', 'sy ON sxg (bxg);', 'sy ON sxzg (dcg);')
  if (boundary) m <- c(m, 'sy@0;')
  m
}
# 潜路线诊断：Round2D 的 D0/D1 结构，可选 sy@0（D0B/D1B）。
d_lines_r2e <- function(shape, interaction = c('none', 'C'), ctrl = 'c1-c24', boundary = FALSE) {
  m <- d_lines(shape, match.arg(interaction), ctrl)
  if (boundary) m <- c(m, 'sy@0;')
  m
}
R2E_G <- list(EDU = list(col = 'c2', in_controls = TRUE), URBAN = list(col = 'c3', in_controls = TRUE),
              INC = list(col = 'ginc', in_controls = FALSE))
# 规格登记。boundary 规格以 B 结尾（E0B、E1B、H4B_EDU…、D0B、D1B）。D1L=潜路线自由SY小试。
spec_info_r2e <- function(z, spec, ctrl, zshape = 'linear') {
  b <- grepl('B$', spec) || grepl('^H4B_', spec)
  keye <- rbind(KEY_XY, key_add(c('gi0', 'gs0'), c('IY', 'SY'), c('Z0', 'Z0')))
  keyd <- rbind(KEY_XY, key_add(c('gii', 'gis', 'gss'), c('IY', 'SY', 'SY'), c('IZ', 'IZ', 'SZ')))
  fz <- if (b) 'SY' else character(0)
  if (spec %in% c('E0', 'E0B', 'E1', 'E1B')) {
    lms <- spec %in% c('E1', 'E1B')
    return(list(kind = if (lms) 'lms_observed' else 'linear', model = e_lines_r2e(if (lms) 'C' else 'none', ctrl, b),
                fac = FAC_XY, obs = OBS_XY, use = c('x1-x5', 'y1-y5', 'z0', ctrl), fixed_zero = fz,
                key = if (lms) rbind(keye, key_add('dc', 'SY', 'SXZ')) else keye, define = NULL))
  }
  if (grepl('^H4B?_', spec)) {
    g <- R2E_G[[sub('^H4B?_', '', spec)]]; stopifnot(!is.null(g))
    return(list(kind = 'lms_observed', model = e2_lines_r2e(g$col, g$in_controls, ctrl, b), fac = FAC_XY, obs = OBS_XY,
                use = c('x1-x5', 'y1-y5', 'z0', if (!g$in_controls) g$col, ctrl, 'zg'), define = paste0('zg=z0*', g$col, ';'),
                fixed_zero = fz, g = g$col,
                key = rbind(keye, key_add(c('gizg', 'gszg', 'dc', 'bxg', 'dcg'), c('IY', 'SY', 'SY', 'SY', 'SY'), c('ZG', 'ZG', 'SXZ', 'SXG', 'SXZG')))))
  }
  if (spec %in% c('D0', 'D0B', 'D1L', 'D1B')) {         # D0 只用于读回/复核 Round2D 已有输出，Round2E 不新估计 D0
    lat <- spec %in% c('D1L', 'D1B')
    return(list(kind = if (lat) 'lms_latent' else 'linear', model = d_lines_r2e(zshape, if (lat) 'C' else 'none', ctrl, spec %in% c('D0B', 'D1B')),
                fac = c('IX', 'SX', 'IZ', 'SZ', 'IY', 'SY'), obs = c(OBS_XY, paste0('Z', 1:5)), use = c('x1-x5', 'y1-y5', 'z1-z5', ctrl),
                fixed_zero = if (spec %in% c('D0B', 'D1B')) 'SY' else character(0), define = NULL,
                key = if (lat) rbind(keyd, key_add('dc', 'SY', 'SXIZ')) else keyd))
  }
  stop('unregistered specification: ', spec)
}
analysis_r2e <- function(kind, points = 15, processors = 1, seed = 26101001) {
  if (kind == 'linear') return(paste0('TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=', processors, '; COVERAGE=.005; ITERATIONS=2000;'))
  c(paste0('TYPE=COMPLEX RANDOM; ESTIMATOR=MLR; PROCESSORS=', processors, ';'),
    paste0('ALGORITHM=INTEGRATION; INTEGRATION=', points, ';'),
    paste0('MCSEED=', seed, '; COVERAGE=.005; ITERATIONS=2000; MITERATIONS=4000;'))
}

# ---------------------------------------------------------------- SVALUES 跨规格拼接（E0→E1、E1→H4、D0→D1、自由→边界）
# 读取源输出 SVALUES 段；(1) 负的方差起点改为 min_var 并登记（从不继承非法终值）；(2) fixed_zero 因子删去方差起点并加 @0；
# (3) 追加新增语句（新增参数一律 *0 起点）。返回模型行与逐行登记表。
svalues_splice <- function(out_file, add = character(0), fixed_zero = character(0), min_var = 0.01) {
  L <- readLines(out_file, warn = FALSE, encoding = 'latin1'); sv <- svalues_block(L)
  if (is.null(sv)) stop('SVALUES section missing in ', out_file)
  log <- data.frame(line = sv, action = 'copied_start', stringsAsFactors = FALSE)
  var_re <- '^([A-Za-z][A-Za-z0-9_]*)\\*(-?[0-9.]+([EeDd][-+]?[0-9]+)?);$'
  for (i in seq_along(sv)) {
    if (!grepl(var_re, sv[i])) next
    nm <- sub(var_re, '\\1', sv[i]); v <- as.numeric(sub('[Dd]', 'E', sub(var_re, '\\2', sv[i])))
    if (toupper(nm) %in% toupper(fixed_zero)) { sv[i] <- NA; log$action[i] <- 'dropped_for_fixed_zero'; next }
    if (v < 0) { sv[i] <- paste0(nm, '*', min_var, ';'); log$action[i] <- paste0('negative_variance_start_replaced_by_', min_var) }
  }
  keep <- !is.na(sv); out <- sv[keep]
  fz <- if (length(fixed_zero)) paste0(tolower(fixed_zero), '@0;') else character(0)   # paste0(character(0), ...) 会返回 '@0;'
  have <- toupper(stmt_key(out)); dup <- add[toupper(stmt_key(add)) %in% have]
  if (length(dup)) log <- rbind(log, data.frame(line = dup, action = 'not_added_statement_already_in_source'))
  new <- c(add[!toupper(stmt_key(add)) %in% have], fz[!fz %in% out])
  if (length(new)) log <- rbind(log, data.frame(line = new, action = 'added_new_statement'))
  stopifnot(!any(grepl('@', new[!new %in% fz]) & !grepl('\\|', new[!new %in% fz])))   # 新增语句不固定参数
  list(model = c(out, new), log = log)
}
# 语句键：去掉标签、起点/固定值与分号，用于判断"同一参数语句"（如 'sy ON sxz*0.13 (dc);' → 'sy ON sxz'）。
stmt_key <- function(x) trimws(gsub('\\s+', ' ', sub('\\*.*$', '', sub('@.*$', '', sub('\\s*\\(.*\\)\\s*;?$', '', sub(';\\s*$', '', x))))))
# 拼接结构核对：目标规格的每个 ON/WITH 参数（区间展开、WITH 不分顺序）都出现在拼接后的模型中，且拼接模型不含规格之外的变量。
# 用途：防止起点源与目标规格结构不同（如控制集不同）时静默丢参数或引入未声明变量；不通过时改用规格默认起点并登记。
expand_vars <- function(tok) unlist(lapply(tok, function(t) { m <- regmatches(t, regexec('^([a-z]+)([0-9]+)-([a-z]+)?([0-9]+)$', t))[[1]]
  if (length(m)) paste0(m[2], as.integer(m[3]):as.integer(m[5])) else t }))
stmt_pairs <- function(lines) {
  out <- character(0)
  for (x in tolower(trimws(lines))) {
    x <- sub('\\s*\\([^)]*\\)\\s*;?\\s*$', '', sub(';\\s*$', '', x)); if (grepl('\\|', x)) next
    for (op in c(' on ', ' with ')) if (grepl(op, x, fixed = TRUE)) {
      p <- strsplit(x, op, fixed = TRUE)[[1]]; l <- expand_vars(strsplit(trimws(p[1]), '\\s+')[[1]])
      r <- expand_vars(sub('[*@].*$', '', strsplit(trimws(p[2]), '\\s+')[[1]]))
      g <- expand.grid(l = l, r = r, stringsAsFactors = FALSE)
      out <- c(out, if (op == ' on ') paste(g$l, 'on', g$r) else apply(g, 1, function(v) paste(sort(v), collapse = ' with ')))
    }
  }
  unique(out)
}
splice_check <- function(spliced, si) {
  missing <- setdiff(stmt_pairs(si$model), stmt_pairs(spliced))
  txt <- gsub('\\([^)]*\\)', ' ', gsub('[*@][^ ;\\]]*', ' ', tolower(spliced)))
  tok <- unique(unlist(regmatches(txt, gregexpr('[a-z][a-z0-9_]*', txt))))
  xw <- tolower(sub('^\\s*([A-Za-z0-9_]+)\\s*\\|.*$', '\\1', grep('XWITH', spliced, value = TRUE, ignore.case = TRUE)))
  allowed <- c(tolower(expand_vars(unlist(strsplit(si$use, '\\s+')))), tolower(si$fac), xw, 'on', 'with', 'by', 'xwith')
  foreign <- setdiff(tok, allowed)
  list(ok = !length(missing) && !length(foreign), missing = missing, foreign = foreign)
}
# 起点映射核对：源中每个参数语句在目标模型行中都有对应语句；返回缺失清单。
svalues_coverage <- function(src_out, model_lines) {
  sv <- svalues_block(readLines(src_out, warn = FALSE, encoding = 'latin1'))
  setdiff(toupper(stmt_key(sv)), toupper(stmt_key(model_lines)))
}

# ---------------------------------------------------------------- 测量层还原与几何（移植自Round2D 01_tools.R）
canonical_measurement <- function(m, fac, obs) {
  TH <- outer(obs, obs, Vectorize(function(r, c) mval(m, 'THETA', r, c))); dimnames(TH) <- list(obs, obs)
  L <- outer(obs, fac, Vectorize(function(r, c) mval(m, 'LAMBDA', r, c))); dimnames(L) <- list(obs, fac)
  promoted <- obs[vapply(obs, function(o) pnum(m, 'PSI', o, o) > 0, logical(1))]
  if (length(promoted)) {
    LP <- outer(obs, promoted, Vectorize(function(r, c) mval(m, 'LAMBDA', r, c)))
    BP <- outer(promoted, fac, Vectorize(function(r, c) mval(m, 'BETA', r, c)))
    PP <- outer(promoted, promoted, Vectorize(function(r, c) mval(m, 'PSI', r, c)))
    cross <- outer(promoted, fac, Vectorize(function(r, c) mval(m, 'PSI', r, c)))
    selfB <- outer(promoted, promoted, Vectorize(function(r, c) mval(m, 'BETA', r, c)))
    stopifnot(all(cross == 0), all(selfB == 0))
    L <- L + LP %*% BP; TH <- TH + LP %*% PP %*% t(LP)
  }
  list(THETA = TH, LAMBDA = L, promoted = promoted)
}
geometry_r2e <- function(m, si, zpoints = c(-1, 0, 1)) {
  fac <- si$fac; obs <- si$obs; fz <- si$fixed_zero; er <- length(fac) - length(fz)
  B <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'BETA', r, c))); dimnames(B) <- list(fac, fac)
  P <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'PSI', r, c))); dimnames(P) <- list(fac, fac)
  meas <- canonical_measurement(m, fac, obs); TH <- meas$THETA; L <- meas$LAMBDA
  ch <- list(PSI = mcheck(P, er), THETA = mcheck(TH)); mats <- list(B = B, PSI = P, THETA = TH, LAMBDA = L)
  if (si$kind == 'linear') {
    A <- solve(diag(length(fac)) - B); G <- A %*% P %*% t(A); S <- L %*% G %*% t(L) + TH
    ch$G <- mcheck(G, er); ch$SIGMA <- mcheck(S); mats$G <- G; mats$SIGMA <- S
  } else if (si$kind == 'lms_observed') {
    # 观测Z0（与G）条件下的协方差；SX系数含观测乘积。点位用真实支持点（含最小、最大值）。
    gcols <- if (!is.null(si$g)) 0:1 else 0
    for (z in zpoints) for (g in gcols) {
      BC <- B; BC['SY', 'SX'] <- BC['SY', 'SX'] + mval(m, 'BETA', 'SY', 'SXZ') * z +
        (if (!is.null(si$g)) mval(m, 'BETA', 'SY', 'SXG') * g + mval(m, 'BETA', 'SY', 'SXZG') * z * g else 0)
      A <- solve(diag(length(fac)) - BC); G <- A %*% P %*% t(A); S <- L %*% G %*% t(L) + TH
      nm <- sprintf('COND_Z%+.3f_G%d', z, g); ch[[nm]] <- mcheck(S); mats[[nm]] <- S
    }
  } else {                                     # lms_latent：乘积的高斯矩（控制=0），不另设乘积方差
    A <- solve(diag(length(fac)) - B); G0 <- A %*% P %*% t(A)
    alpha <- vapply(fac, function(f) mval(m, 'ALPHA', '1', f), numeric(1)); mu <- as.vector(A %*% alpha)
    a <- match('SX', fac); bb <- match('IZ', fac); t <- match('SY', fac); d <- mval(m, 'BETA', 'SY', 'SXIZ')
    covgp <- mu[a] * G0[, bb] + mu[bb] * G0[, a]
    vp <- G0[a, a] * G0[bb, bb] + G0[a, bb]^2 + mu[a]^2 * G0[bb, bb] + mu[bb]^2 * G0[a, a] + 2 * mu[a] * mu[bb] * G0[a, bb]
    e <- rep(0, length(mu)); e[t] <- d
    C <- G0 + outer(covgp, e) + outer(e, covgp) + vp * outer(e, e); S <- L %*% C %*% t(L) + TH
    ch$NONLINEAR_COV_C0 <- mcheck(C); ch$NONLINEAR_SIGMA_C0 <- mcheck(S); mats$NONLINEAR_COV_C0 <- C; mats$NONLINEAR_SIGMA_C0 <- S
  }
  ok <- all(vapply(names(ch), function(n) ch[[n]]$psd && (ch[[n]]$rank_ok || !(n %in% c('PSI', 'G'))), logical(1))) &&
    ch$PSI$rank_ok && ch$THETA$positive_definite && all(vapply(grep('SIGMA|COND_', names(ch), value = TRUE), function(n) ch[[n]]$positive_definite, logical(1)))
  list(checks = ch, matrices = mats, passed = ok, promoted = meas$promoted)
}
# 门槛：正常结束、无致命警告、无自由负方差、TECH3与SE一致且正定、几何合法；fixed_zero 规格允许 PSI 警告。
gate_r2e <- function(m, si, zpoints = c(-1, 0, 1)) {
  fl <- out_flags(m$lines); neg <- free_negative(m)
  vc <- tryCatch({ stopifnot(all(is.finite(m$V)), all(is.finite(m$par$se)), all(m$par$se > 0))
    e <- eigen(m$V / outer(sqrt(diag(m$V)), sqrt(diag(m$V))), symmetric = TRUE, only.values = TRUE)$values
    list(ok = min(e) > 1e-10 && all(abs(diag(m$V) - m$par$se^2) <= 1e-6 + 1e-5 * m$par$se^2), minimum = min(e)) },
    error = function(e) list(ok = FALSE, error = conditionMessage(e)))
  geo <- tryCatch(geometry_r2e(m, si, zpoints), error = function(e) list(passed = FALSE, error = conditionMessage(e)))
  psi_ok <- !fl$psi_warning || length(si$fixed_zero) > 0
  list(passed = fl$normal && !fl$fatal && !length(neg) && vc$ok && isTRUE(geo$passed) && psi_ok && !fl$theta_warning,
       flags = fl, negative = neg, vcov = vc, geometry = geo)
}
# 边界分类（预登记）：唯一违规为 PSI:SY 为负、且 est/SE > −1.96、其余全部合格（把SY方差置0后几何合法）→ BOUNDARY_SY。
classify_member <- function(m, si, gate, zpoints = c(-1, 0, 1)) {
  if (isTRUE(gate$passed)) return(list(status = 'USABLE', sy = NA_real_, sy_se = NA_real_, sy_z = NA_real_))
  p <- m$par[m$par$matrix == 'psi' & m$par$row == 'SY' & m$par$column == 'SY', ]
  sy <- if (nrow(p)) p$estimate else NA_real_; se <- if (nrow(p)) p$se else NA_real_; z <- sy / se
  res <- list(status = 'INADMISSIBLE', sy = sy, sy_se = se, sy_z = z)
  if (!identical(gate$negative, 'psi:SY') || !is.finite(z) || z <= -1.96) return(res)
  if (!gate$flags$normal || gate$flags$fatal || gate$flags$theta_warning || !isTRUE(gate$vcov$ok)) return(res)
  m0 <- m; j <- .cell(m0$values, 'PSI', 'SY', 'SY'); m0$values$value[j] <- 0
  si0 <- si; si0$fixed_zero <- unique(c(si$fixed_zero, 'SY'))
  g0 <- tryCatch(geometry_r2e(m0, si0, zpoints), error = function(e) list(passed = FALSE))
  if (isTRUE(g0$passed)) res$status <- 'BOUNDARY_SY'
  res
}
key_paths_r2e <- function(m, key) do.call(rbind, lapply(seq_len(nrow(key)), function(i) {
  k <- key[i, ]; id <- pnum(m, 'BETA', k$row, k$column); if (id == 0) stop('missing path ', k$label)
  p <- m$par[m$par$parameter == id, ]; stopifnot(nrow(p) == 1, is.finite(p$estimate), is.finite(p$se))
  data.frame(label = k$label, parameter = id, row = k$row, column = k$column, estimate = p$estimate, se = p$se)
}))
# 数值一致性：start（LL≤.01，路径≤max(.001,.01SE)，SE相对≤5%）；integration（路径≤.05SE，SE相对≤5%）；processors（同start）。
compare_numeric <- function(a, b, mode = c('start', 'integration', 'processors'), th = list(start_LL = .01, start_path_abs = .001, start_path_se = .01, integration_path_se = .05, se_rel = .05)) {
  mode <- match.arg(mode)
  if (is.null(a) || is.null(b) || is.null(a$key) || is.null(b$key)) return(list(passed = FALSE, mode = mode, reason = 'comparison member absent or without key paths'))
  stopifnot(setequal(a$key$label, b$key$label)); bk <- b$key[match(a$key$label, b$key$label), ]
  d <- abs(a$key$estimate - bk$estimate); se <- bk$se
  lim <- if (mode == 'integration') th$integration_path_se * se else pmax(th$start_path_abs, th$start_path_se * se)
  ll <- abs(as.numeric(a$receipt$LL) - as.numeric(b$receipt$LL)); sd <- abs(a$key$se - bk$se) / bk$se
  ok <- all(is.finite(d)) && all(d <= lim) && all(sd <= th$se_rel) && (mode == 'integration' || (is.finite(ll) && ll <= th$start_LL))
  list(passed = ok, mode = mode, reference = a$receipt$id, candidate = b$receipt$id, delta_LL = ll,
       max_path_over_SE = max(d / se), max_SE_relative = max(sd), paths = data.frame(label = a$key$label, difference = d, tolerance = lim))
}

# ---------------------------------------------------------------- 真实支持点（只用于呈现条件斜率；不改变连续交互）
# z：该分支 2012 年已定向标准化 Z0（全样本，MI间相同）；zraw0：原始差值/SD=0 对应的标准分。
support_points <- function(z, zraw0, min_share = .05, tol = 1e-9) {
  z <- z[is.finite(z)]; n <- length(z); at0 <- abs(z - zraw0) < tol
  pts <- data.frame(point = 'raw_zero', z = zraw0, rule = 'raw difference/SD equals 0', n_at_or_side = sum(at0), share = mean(at0))
  for (side in c('below', 'above')) {
    s <- if (side == 'below') z[z < zraw0 - tol] else z[z > zraw0 + tol]
    if (length(s) / n >= min_share)
      pts <- rbind(pts, data.frame(point = paste0('median_', side, '_zero'), z = stats::median(s),
                                   rule = paste('median of non-zero values', side, 'the raw-zero point'), n_at_or_side = length(s), share = length(s) / n))
  }
  q <- stats::quantile(z, c(.10, .90), type = 7, names = FALSE)
  for (i in 1:2) if (abs(q[i] - zraw0) > tol && !any(abs(pts$z - q[i]) < tol))
    pts <- rbind(pts, data.frame(point = c('P10', 'P90')[i], z = q[i], rule = 'sample quantile (secondary)', n_at_or_side = NA, share = NA))
  pts$min_z <- min(z); pts$max_z <- max(z); pts$N <- n
  pts
}
winsorize <- function(z, p = c(.01, .99)) { q <- stats::quantile(z, p, type = 7, na.rm = TRUE, names = FALSE); pmin(pmax(z, q[1]), q[2]) }

# ---------------------------------------------------------------- H4 方向判定（预登记，结果未知时修订）
# Z 定向：数值越大越"不和谐"。X=亲近度，Y=抑郁，假定条件斜率 b<0、Z主效应 g>0。
# 同一交互系数：δ>0 ↔ "消极关系的弱化效应"（H2.1，s=+1）；δ<0 ↔ "积极关系的缓解效应"（H2.2，s=−1）。
# δ0=资源0组，δ1=δ0+δG=资源1组。lo/hi 为九项对比的Bonferroni同时95%区间。H4.2a/H4.2b 文本同时含两种成分，故按成分报告。
h4_decide <- function(d0, d1, dG) {
  sgn <- function(x) if (x$lo > 0) 1L else if (x$hi < 0) -1L else 0L
  s0 <- sgn(d0); s1 <- sgn(d1); sG <- sgn(dG)
  comp <- function(s) if (s > 0) '弱化成分(δ>0)' else '缓解成分(δ<0)'
  tag <- function(s) if (s > 0) 'WEAKENING' else 'BUFFERING'
  if (s0 != 0 && s1 != 0 && s0 != s1) return(list(label = 'CROSSOVER', text = '两组调节方向相反（交叉）；H4.2a/H4.2b 均未覆盖', component = NA))
  if (sG == 0) return(list(label = 'DIFFERENCE_UNDETERMINED', text = '组间差异δG的同时区间含0；不作H4.2a/b方向判定', component = NA))
  # H4.2b：资源1组在成分s上的调节已确立，且差异朝同一方向；资源0组不显著反向
  if (s1 != 0 && sG == s1 && s0 != -s1) return(list(label = paste0('H4.2b_', tag(s1)), text = paste0('资源较好组', comp(s1), '更强；另一成分未获支持'), component = comp(s1)))
  # H4.2a：资源0组在成分s上的调节已确立，差异与之反向（资源1组较弱）；资源1组不显著反向
  if (s0 != 0 && sG == -s0 && s1 != -s0) return(list(label = paste0('H4.2a_', tag(s0)), text = paste0('资源较好组', comp(s0), '更弱；另一成分未获支持'), component = comp(s0)))
  list(label = 'DIFFERENCE_WITHOUT_COMPONENT', text = 'δG同时区间不含0，但无法确定差异属于哪一成分（两组调节方向均未确立）', component = NA)
}

# ---------------------------------------------------------------- Z0 对潜在 IZ 的信度（由Round2D已保存D0输出计算，只作解释背景）
z0_reliability <- function(m) {
  fac <- c('IX', 'SX', 'IZ', 'SZ', 'IY', 'SY')
  B <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'BETA', r, c))); P <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'PSI', r, c)))
  G <- solve(diag(6) - B) %*% P %*% t(solve(diag(6) - B)); v <- G[3, 3]; th <- mval(m, 'THETA', 'Z1', 'Z1')
  c(var_IZ_given_controls = v, theta_z1 = th, reliability_z1_for_IZ = v / (v + th))
}
