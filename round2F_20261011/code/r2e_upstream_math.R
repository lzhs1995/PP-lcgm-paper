# Round2D 纯函数工具：语法生成、数据构建、Mplus原始输出独立读取、几何、门槛、Rubin与对比合并。
# 本文件不调用Mplus、不读写项目目录；可在任何R(>=4.1)中source，云端自测见 r2d_selftest.R。

R2D_CONTROLS <- c('sex12','edu12','urban12','prov122','prov123','cdn12','cdar12','cdsc121','cdsc122','minor12',
                  'ageg12','pinc12','pinc212','cores12','heal121','heal123','marr12','eco122','eco123','hwc122',
                  'hwc123','hukou12','adl12','finc12')
R2D_YEARS <- c(12, 16, 18, 20, 22)
R2D_TIME <- c(0, .4, .6, .8, 1)                       # 十年单位，与Round2C一致
R2D_Y_FROZEN <- c(mean = 13.5754428833232, sd = 4.25923864592045)   # Round2C input_scale_reproducible_check.json
# 四个家内差异Z：原始列前缀（每期后缀12…22）、2012年应有观测数（Round2B observed_longitudinal_descriptives.csv）、
# 方向（+1：数值越大越"不利"；−1：数值越小越"不利"，与假设1.2—1.4及2.1的"消极关系"一致）、历史增长形状。
R2D_Z <- list(
  SD     = list(raw = 'wfd_s',  n2012 = 3274L, orient = +1, shape = 'free',   label = '标准差/均值'),
  SEXGAP = list(raw = 'wfd_d',  n2012 = 2339L, orient = -1, shape = 'linear', label = '性别差(儿-女)/均值'),
  OLDEST = list(raw = 'wfd_d1', n2012 = 3159L, orient = -1, shape = 'linear', label = '排行差(老大-其他)/均值'),
  SONGAP = list(raw = 'wfd_d4', n2012 = 2894L, orient = -1, shape = 'linear', label = '排行差(长子-其他)/均值'))
# H4.2b资源变量：模型列col（学历、城乡已在24控制中，直接用c2、c3，避免与控制列完全共线；收入另加ginc）。
# 须为0/1；1是否代表"资源较好"由astra按CFPS编码手册在Z_CONTRACT里确认（better_is_one）。
R2D_G <- list(EDU   = list(col = 'c2',   src = 'edu12',   in_controls = TRUE),
              URBAN = list(col = 'c3',   src = 'urban12', in_controls = TRUE),
              INC   = list(col = 'ginc', src = 'pinc412', in_controls = FALSE))

# ---------------------------------------------------------------- 文本工具
wrap90 <- function(s, indent = '  ', width = 88) {
  out <- character(0)
  for (line in unlist(strsplit(s, '\n', fixed = TRUE))) {
    if (nchar(line) <= width) { out <- c(out, line); next }
    words <- strsplit(line, ' ', fixed = TRUE)[[1]]; cur <- ''
    for (w in words) {
      cand <- if (nchar(cur)) paste(cur, w) else w
      if (nchar(cand) > width && nchar(cur)) { out <- c(out, cur); cur <- paste0(indent, w) } else cur <- cand
    }
    out <- c(out, cur)
  }
  stopifnot(all(nchar(out) <= 90))
  out
}
growth_line <- function(f1, f2, p, shape) {
  op <- if (shape == 'linear') rep('@', 5) else c('@', '*', '*', '*', '@')
  paste0(f1, ' ', f2, ' | ', paste0(p, 1:5, op, R2D_TIME, collapse = ' '), ' ;')
}

