# Round2F 一次性准备：从 Round2E 根目录按合同哈希复制三件复用代码与支持点表，写冻结清单。
# 不读私有数据、不调用 Mplus。已存在且哈希一致的文件不覆盖；不一致即停止。
library(jsonlite); library(digest)
root <- normalizePath(Sys.getenv('R2F_ROOT'), winslash = '/', mustWork = TRUE)
C <- fromJSON(file.path(root, 'contracts/RUN_CONTRACT_2F.json'), simplifyVector = FALSE)
r2e <- Sys.getenv('R2F_R2E', C$paths_default$R2F_R2E)
hashf <- function(f) digest(file = f, algo = 'sha256')
for (f in names(C$reused_round2E_code_sha256)) {
  src <- file.path(r2e, 'code', f); dst <- file.path(root, 'code', f); want <- C$reused_round2E_code_sha256[[f]]
  if (!file.exists(dst)) { stopifnot(identical(hashf(src), want)); stopifnot(file.copy(src, dst)) }
  if (!identical(hashf(dst), want)) stop('Reused Round2E code hash mismatch: ', f)
}
sp <- file.path(r2e, 'contracts/SUPPORT_POINTS.csv'); if (!file.exists(file.path(root, 'contracts/SUPPORT_POINTS_R2E.csv'))) invisible(file.copy(sp, file.path(root, 'contracts/SUPPORT_POINTS_R2E.csv')))
for (d in c('models', 'runtime', 'audit', 'results', 'private/SD')) dir.create(file.path(root, d), recursive = TRUE, showWarnings = FALSE)
code <- sort(list.files(file.path(root, 'code'), pattern = '\\.(R|py)$'))
fz <- setNames(lapply(code, function(f) hashf(file.path(root, 'code', f))), code)
ff <- file.path(root, 'contracts/FROZEN_CODE_2F.json')
if (file.exists(ff)) {
  old <- fromJSON(ff, simplifyVector = FALSE)
  if (!identical(old[order(names(old))], fz[order(names(fz))])) stop('FROZEN_CODE_2F.json exists and differs; code changed after freezing')
} else write_json(fz, ff, auto_unbox = TRUE, pretty = TRUE)
cat('SETUP_OK', length(code), 'code files frozen\n')

writeLines(hashf(file.path(root,'contracts/RUN_CONTRACT_2F.json')), file.path(root,'contracts/FROZEN_CONTRACT_SHA256.txt'))
cat('CONTRACT FROZEN\n')
