# 四次本机合成Mplus预检；它们不是CFPS新研究结果。
source('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/code/03_engine.R',local=TRUE)
stopifnot(isTRUE(fromJSON(file.path(ROOT,'tests/unit_summary.json'))$passed))
set.seed(26100803);n<-1200;C<-matrix(rbinom(n*24,1,.4),n);fid<-rep(seq_len(n/2),each=2)
ix<-rnorm(n,0,.8)+.1*C[,1];sx<-.15*ix+rnorm(n,0,.7);iz<-.3*ix+rnorm(n,0,.8);sz<-.1*sx+rnorm(n,0,.6)
iy<--.35*ix+.15*iz+.1*sx+.1*sz+rnorm(n,0,.8);sy<-.1*ix-.3*sx+.2*iy+.1*iz+.1*sz+.3*sx*iz+rnorm(n,0,.6)
X<-Y<-Z<-matrix(0,n,5)
for(w in 1:5){e<-matrix(rnorm(n*3),n)%*%chol(matrix(c(.4,.04,.03,.04,.4,.04,.03,.04,.4),3));
 X[,w]<-ix+c(0,.65,.7,.95,1)[w]*sx+e[,1];Y[,w]<-iy+R2D_TIME[w]*sy+e[,2];Z[,w]<-iz+c(0,.45,.6,.85,1)[w]*sz+e[,3]}
dat<-data.frame(fid,X,Y,Z,Z[,1],C[,2],C[,3],C[,4],C);names(dat)<-R2D_NAMES
f<-file.path(ROOT,'tests/synthetic_data.dat');if(!file.exists(f))write_dat(dat,f)
out<-list()
for(spec in c('D0','D1','E1','H4_EDU')){
 r<-run_one('SD',spec,0,'synthetic','SYNTHETIC',sample='SYNTHETIC',settings=list(method='montecarlo',points=500,seed=26100803),source_data=f,ctrl='c1-c3')
 out[[spec]]<-r$receipt
 if(r$receipt$status%in%c('INPUT_REJECTED','EXTRACTION_FAILED','KEY_PATH_ERROR','PRINTED_MISMATCH'))break
}
# 软件接口预检与模型的样本数值表现分开：合法性及警告仍全部留档。
ok<-length(out)==4&&all(vapply(out,function(r)isTRUE(r$normal)&&r$status%in%c('USABLE','INADMISSIBLE'),logical(1)))
wj(list(interface_passed=ok,receipts=out,created=as.character(Sys.time()),note='Synthetic Mplus interface check only; actual-data adoption requires all gates'),file.path(ROOT,'tests/synthetic_summary.json'))
progress('synthetic_complete',paste('Mplus interface check',ok))
if(!ok)stop('Synthetic interface failed; inspect actual outputs before any CFPS fit')