# ---------------------------------------------------------------- 模型语法
# SW父模型（Round2C冻结规格）。yshape='free' 为YFREE敏感性；sy_fix 为SW剖面固定值。
sw_lines <- function(yshape = 'linear', sy_fix = NULL, samewave = TRUE, ctrl = 'c1-c24') {
  m <- c(growth_line('ix', 'sx', 'x', 'free'), growth_line('iy', 'sy', 'y', yshape),
         'iy ON ix (bii);', 'sy ON ix (bis);', 'sy ON sx (bss);', 'sy ON iy (bsyiy);', 'ix WITH sx;',
         paste0('ix sx iy sy ON ', ctrl, ';'), 'sx WITH iy;')
  if (samewave) m <- c(m, paste0('x', 1:5, ' WITH y', 1:5, ';'))
  if (!is.null(sy_fix)) m <- c(m, paste0('sy@', format(sy_fix, scientific = FALSE, trim = TRUE), ';'))
  m
}
# 三过程（D线）：在SW上加入Z完整增长过程。interaction: none | C (SX×IZ→SY) | L (IX×IZ→IY)
d_lines <- function(zshape = 'linear', interaction = 'none', ctrl = 'c1-c24') {
  stopifnot(interaction %in% c('none', 'C', 'L', 'CL'))
  m <- c(growth_line('ix', 'sx', 'x', 'free'), growth_line('iy', 'sy', 'y', 'linear'), growth_line('iz', 'sz', 'z', zshape),
         'iy ON ix (bii);', 'iy ON iz (gii);',
         'sy ON ix (bis);', 'sy ON sx (bss);', 'sy ON iy (bsyiy);', 'sy ON iz (gis);', 'sy ON sz (gss);',
         paste0('ix sx iz sz iy sy ON ', ctrl, ';'),
         'ix WITH sx iz sz;', 'sx WITH iz sz;', 'iz WITH sz;', 'sx WITH iy;', 'sz WITH iy;',
         paste0('x', 1:5, ' WITH y', 1:5, ';'), paste0('x', 1:5, ' WITH z', 1:5, ';'), paste0('y', 1:5, ' WITH z', 1:5, ';'))
  if (interaction %in% c('C', 'CL')) m <- c(m, 'sxiz | sx XWITH iz;', 'sy ON sxiz (dc);')
  if (interaction %in% c('L', 'CL')) m <- c(m, 'ixiz | ix XWITH iz;', 'iy ON ixiz (dl);', 'sy ON ixiz (dx);')
  m
}
# 观测基期Z0（E线）：SW + 观测2012 Z0。interaction: none | LC（IX×Z0→IY、IX×Z0→SY 与 SX×Z0→SY 同一模型，积分维数2）
e_lines <- function(interaction = 'none', ctrl = 'c1-c24', yshape = 'linear') {
  stopifnot(interaction %in% c('none', 'LC'))
  m <- c(sw_lines(yshape = yshape, ctrl = ctrl), 'ix sx ON z0;', 'iy ON z0 (gi0);', 'sy ON z0 (gs0);',
         'x1 y1 ON z0;')                                   # 同期同源：2012年X、Y指标与Z0的测量层关联（对应D线x1/y1 WITH z1）
  if (interaction == 'LC') m <- c(m, 'ixz | ix XWITH z0;', 'iy ON ixz (dl);', 'sy ON ixz (dx);', 'sxz | sx XWITH z0;', 'sy ON sxz (dc);')
  m
}
# H4.2b（E线三阶）：g为0/1资源变量列名，zg=z0*g 在DEFINE中生成。g已在控制集中时 g_in_controls=TRUE。
e2_lines <- function(g, g_in_controls, ctrl = 'c1-c24') {
  m <- c(sw_lines(ctrl = ctrl), 'ix sx ON z0 zg;', 'iy ON z0 zg;', 'sy ON z0 zg;', 'x1 y1 ON z0;')
  if (!g_in_controls) m <- c(m, paste('ix sx iy sy ON', g, ';'))
  c(m, paste('ixz | ix XWITH z0;'), paste('ixg | ix XWITH', paste0(g, ';')), 'ixzg | ix XWITH zg;',
    paste('sxz | sx XWITH z0;'), paste('sxg | sx XWITH', paste0(g, ';')), 'sxzg | sx XWITH zg;',
    'iy ON ixz (dl);', 'iy ON ixg;', 'iy ON ixzg (dlg);', 'sy ON ixz (dx);', 'sy ON ixg;', 'sy ON ixzg (dxg);',
    'sy ON sxz (dc);', 'sy ON sxg;', 'sy ON sxzg (dcg);')
}
e2_constraint <- function() c('NEW(dl_g1 dx_g1 dc_g1);', 'dl_g1 = dl + dlg;', 'dx_g1 = dx + dxg;', 'dc_g1 = dc + dcg;')
# Z单变量形状核查（无条件、全部可用观测）
zuni_lines <- function(shape) c(growth_line('iz', 'sz', 'z', shape), 'iz WITH sz;')

