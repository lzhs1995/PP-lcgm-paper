# 仅输出命中计数和路径，不公开真实PID/FID；发布目录在本地先检查。
local({
 root<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006';stage<-file.path(root,'public_stage')
 stopifnot(dir.exists(stage));d<-readRDS(file.path(root,'private/baseline_preMI.rds'))$data
 docs<-jsonlite::fromJSON(file.path(root,'runtime/document_privacy_scan.json'))
 stopifnot(docs$status=='PASS',isTRUE(docs$manuscript_pairs_complete))
 actualdocs<-list.files(stage,pattern='[.](docx|pdf)$',recursive=TRUE,full.names=FALSE,ignore.case=TRUE)
 stopifnot(setequal(actualdocs,docs$files$path))
 for(k in seq_len(nrow(docs$files)))stopifnot(digest::digest(file=file.path(stage,docs$files$path[k]),algo='sha256')==docs$files$sha256[k])
 dir.create(file.path(stage,'runtime'),showWarnings=FALSE)
 file.copy(file.path(root,'runtime/document_privacy_scan.json'),file.path(stage,'runtime'),overwrite=TRUE)
 ids<-unique(format(c(d$pid,d$fid),scientific=FALSE,trim=TRUE));ids<-ids[nchar(ids)>=5]
 files<-list.files(stage,recursive=TRUE,full.names=TRUE);files<-files[!file.info(files)$isdir]
 banned<-files[tolower(tools::file_ext(files))%in%c('dat','dta','rds','gh5','rdata')]
 stopifnot(length(banned)==0)
 txt<-files[tolower(tools::file_ext(files))%in%c('txt','out','inp','csv','json','md','r','py')]
 rows<-lapply(txt,function(p){
   s<-paste(readLines(p,warn=FALSE,encoding='UTF-8'),collapse='\n')
   tok<-regmatches(s,gregexpr('(?<![[:alnum:].])[0-9]{5,14}(?![[:alnum:].])',s,perl=TRUE))[[1]]
   data.frame(path=substring(p,nchar(stage)+2),potential_identifier_matches=length(intersect(tok,ids)))
 })
 out<-do.call(rbind,rows);write.csv(out,file.path(root,'runtime/public_privacy_scan.csv'),row.names=FALSE)
 bound<-files[basename(files)!='FILE_MANIFEST.csv' & !grepl('/runtime/public_privacy_scan\\.(csv|json)$',files)]
 hashes<-data.frame(path=substring(bound,nchar(stage)+2),sha256=vapply(bound,function(p)digest::digest(file=p,algo='sha256'),character(1)))
 write.csv(hashes,file.path(root,'runtime/public_scan_file_hashes.csv'),row.names=FALSE)
 jsonlite::write_json(list(status=if(all(out$potential_identifier_matches==0))'PASS'else'REQUIRES_LOCAL_REVIEW',text_files=nrow(out),banned_files=length(banned),matching_files=sum(out$potential_identifier_matches>0),limitations='Known exact numeric PID/FID token scan plus allowlist; does not certify unrestricted microdata deidentification'),file.path(root,'runtime/public_privacy_scan.json'),pretty=TRUE,auto_unbox=TRUE)
 stopifnot(all(out$potential_identifier_matches==0));cat('Known identifier scan passed',nrow(out),'text files\n')
 dir.create(file.path(stage,'runtime'),showWarnings=FALSE)
 file.copy(file.path(root,'runtime',c('public_privacy_scan.csv','public_privacy_scan.json')),file.path(stage,'runtime'),overwrite=TRUE)
})
