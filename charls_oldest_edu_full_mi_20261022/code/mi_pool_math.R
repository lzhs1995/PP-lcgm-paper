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