# 有效控制列（按序号）压缩为Mplus列表，如 c(1:7,10:24) -> 'c1-c7 c10-c24'
ctrl_term <- function(idx) {
  idx <- sort(unique(idx)); br <- c(0, which(diff(idx) != 1), length(idx))
  paste(vapply(seq_len(length(br) - 1), function(i) { a <- idx[br[i] + 1]; b <- idx[br[i + 1]]
    if (a == b) paste0('c', a) else paste0('c', a, '-c', b) }, ''), collapse = ' ')
}
# 确定性的可估计控制列：在每份插补的分析样本内，零方差列删除；再按列序逐一加入，不增加秩的列删除（精确线性依赖）。
valid_controls <- function(mats) {
  keep <- rep(TRUE, 24)
  for (C in mats) keep <- keep & apply(C, 2, function(v) stats::var(v) > 0)
  idx <- which(keep); out <- integer(0)
  for (j in idx) { cand <- c(out, j)
    if (all(vapply(mats, function(C) qr(cbind(1, C[, cand, drop = FALSE]))$rank == length(cand) + 1, logical(1)))) out <- cand }
  out
}
R2D_NAMES <- c('fid', paste0('x', 1:5), paste0('y', 1:5), paste0('z', 1:5), 'z0', 'gedu', 'gurb', 'ginc', paste0('c', 1:24))
analysis_lines <- function(kind = c('linear', 'lms'), integration = 15, processors = 1, iterations = 1000) {
  kind <- match.arg(kind)
  if (kind == 'linear') return(paste0('TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=', processors, '; COVERAGE=.005; ITERATIONS=', iterations, ';'))
  c(paste0('TYPE=COMPLEX RANDOM; ESTIMATOR=MLR; PROCESSORS=', processors, ';'),
    paste0('ALGORITHM=INTEGRATION; INTEGRATION=', integration, '; COVERAGE=.005;'),
    paste0('ITERATIONS=', iterations, '; MITERATIONS=2000;'))
}
# 完整INP文本；usev为USEVARIABLES（不含DEFINE变量时define=NULL）。
inp_text <- function(title, usev, analysis, model, define = NULL, constraint = NULL, kind = 'linear', svalues = TRUE) {
  out <- if (kind == 'linear') 'TECH1 TECH3 TECH4 SAMPSTAT RESIDUAL CINTERVAL' else 'TECH1 TECH3 TECH8 CINTERVAL'
  if (svalues) out <- paste(out, 'SVALUES')
  s <- c('TITLE:', title, 'DATA:', 'FILE = "data.dat";', 'VARIABLE:',
         wrap90(paste0('NAMES = ', paste(R2D_NAMES, collapse = ' '), ';')), ' MISSING=.;',
         wrap90(paste0(' CLUSTER=fid; USEVARIABLES=', paste(usev, collapse = ' '), ';')))
  if (!is.null(define)) s <- c(s, 'DEFINE:', define)
  s <- c(s, 'ANALYSIS:', analysis, 'MODEL:', unlist(lapply(model, wrap90)))
  if (!is.null(constraint)) s <- c(s, 'MODEL CONSTRAINT:', constraint)
  s <- c(s, 'OUTPUT:', paste0(out, ';'), 'SAVEDATA:', 'TECH3=tech3.dat; RESULTS=estimates.dat;')
  stopifnot(all(nchar(s) <= 90))
  s
}
usev_for <- function(spec, g = NULL, ctrl = 'c1-c24') {
  base <- c('x1-x5', 'y1-y5')
  switch(spec,
    SW = c(base, ctrl), YFREE = c(base, ctrl), SWPROF = c(base, ctrl),
    D0 = , D1C = , D1L = , D1CL = c(base, 'z1-z5', ctrl),
    E0 = , E1 = c(base, 'z0', ctrl),
    E2 = c(base, 'z0', if (identical(g, 'ginc')) 'ginc', ctrl, 'zg'),
    ZUNI = 'z1-z5', stop('unknown spec ', spec))
}

