# Round2B：输入、数据和输出一一绑定；所有估计在新目录，不覆盖历史运行。
library(MplusAutomation);library(jsonlite);library(digest)
R2ROOT <- 'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
progress2 <- function(stage,message){
 write_json(list(stage=stage,message=message,updated_at=as.character(Sys.time()),pid=Sys.getpid()),file.path(R2ROOT,'runtime/model_progress.json'),pretty=TRUE,auto_unbox=TRUE)
 cat(format(Sys.time()),stage,message,'\n');flush.console()
 if(exists('clauder_progress',mode='function'))clauder_progress(stage,message)
}
growth2 <- function(f,p,n=5,shape='linear'){
 t<-if(n==5)c(0,.4,.6,.8,1)else c(0,.2,.4,.6)
 op<-if(shape=='linear')rep('@',n)else c('@',rep('*',n-2),'@')
 paste(f,'|',paste0(p,seq_len(n),op,t,collapse=' '),';')
}
parent2 <- function(n=5,nc=24,yshape='linear',samewave=FALSE,boundary=FALSE){
 s<-paste(growth2('ix sx','x',n,'free'),growth2('iy sy','y',n,yshape),
 'iy ON ix (bii);\nsy ON ix (bis);\nsy ON sx (bss);\nsy ON iy (bsyiy);\nix WITH sx;',
 paste0('ix sx iy sy ON c1-c',nc,';'),sep='\n')
 if(samewave)s<-paste(s,paste0('x',1:n,' WITH y',1:n,';',collapse='\n'),sep='\n')
 if(boundary)s<-paste(s,'sy@0;',sep='\n')
 s
}
prepare2 <- function(id,dat,model,use,meta=list(),analysis='TYPE=COMPLEX; ESTIMATOR=MLR; PROCESSORS=1; COVERAGE=.005; ITERATIONS=1000;'){
 dest<-file.path(R2ROOT,'models',id,getOption('round2B.attempt','attempt01'));stopifnot(!dir.exists(dest));dir.create(dest,recursive=TRUE)
 obj<-mplusObject(TITLE=paste('Round2B',id),VARIABLE=paste0('CLUSTER=fid; USEVARIABLES=',use,';'),ANALYSIS=analysis,MODEL=model,OUTPUT='TECH1 TECH3 TECH4 TECH8 SAMPSTAT RESIDUAL CINTERVAL;',SAVEDATA='TECH3=tech3.dat; RESULTS=estimates.dat;',rdata=dat,usevariables=names(dat))
 wd<-getwd();setwd(dest);tryCatch(mplusModeler(obj,dataout='data.dat',modelout='model.inp',run=0L,writeData='always',hashfilename=FALSE,quiet=TRUE),finally=setwd(wd))
 inp<-file.path(dest,'model.inp');da<-file.path(dest,'data.dat');stopifnot(all(nchar(readLines(inp,warn=FALSE))<=90))
 back<-read.table(da,na.strings='.');stopifnot(nrow(back)==nrow(dat),ncol(back)==ncol(dat),identical(unname(is.na(as.matrix(back))),unname(is.na(as.matrix(dat)))),max(abs(as.matrix(back)-as.matrix(dat)),na.rm=TRUE)<1e-8)
 row<-c(list(id=id,N=nrow(dat),households=length(unique(dat$fid)),input=inp,data=da,input_sha256=digest(file=inp,algo='sha256'),data_sha256=digest(file=da,algo='sha256')),meta)
 write_json(row,file.path(dest,'input_contract.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA);row
}
run2 <- function(row){
 inp<-row$input;out<-sub('\\.inp$','.out',inp);dest<-dirname(inp);rec<-file.path(dest,'receipt.json')
 stopifnot(digest(file=inp,algo='sha256')==row$input_sha256,digest(file=row$data,algo='sha256')==row$data_sha256)
 if(file.exists(rec))return(fromJSON(rec))
 if(!file.exists(out)){
   progress2(row$id,paste('start N=',row$N));start<-Sys.time()
   runModels(inp,recursive=FALSE,showOutput=FALSE,replaceOutfile='never',Mplus_command=unname(Sys.which('Mplus')),killOnFail=FALSE,logFile=file.path(dest,'MplusAutomation.log'))
   seconds<-as.numeric(difftime(Sys.time(),start,units='secs'))
 }else seconds<-NA_real_
 stopifnot(file.exists(out));txt<-readLines(out,warn=FALSE);flat<-gsub('[[:space:]]+',' ',paste(txt,collapse=' '))
 p<-tryCatch(readModels(out,quiet=TRUE),error=function(e)list(read_error=conditionMessage(e)))
 saveRDS(p,file.path(dest,'readback.rds'))
 pars<-p$parameters$unstandardized;negative<-FALSE;finite<-FALSE
 if(is.data.frame(pars)&&nrow(pars)>0){
   write.csv(pars,file.path(dest,'parameters.csv'),row.names=FALSE)
   v<-pars[pars$paramHeader%in%c('Variances','Residual.Variances'),]
   negative<-any(v$est<0,na.rm=TRUE)||any(v$se>0&v$est_se<0&v$est_se> -900,na.rm=TRUE)
   finite<-all(is.finite(pars$est))&&all(is.finite(pars$se))
 }
 if(is.data.frame(p$summaries))write.csv(p$summaries,file.path(dest,'fit.csv'),row.names=FALSE)
 normal<-grepl('THE MODEL ESTIMATION TERMINATED NORMALLY',flat,fixed=TRUE)
 bad<-grepl('NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT|STANDARD ERRORS.*COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED',flat)
 inputbad<-grepl('ERROR in .* command|Unknown variable|Unknown option',flat)
 status<-if(inputbad)'INPUT_REJECTED'else if(!normal)'ESTIMATION_FAILED'else if(negative||bad||!finite)'INADMISSIBLE'else'REVIEWABLE'
 result<-list(id=row$id,N=row$N,status=status,normal=normal,negative_variance=negative,matrix_warning=bad,finite_parameters=finite,seconds=seconds,input_sha256=row$input_sha256,data_sha256=row$data_sha256,output_sha256=digest(file=out,algo='sha256'),diagnostics=txt[grepl('WARNING|ERROR|NOT POSITIVE|DID NOT CONVERGE|NO CONVERGENCE|ITERATIONS EXCEEDED|SADDLE POINT',txt)])
 write_json(result,rec,pretty=TRUE,auto_unbox=TRUE,digits=NA)
 progress2(paste0(row$id,'_done'),status);result
}
