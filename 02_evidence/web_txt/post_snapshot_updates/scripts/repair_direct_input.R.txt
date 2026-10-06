# 仅修正输入格式：参数标签各占一条ON语句，变量范围缩写避免90列截断；数据和估计规格不变。
local({
 library(jsonlite);library(digest)
 dest<-'C:/Users/LZHS/pp_lgcm_review/20261005'
 old<-fromJSON(file.path(dest,'analysis/sensitivity/manifest.json'),simplifyVector=FALSE)
 rows<-Filter(function(x)x$family=='direct',old$models)
 for(i in seq_along(rows)){
   r<-rows[[i]];src<-readLines(r$input,warn=FALSE)
   target<-file.path(dest,'analysis/sensitivity_input_repair',r$id);dir.create(target,recursive=TRUE,showWarnings=FALSE)
   inp<-file.path(target,'model.inp');dat<-file.path(target,'data.dat');stopifnot(!file.exists(inp),!file.exists(dat))
   k<-if(r$window=='five')5 else 4
   src[grepl('CLUSTER=fid;',src,fixed=TRUE)]<-paste0('CLUSTER=fid;\nUSEVARIABLES=y1-y',k,' x1-x',k,' c1-c26;')
   src[grepl('iy ON ix (bii);',src,fixed=TRUE)]<-'iy ON ix (bii);\nsy ON ix (bis);\nsy ON sx (bss);\nsy ON iy;\niy sy ON c1-c26;'
   writeLines(src,inp);stopifnot(file.copy(r$data,dat),digest(dat,algo='sha256',file=TRUE)==r$data_sha256)
   stopifnot(all(nchar(readLines(inp))<=90))
   r$previous_input<-r$input;r$previous_input_sha256<-r$input_sha256;r$input<-inp;r$data<-dat;r$input_sha256<-digest(inp,algo='sha256',file=TRUE)
   r$status<-'PREPARED_FORMAT_REPAIR_ONLY';rows[[i]]<-r
 }
 old$models<-rows;old$repair<-'Mplus label grammar and 90-column input width only; same data bytes, covariates, estimand and estimator.'
 write_json(old,file.path(dest,'analysis/sensitivity_input_repair/manifest.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA)
 cat('4个输入格式修正版已准备；未修改任何原输入/输出；数据哈希恒等\n')
})