# ---------------------------------------------------------------- 数据构建（只在astra本机对私有RDS运行）
z_series <- function(d, zkey) {
  zs <- R2D_Z[[zkey]]
  raw <- as.matrix(d[, paste0(zs$raw, R2D_YEARS)]); mean_x <- as.matrix(d[, paste0('wfd_m', R2D_YEARS)])
  stopifnot(all(mean_x[is.finite(mean_x)] >= 1))           # 原始均值1—5分，分母不为0
  100 * raw / mean_x                                         # (差异/均值)*100%，与正文表3.2一致
}
build_member <- function(d, zkey, ref = NULL) {
  stopifnot(nrow(d) == 3274L, all(R2D_CONTROLS %in% names(d)))
  x <- as.matrix(d[, paste0('wfdms', R2D_YEARS)])
  y <- (as.matrix(d[, paste0('ces8', R2D_YEARS)]) - R2D_Y_FROZEN[['mean']]) / R2D_Y_FROZEN[['sd']]
  zr <- z_series(d, zkey)
  elig <- is.finite(zr[, 1])
  if (is.null(ref)) ref <- c(mean = mean(zr[elig, 1]), sd = stats::sd(zr[elig, 1]))
  z <- R2D_Z[[zkey]]$orient * (zr - ref[['mean']]) / ref[['sd']]   # 基期标准化后按"不利方向"定向
  g <- function(v) if (v %in% names(d)) as.numeric(d[[v]]) else rep(NA_real_, nrow(d))
  dat <- data.frame(fid = d$fid, x, y, z, z0 = z[, 1], gedu = g('edu12'), gurb = g('urban12'), ginc = g('pinc412'),
                    as.matrix(d[, R2D_CONTROLS]), check.names = FALSE)
  names(dat) <- R2D_NAMES
  list(data = dat, eligible = elig, ref = ref)
}
read_dat <- function(path, names = NULL) {
  a <- utils::read.table(path, na.strings = '.', header = FALSE)
  if (!is.null(names)) names(a) <- names
  a
}
# 与Round2C已用data.dat（fid x1-x5 y1-y5 c1-c24）逐格比较：保证新数据与SW父模型同源。
compare_with_r2c <- function(dat, r2c_dat, tol = 1e-6) {
  cols <- c('fid', paste0('x', 1:5), paste0('y', 1:5), paste0('c', 1:24))
  stopifnot(ncol(r2c_dat) == 35L, nrow(r2c_dat) == nrow(dat))
  a <- as.matrix(dat[, cols]); b <- as.matrix(r2c_dat); colnames(b) <- cols
  same_na <- identical(is.na(a), is.na(b))
  diff <- max(abs(a - b), na.rm = TRUE)
  list(same_missing_pattern = same_na, max_abs_difference = diff, passed = same_na && diff < tol)
}
write_dat <- function(dat, path) {
  m <- as.matrix(dat); txt <- matrix(formatC(m, digits = 12, format = 'g'), nrow(m)); txt[is.na(m)] <- '.'
  writeLines(apply(txt, 1, paste, collapse = ' '), path, useBytes = TRUE)
  back <- read_dat(path); bm <- as.matrix(back)
  stopifnot(identical(unname(is.na(bm)), unname(is.na(m))), max(abs(bm - m), na.rm = TRUE) < 1e-8)
  invisible(path)
}

