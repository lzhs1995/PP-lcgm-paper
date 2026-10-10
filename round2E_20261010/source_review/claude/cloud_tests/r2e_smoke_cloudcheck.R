# 云端检查冒烟脚本本身的流程（无 Mplus）：以模拟的 run_model 替换 Mplus 调用，其余（合成数据、合同、输入生成、SVALUES 拼接、全部判定）照常执行。
# 模拟输出取 Round2D 真实输出副本；边界规格在副本末尾补一行固定 SY 的打印格式；关键路径取生成模型真值附近的数。
# 用法：Rscript r2e_smoke_cloudcheck.R <code目录> <Round2D包的models目录> <新的空目录>
args <- commandArgs(TRUE); code <- normalizePath(args[1], winslash = '/'); r2dm <- normalizePath(args[2], winslash = '/'); work <- args[3]
Sys.setenv(R2E_SMOKE_SOURCE_ONLY = '1', R2E_CODE = code, R2E_RESOURCE_GATE = '0')
source(file.path(code, 'r2e_smoke_mplus.R'))
OUT <- list(lin = file.path(r2dm, 'OLDEST', 'D0_Z0_MI01', 'base'), e1 = file.path(r2dm, 'SD', 'E1_SYNTHETIC_MI00', 'synthetic'),
            h4 = file.path(r2dm, 'SD', 'H4_EDU_SYNTHETIC_MI00', 'synthetic'), d1 = file.path(r2dm, 'SD', 'D1_SYNTHETIC_MI00', 'synthetic'))
# 模拟输出：取真实输出副本，但把 SVALUES 段换成本次输入的 MODEL 行，使下一步起点拼接面对结构一致的源（与真实流程相同）
mock_out <- function(src, dest) {
  L <- readLines(file.path(src, 'model.out'), warn = FALSE, encoding = 'latin1'); a <- grep('MODEL COMMAND WITH FINAL ESTIMATES USED AS STARTING VALUES', L)[1]
  k <- a + 1L; while (k <= length(L) && !(nchar(trimws(L[k])) && !grepl('^\\s', L[k]))) k <- k + 1L
  I <- readLines(file.path(dest, 'model.inp')); m <- I[(which(I == 'MODEL:') + 1):(which(I == 'OUTPUT:') - 1)]
  c(L[1:a], '', paste0('     ', m), '', L[k:length(L)])
}
hook <- function() {
  mock <- function(row) {
    dest <- row$dest; rf <- file.path(dest, 'receipt.json'); if (file.exists(rf)) return(jsonlite::fromJSON(rf, simplifyVector = FALSE))
    stopifnot(hashf(file.path(dest, 'model.inp')) == row$input_sha256); register_call(row)
    src <- if (row$spec %in% c('E0', 'E0B', 'D0', 'D0B')) OUT$lin else if (grepl('^H4', row$spec)) OUT$h4 else if (grepl('^D1', row$spec)) OUT$d1 else OUT$e1
    L <- mock_out(src, dest)
    if (length(row$fixed_zero)) L <- c(L, '    SY                 0.000      0.000    999.000    999.000')
    writeLines(L, file.path(dest, 'model.out'), useBytes = TRUE)
    si <- spec_info_r2e(row$z, row$spec, ctrl_of(row$z), zshape_of(row$z)); lab <- si$key$label
    tv <- c(bii = -.35, bis = .1, bss = -.3, bsyiy = .2, gi0 = .15, gs0 = .1, gii = .1, gis = 0, gss = 0, gizg = 0, gszg = 0, bxg = 0,
            dc = if (grepl('^H4', row$spec)) -.25 else -.33, dcg = if (grepl('EDU', row$spec)) -.2 else 0)
    est <- unname(tv[lab]); se <- rep(.04, length(lab))
    utils::write.csv(data.frame(label = lab, parameter = seq_along(lab), row = si$key$row, column = si$key$column, estimate = est, se = se), file.path(dest, 'key_paths.csv'), row.names = FALSE)
    utils::write.csv(diag(se^2, length(lab)), file.path(dest, 'parameter_covariance.csv'))
    r <- c(row[c('id', 'z', 'spec', 'member', 'attempt', 'category', 'batch', 'kind', 'sample', 'N', 'households', 'settings')],
           list(status = 'USABLE', usable = TRUE, boundary = FALSE, normal = TRUE, seconds = if (row$settings$processors == 4) 3 else 5, LL = -5000, parameters = 80L,
                iterations = 40L, integration_dimensions = if (si$kind == 'lms_latent') 2L else if (si$kind == 'lms_observed') 1L else NA))
    wj(r, rf); add_ledger(r, row$batch); r
  }
  assign('run_model', mock, envir = globalenv())
}
tab <- smoke_main(work, hook)
need <- c('contract_frozen', 'call_E0', 'call_E1_q15', 'call_E1_q15_p4', 'call_E1_q15_default_start', 'call_E0B', 'call_E1B_q15', 'call_H4_EDU_q15', 'call_H4_INC_q15',
          'call_H4B_EDU_q15', 'call_D0', 'call_D0B', 'call_D1L_q10', 'call_D1B_q10', 'splice_E1_q15', 'splice_E1_q15_p4', 'splice_E0B', 'splice_E1B_q15', 'splice_H4_EDU_q15',
          'splice_H4_INC_q15', 'splice_H4B_EDU_q15', 'splice_D0B', 'splice_D1L_q10', 'splice_D1B_q10', 'sy_fixed_E0B', 'sy_fixed_E1B_q15', 'sy_fixed_H4B_EDU_q15',
          'sy_fixed_D0B', 'sy_fixed_D1B_q10', 'processors_4_vs_1_numeric', 'processors_input_line', 'start_default_vs_spliced', 'recover_E1_dc_marginal',
          'recover_H4_EDU_delta0', 'recover_H4_EDU_deltaG', 'recover_H4_INC_deltaG_null', 'integration_dims_E1_H4', 'integration_dims_D1')
miss <- setdiff(need, tab$test); bad <- tab[tab$result != 'PASS', ]
ex <- file.path(dirname(normalizePath(work)), 'smoke_return_cloudcheck.zip'); if (file.exists(ex)) file.remove(ex)
o <- system2(Sys.which('python3'), c('-I', file.path(code, 'r2e_06_export.py'), file.path(work, 'R2E'), ex), stdout = TRUE, stderr = TRUE)
zl <- utils::unzip(ex, list = TRUE)$Name
cat('missing tests:', length(miss), paste(miss, collapse = ' '), '\nnon-pass:', nrow(bad), '\n'); if (nrow(bad)) print(bad, row.names = FALSE)
cat('export has SMOKE_RESULTS:', any(grepl('results/SMOKE_RESULTS.csv', zl)), '; private excluded:', !any(grepl('private/|/data\\.dat$', zl)), '\n')
ok <- !length(miss) && !nrow(bad) && any(grepl('results/SMOKE_RESULTS.csv', zl)) && !any(grepl('private/|/data\\.dat$', zl))
cat(if (ok) 'SMOKE CLOUDCHECK PASSED' else 'SMOKE CLOUDCHECK FAILED', nrow(tab), 'checks\n'); if (!ok) quit(status = 1)
