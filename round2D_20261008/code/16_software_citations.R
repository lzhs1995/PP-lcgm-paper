# 只读提取当前会话可见的软件引文；不安装、不修改全局库路径。
library(utils)
local({
  packages <- c('mice', 'miceadds', 'MplusAutomation')
  rows <- unlist(lapply(packages, function(pkg) {
    c(pkg, tryCatch(capture.output(print(utils::citation(pkg))),
      error = function(e) paste('NOT_VISIBLE_IN_CURRENT_SESSION:', conditionMessage(e))), '')
  }))
  writeLines(rows, 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008/audit/method_software_citations.txt')
  cat('SESSION_PID', Sys.getpid(), '\n', paste(rows, collapse='\n'), '\n')
})