# ---------------------------------------------------------------- Mplus原始输出的独立读取（不依赖MplusAutomation）
.mats <- c('NU', 'LAMBDA', 'THETA', 'ALPHA', 'BETA', 'PSI', 'GAMMA', 'TAU', 'KAPPA')
tech1_blocks <- function(lines, numeric = FALSE) {
  out <- list(); k <- 1L; n <- length(lines)
  while (k <= n) {
    nm <- trimws(lines[k])
    if (nm %in% .mats && k + 2 <= n && grepl('^[_ ]+$', lines[k + 2]) && nchar(trimws(lines[k + 2]))) {
      cols <- strsplit(trimws(lines[k + 1]), '\\s+')[[1]]; k <- k + 3L
      while (k <= n && nchar(trimws(lines[k])) && !(trimws(lines[k]) %in% .mats)) {
        tk <- strsplit(trimws(lines[k]), '\\s+')[[1]]
        if (nm %in% c('NU', 'ALPHA', 'TAU', 'KAPPA') && !grepl('^[A-Za-z]', tk[1])) { row <- '1'; vals <- tk } else { row <- tk[1]; vals <- tk[-1] }
        for (j in seq_along(vals)) out[[length(out) + 1]] <- data.frame(matrix = nm, row = row, column = cols[j],
                                                                         value = if (numeric) as.numeric(sub('D', 'E', vals[j])) else as.integer(vals[j]))
        k <- k + 1L
      }
    } else k <- k + 1L
  }
  do.call(rbind, out)
}
read_mplus_raw <- function(dir, out = 'model.out', est = 'estimates.dat', t3 = 'tech3.dat') {
  L <- readLines(file.path(dir, out), warn = FALSE, encoding = 'latin1')
  a <- which(trimws(L) == 'PARAMETER SPECIFICATION'); b <- which(trimws(L) == 'STARTING VALUES')
  stopifnot(length(a) >= 1, length(b) >= 1, b[1] > a[1])
  spec <- tech1_blocks(L[(a[1] + 1):(b[1] - 1)])
  nxt <- which(grepl('^TECHNICAL [0-9]+ OUTPUT|^RESULTS SAVING INFORMATION|^SAVEDATA INFORMATION', L) & seq_along(L) > b[1])[1]
  start <- tech1_blocks(L[(b[1] + 1):(nxt - 1)], numeric = TRUE)
  free <- spec[spec$value > 0, ]; P <- max(free$value)
  stopifnot(identical(sort(unique(free$value)), seq_len(P)))
  v <- scan(file.path(dir, est), quiet = TRUE); stopifnot(length(v) >= 2 * P)
  t <- scan(file.path(dir, t3), quiet = TRUE); stopifnot(length(t) == P * (P + 1) / 2)
  V <- matrix(0, P, P); V[upper.tri(V, diag = TRUE)] <- t; V <- V + t(V) - diag(diag(V))   # 行优先下三角=列优先上三角
  first <- free[!duplicated(free$value), ]; first <- first[order(first$value), ]
  par <- data.frame(parameter = first$value, matrix = tolower(first$matrix), row = first$row, column = first$column,
                    estimate = v[seq_len(P)], se = v[P + seq_len(P)])
  # 结果文件中参数和SE之后的统计量：按输出"Order of data"清单命名
  o <- which(trimws(L) == 'Order of data'); extra <- list()
  if (length(o)) {
    lab <- trimws(L[(o + 1):(o + 40)]); lab <- lab[nchar(lab) > 0]
    lab <- lab[!grepl('^\\(saved|^Parameter estimates|^Standard errors|^Save file', lab)]
    lab <- lab[seq_len(min(length(lab), which(grepl('^Save file', trimws(L[(o + 1):(o + 40)])))[1] - 1))]
    rest <- v[-seq_len(2 * P)]
    for (i in seq_len(min(length(rest), length(lab)))) extra[[lab[i]]] <- rest[i]
  }
  vals <- start; for (i in seq_len(nrow(free))) {
    j <- which(vals$matrix == free$matrix[i] & vals$row == free$row[i] & vals$column == free$column[i])
    vals$value[j] <- v[free$value[i]]
  }
  list(par = par, V = V, P = P, spec = spec, values = vals, extra = extra,
       se_tech3_max_diff = max(abs(sqrt(diag(V)) - par$se)), lines = L)
}
# 对称矩阵（PSI、THETA）TECH1只列下三角，可双向查找；BETA、LAMBDA等有方向，行=结果、列=预测。
.cell <- function(x, mat, r, c) {
  hit <- x$matrix == mat & x$row == r & x$column == c
  if (mat %in% c('PSI', 'THETA')) hit <- hit | (x$matrix == mat & x$row == c & x$column == r)
  hit
}
mval <- function(m, mat, r, c) {
  z <- m$values[.cell(m$values, mat, r, c), 'value']
  if (length(z)) z[1] else 0
}
pnum <- function(m, mat, r, c) {
  x <- m$spec; z <- x[.cell(x, mat, r, c) & x$value > 0, 'value']
  if (length(z)) z[1] else 0L
}
out_flags <- function(L) {
  flat <- gsub('[[:space:]]+', ' ', paste(L, collapse = ' '))
  list(normal = grepl('THE MODEL ESTIMATION TERMINATED NORMALLY', flat, fixed = TRUE),
       fatal = grepl('SADDLE POINT|STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED|NON-POSITIVE DEFINITE FIRST-ORDER DERIVATIVE|NOT TRUSTWORTHY|DID NOT CONVERGE|NO CONVERGENCE', flat),
       psi_warning = grepl('LATENT VARIABLE COVARIANCE MATRIX \\(PSI\\) IS NOT POSITIVE', flat),
       theta_warning = grepl('RESIDUAL COVARIANCE MATRIX \\(THETA\\) IS NOT POSITIVE', flat),
       warnings = unique(trimws(L[grepl('WARNING|PROBLEM|NOT POSITIVE|SADDLE|NOT TRUSTWORTHY', L)])))
}

