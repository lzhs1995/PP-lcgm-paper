local({
 py<-'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
 sc<-'C:/Users/LZHS/.agents/skills/mplusautomation-guide/scripts/windows_host_profile.py'
 z<-system2(py,c('-X','utf8',shQuote(sc),'--output',shQuote('C:/Users/LZHS/pp_lgcm_review/20261005/native/resource_diagnostic.json'),'--samples','2','--interval','1','--include-processes'),stdout=TRUE,stderr=TRUE)
 writeLines(z,'C:/Users/LZHS/pp_lgcm_review/20261005/native/resource_command_error.log')
 cat(z,sep='\n');print(attr(z,'status'))
})
