# 只为本地公开范围扫描读取已绑定键；真实标识列表始终写在private内。
library(jsonlite)
library(digest)
local({
  root <- 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
  src <- file.path(root,'private/row_keys_and_cc.rds')
  d <- readRDS(src)
  stopifnot(length(d$pid)==3274, length(d$fid)==3274, !anyNA(d$pid), !anyNA(d$fid))
  values <- unique(format(c(d$pid,d$fid),scientific=FALSE,trim=TRUE))
  stopifnot(all(grepl('^[0-9]+$',values)))
  dest <- file.path(root,'private/privacy_scan_identifiers.json')
  write_json(list(identifiers=values),dest,auto_unbox=FALSE)
  write_json(list(scope='Exact current-cohort PID/FID tokens; private scan list is not for publication',
      source_sha256=digest(file=src,algo='sha256'),scan_list_sha256=digest(file=dest,algo='sha256'),
      distinct_identifiers=length(values),created=as.character(Sys.time())),
      file.path(root,'audit/identity_scan_scope.json'),auto_unbox=TRUE,pretty=TRUE)
  cat('PRIVATE_ID_SCAN_LIST_READY: ',length(values),' unique tokens; no identifiers printed\n',sep='')
})