# ---------------------------------------------------------------- 几何与门槛
mcheck <- function(m, expected_rank = nrow(m), tol = 1e-7) {      # 与astra matrix_check3同一标准化规则
  stopifnot(is.matrix(m), all(is.finite(m)), max(abs(m - t(m))) < 1e-8)
  s <- sqrt(abs(diag(m))); s[s < 1e-10] <- 1; a <- m / outer(s, s)
  ev <- eigen((a + t(a)) / 2, symmetric = TRUE, only.values = TRUE)$values; rank <- sum(ev > tol)
  list(min_eigen = min(ev), rank = rank, expected_rank = expected_rank, psd = min(ev) >= -tol, rank_ok = rank == expected_rank,
       positive_definite = min(ev) > tol)
}
# 线性部分几何。fac=增长因子；obs=指标；fixed_zero=预定固定为0的因子方差（如剖面tau=0）。
geometry_linear <- function(m, fac, obs, fixed_zero = character(0)) {
  B <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'BETA', r, c)))
  P <- outer(fac, fac, Vectorize(function(r, c) mval(m, 'PSI', r, c)))
  dimnames(B) <- dimnames(P) <- list(fac, fac)
  A <- solve(diag(length(fac)) - B); G <- A %*% P %*% t(A); dimnames(G) <- list(fac, fac)
  TH <- outer(obs, obs, Vectorize(function(r, c) mval(m, 'THETA', r, c))); dimnames(TH) <- list(obs, obs)
  LAM <- outer(obs, fac, Vectorize(function(r, c) mval(m, 'LAMBDA', r, c)))
  S <- LAM %*% G %*% t(LAM) + TH
  er <- length(fac) - length(fixed_zero)
  ch <- list(PSI = mcheck(P, er), G = mcheck(G, er), THETA = mcheck(TH), SIGMA = mcheck(S))
  list(B = B, PSI = P, G = G, THETA = TH, LAMBDA = LAM, SIGMA = S, checks = ch,
       passed = all(vapply(ch, function(q) q$psd && q$rank_ok, logical(1))) && ch$THETA$positive_definite && ch$SIGMA$positive_definite)
}
free_negative <- function(m) {
  p <- m$par; v <- p[p$matrix %in% c('psi', 'theta') & p$row == p$column, ]
  paste(v$matrix[v$estimate < 0], v$row[v$estimate < 0], sep = ':')
}
# 门槛：线性模型要求完整几何；LMS模型只检查线性组成部分（乘积不是独立正态因子，不套用线性G/SIGMA）。
gate_model <- function(m, kind, fac, obs, fixed_zero = character(0)) {
  fl <- out_flags(m$lines); neg <- free_negative(m)
  ev <- eigen(m$V / outer(sqrt(diag(m$V)), sqrt(diag(m$V))), symmetric = TRUE, only.values = TRUE)$values
  vcov_ok <- min(ev) > 1e-10 && m$se_tech3_max_diff < max(1e-5, max(m$par$se^2) * 1e-4) && all(m$par$se > 0)
  geo <- tryCatch(geometry_linear(m, fac, obs, fixed_zero), error = function(e) NULL)
  geo_ok <- if (kind == 'linear') !is.null(geo) && geo$passed else
    !is.null(geo) && geo$checks$PSI$psd && geo$checks$PSI$rank_ok && geo$checks$THETA$positive_definite
  passed <- fl$normal && !fl$fatal && !length(neg) && vcov_ok && geo_ok && !(fl$psi_warning && !length(fixed_zero)) && !fl$theta_warning
  list(passed = passed, normal = fl$normal, fatal = fl$fatal, negative = neg, vcov_ok = vcov_ok, geometry_ok = geo_ok,
       warnings = fl$warnings, geometry = geo)
}

# ---------------------------------------------------------------- SVALUES 起始值拼接（D0→D1，E0→E1）
svalues_block <- function(L) {
  a <- grep('MODEL COMMAND WITH FINAL ESTIMATES USED AS STARTING VALUES', L)
  if (!length(a)) return(NULL)
  out <- character(0); k <- a[1] + 1L
  while (k <= length(L)) {
    line <- L[k]
    if (nchar(trimws(line)) && !grepl('^\\s', line)) break       # 下一节标题顶格
    if (nchar(trimws(line))) out <- c(out, trimws(line))
    k <- k + 1L
  }
  if (!length(out) || !all(grepl(';\\s*$', out))) return(NULL)
  out
}

# ---------------------------------------------------------------- Rubin合并与线性对比
rubin_pool <- function(Q, U, nu_com = Inf) {
  Q <- as.matrix(Q); m <- nrow(Q); p <- ncol(Q); stopifnot(m >= 2, length(U) == m)
  W <- Reduce('+', U) / m; B <- if (m > 1) stats::cov(Q) else matrix(0, p, p); T <- W + (1 + 1 / m) * B
  est <- colMeans(Q); se <- sqrt(diag(T)); r <- (1 + 1 / m) * diag(B) / diag(W); lam <- (1 + 1 / m) * diag(B) / diag(T)
  df_old <- ifelse(r > 0, (m - 1) * (1 + 1 / r)^2, Inf)
  df_obs <- if (is.finite(nu_com)) (nu_com + 1) / (nu_com + 3) * nu_com * (1 - lam) else Inf
  df <- if (is.finite(nu_com)) 1 / (1 / df_old + 1 / df_obs) else df_old          # Barnard–Rubin
  crit <- stats::qt(.975, df)
  list(table = data.frame(estimate = est, se = se, df = df, lower = est - crit * se, upper = est + crit * se,
                          p = 2 * stats::pt(-abs(est / se), df), lambda = lam, MCSE_over_SE = sqrt(diag(B) / m) / se),
       W = W, B = B, T = T)
}
# a为系数向量（与Q列对齐）；返回对比a'β的合并结果。与对T做二次型等价，用作交叉核对。
pool_contrast <- function(Q, U, a, nu_com = Inf) {
  q <- as.matrix(Q) %*% a; u <- lapply(U, function(v) matrix(t(a) %*% v %*% a, 1, 1))
  rubin_pool(q, u, nu_com)$table
}
holm <- function(p) stats::p.adjust(p, 'holm')
mde80 <- function(se) 2.8 * se        # 双侧α=.05、80%把握度的最小可检出效应（正态近似）
# MLR缩放差异检验（Satorra–Bentler 2001），L0为受限模型
sb_test <- function(L0, c0, p0, L1, c1, p1) {
  cd <- (p0 * c0 - p1 * c1) / (p0 - p1); TRd <- -2 * (L0 - L1) / cd; df <- abs(p1 - p0)
  data.frame(cd = cd, TRd = TRd, df = df, p = stats::pchisq(TRd, df, lower.tail = FALSE))
}
