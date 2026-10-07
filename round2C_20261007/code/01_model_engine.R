# 预定规格、矩阵重建和采用规则；所有输出留在Round2C。
.libPaths(c('C:/Users/LZHS/pp_lgcm_runs/20260908/library_mplusautomation_20260926',.libPaths()))
library(MplusAutomation);library(jsonlite);library(digest)
R2C<-'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
R2B<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
source(file.path(R2C,'vendor/model_tools.R'),local=TRUE);R2ROOT<-R2C
source(file.path(R2C,'vendor/08_pool_parent.R'),local=TRUE)
F3<-c('IX','SX','IY','SY');V3<-c(paste0('X',1:5),paste0('Y',1:5))
KEY3<-data.frame(label=c('bii','bis','bss','bsyiy'),row=c('IY','SY','SY','SY'),column=c('IX','IX','SX','IY'))
hash3<-function(f)digest(file=f,algo='sha256')
key3<-function(p){
 out<-KEY3
 for(k in 1:4){x<-p[p$matrix=='beta'&p$row==out$row[k]&p$column==out$column[k],];stopifnot(nrow(x)==1);out$parameter[k]<-x$parameter;out$estimate[k]<-x$estimate;out$se[k]<-x$se}
 out
}
matrix_check3<-function(m,expected_rank=nrow(m),tol=1e-7){
 stopifnot(is.matrix(m),all(is.finite(m)),max(abs(m-t(m)))<1e-8)
 # 正对角线标准化；零对角线保留单位尺度，禁止投影矩阵。
 s<-sqrt(abs(diag(m)));s[s<1e-10]<-1
 a<-m/outer(s,s);ev<-eigen((a+t(a))/2,symmetric=TRUE,only.values=TRUE)$values
 rank<-sum(ev>tol)
 list(min_eigen=min(ev),max_eigen=max(ev),rank=rank,expected_rank=expected_rank,
      psd=min(ev)>= -tol,rank_ok=rank==expected_rank,positive_definite=min(ev)>tol,
      tolerance=tol,condition=if(min(ev)>0)max(ev)/min(ev)else NA_real_)
}
geometry3<-function(p,spec,tau=NA_real_){
 B<-P<-matrix(0,4,4,dimnames=list(F3,F3));L<-matrix(0,10,4,dimnames=list(V3,F3));T<-matrix(0,10,10,dimnames=list(V3,V3))
 # 固定测量系数来自冻结语法，所有期望自由参数必须确实存在。
 L[1:5,'IX']<-1;L[6:10,'IY']<-1;L[1:5,'SX']<-c(0,.4,.6,.8,1);L[6:10,'SY']<-c(0,.4,.6,.8,1)
 getp<-function(mat,r,c,symmetric=FALSE){
  z<-p[p$matrix==mat & ((p$row==r&p$column==c)|(symmetric&p$row==c&p$column==r)),]
  stopifnot(nrow(z)==1);z$estimate
 }
 if(spec!='XLIN')for(i in 2:4)L[paste0('X',i),'SX']<-getp('lambda',paste0('X',i),'SX')
 for(k in 1:4)B[KEY3$row[k],KEY3$column[k]]<-getp('beta',KEY3$row[k],KEY3$column[k])
 for(f in F3){
  if(f=='SY'&&!is.na(tau)){
   stopifnot(!any(p$matrix=='psi'&p$row=='SY'&p$column=='SY'));P[f,f]<-tau
  }else P[f,f]<-getp('psi',f,f)
 }
 for(pair in list(c('IX','SX'),c('SX','IY'))){r<-pair[1];c<-pair[2];P[r,c]<-P[c,r]<-getp('psi',r,c,TRUE)}
 for(v in V3)T[v,v]<-getp('theta',v,v)
 if(spec=='SW')for(i in 1:5){x<-paste0('X',i);y<-paste0('Y',i);T[x,y]<-T[y,x]<-getp('theta',x,y,TRUE)}
 A<-solve(diag(4)-B);G<-A%*%P%*%t(A);dimnames(G)<-list(F3,F3)
 S<-L%*%G%*%t(L)+T
 i<-c('IX','IY');s<-c('SX','SY');H<-G[s,s]-G[s,i]%*%solve(G[i,i],G[i,s]);
 checks<-list(PSI=matrix_check3(P,if(!is.na(tau)&&tau==0)3 else 4),G=matrix_check3(G,if(!is.na(tau)&&tau==0)3 else 4),THETA=matrix_check3(T),SIGMA=matrix_check3(S))
 # 高精度保存仍可能舍入：自由方差负数一律不自动放行。
 free_v<-p[p$matrix%in%c('psi','theta')&p$row==p$column,]
 negative<-paste(free_v$matrix[free_v$estimate<0],free_v$row[free_v$estimate<0],sep=':')
 ok<-!length(negative)&&all(vapply(checks,function(q)q$psd&&q$rank_ok,logical(1)))&&checks$SIGMA$positive_definite&&checks$THETA$positive_definite
 list(B=B,PSI=P,LAMBDA=L,THETA=T,G=G,SIGMA=S,partial=H,checks=checks,negative=negative,passed=ok,
      diagnostic=list(partial_SX=H[1,1],partial_SY=H[2,2],partial_covariance=H[1,2],
      partial_ratio=if(all(diag(H)>0))H[1,2]/sqrt(prod(diag(H)))else NA_real_,
      residual_reconstructed=if(H[1,1]>0)H[2,2]-H[1,2]^2/H[1,1]else NA_real_,SY_residual=P['SY','SY']))
}
collect3<-function(dest){
 o<-readRDS(file.path(dest,'readback.rds'));n<-o$summaries$Parameters
 stopifnot(length(n)==1L,file.exists(file.path(dest,'estimates.dat')))
 v<-scan(file.path(dest,'estimates.dat'),quiet=TRUE);stopifnot(length(v)>=2*n+1,v[2*n+1]==n)
 q<-v[seq_len(n)];se<-v[n+seq_len(n)]
 sp<-o$tech1$parameterSpecification;rows<-list()
 for(m in names(sp)){z<-sp[[m]];ix<-which(is.finite(z)&z>0,arr.ind=TRUE);if(nrow(ix))rows[[m]]<-data.frame(parameter=as.integer(z[ix]),matrix=m,row=rownames(z)[ix[,1]],column=colnames(z)[ix[,2]])}
 p<-do.call(rbind,rows);p<-p[!duplicated(p$parameter),];p<-p[order(p$parameter),];stopifnot(identical(p$parameter,seq_len(n)))
 p$estimate<-q;p$se<-se
 write.csv(p,file.path(dest,'parameters_high_precision.csv'),row.names=FALSE)
 U<-o$tech3$paramCov.savedata;if(is.null(U))U<-o$tech3$paramCov
 stopifnot(is.matrix(U),all(dim(U)==n),all(is.finite(U)),max(abs(U-t(U)))<1e-6)
 write.csv(U,file.path(dest,'parameter_covariance.csv'),row.names=TRUE)
 discrepancy<-max(abs(diag(U)-se^2));finite<-all(is.finite(q))&&all(is.finite(se))&&all(se>0)
 ch<-matrix_check3(U)
 valid<-finite&&discrepancy<max(1e-5,max(se^2)*1e-4)&&ch$positive_definite
 write_json(list(parameters=n,vcov_diagonal_max_difference=discrepancy,results_sha256=hash3(file.path(dest,'estimates.dat')),tech3_sha256=hash3(file.path(dest,'tech3.dat')),bound_to_TECH1=TRUE,valid=valid,covariance=ch),file.path(dest,'parameter_binding.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 # 保留TECH1/TECH4/R读回的聚合内容；私有RDS不公开。
 write_json(o$tech1,file.path(dest,'tech1.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 write_json(o$tech4,file.path(dest,'tech4.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 if(!is.null(o$residuals))write_json(o$residuals,file.path(dest,'local_residuals.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
 list(p=p,U=U,valid=valid)
}
prepare3<-function(spec,k,tau=NA_real_,attempt='attempt01',start=FALSE,iterations=1000){
 id<-sprintf('%s_MI%02d',spec,k);dest<-file.path(R2C,'models',id,attempt)
 contract<-file.path(dest,'input_contract.json');if(file.exists(contract))return(fromJSON(contract))
 src<-file.path(R2B,'models',sprintf('PARENT_MI%02d/attempt01',k));old<-fromJSON(file.path(src,'input_contract.json'))
 stopifnot(hash3(file.path(src,'data.dat'))==old$data_sha256,hash3(file.path(src,'model.inp'))==old$input_sha256)
 s<-readLines(file.path(src,'model.inp'),warn=FALSE)
 a<-which(s=='MODEL:');b<-which(s=='OUTPUT:');stopifnot(length(a)==1,length(b)==1,b>a)
 expected<-paste(parent2(), 'sx WITH iy;',sep='\n');norm<-function(x)gsub('[[:space:]]','',paste(x,collapse=''))
 stopifnot(norm(s[(a+1):(b-1)])==norm(expected))
 m<-s[(a+1):(b-1)]
 if(spec=='XLIN')m[1]<-'ix sx | x1@0 x2@0.4 x3@0.6 x4@0.8 x5@1;'
 if(spec=='SW')m<-c(m,paste0('x',1:5,' WITH y',1:5,';'))
 if(!is.na(tau))m<-c(m,paste0('sy@',format(tau,scientific=FALSE,trim=TRUE),';'))
 if(start){oldp<-read.csv(file.path(R2C,'models',id,'attempt01/parameters_high_precision.csv'));bss<-key3(oldp)$estimate[3];m<-sub('sy ON sx \\(bss\\);',paste0('sy ON sx*',if(bss<=0)'.5'else'-.5',' (bss);'),m)}
 s<-c(s[1:a],m,s[b:length(s)]);s<-sub('Round2B PARENT_MI[0-9]+',paste('Round2C',id,attempt),s)
 s<-sub('ITERATIONS=1000;',paste0('ITERATIONS=',iterations,';'),s,fixed=TRUE)
 # TECH8不适用于普通COMPLEX，不再产生无关输出警告。
 s<-sub('TECH4 TECH8','TECH4',s,fixed=TRUE)
 stopifnot(all(nchar(s)<=90));dir.create(dest,recursive=TRUE)
 stopifnot(file.copy(file.path(src,'data.dat'),file.path(dest,'data.dat')))
 writeLines(s,file.path(dest,'model.inp'),useBytes=TRUE)
 row<-list(id=id,spec=spec,member=k,attempt=attempt,tau=tau,start_check=start,N=3274,households=2410,
  input=file.path(dest,'model.inp'),data=file.path(dest,'data.dat'),source_input_sha256=old$input_sha256,
  input_sha256=hash3(file.path(dest,'model.inp')),data_sha256=hash3(file.path(dest,'data.dat')))
 stopifnot(row$data_sha256==old$data_sha256)
 write_json(row,contract,pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null');row
}
run3<-function(row){
 dest<-dirname(row$input);f<-file.path(dest,'receipt_round2C.json')
 if(file.exists(f))return(fromJSON(f))
 # 每次真实调用前登记，故中断恢复不会重跑已完成输出。
 reg<-file.path(R2C,'audit/CALL_REGISTER.csv')
 tab<-if(file.exists(reg))read.csv(reg)else data.frame()
 if(!file.exists(file.path(dest,'model.out'))){
  stopifnot(nrow(tab)<40)
  record<-data.frame(id=row$id,attempt=row$attempt,spec=row$spec,member=row$member,start_check=row$start_check,time=as.character(Sys.time()))
  if(!nrow(tab)||!any(tab$id==row$id&tab$attempt==row$attempt))write.csv(rbind(tab,record),reg,row.names=FALSE)
 }
 r<-run2(row);r$spec<-row$spec;r$member<-row$member;r$attempt<-row$attempt
 r$tau<-row$tau;r$usable<-FALSE
 if(r$normal){
  x<-tryCatch(collect3(dest),error=function(e){write_json(list(error=conditionMessage(e)),file.path(dest,'extraction_failure.json'),pretty=TRUE);NULL})
  if(!is.null(x)){
   tau<-if(is.null(row$tau))NA_real_ else row$tau
   geom<-tryCatch(geometry3(x$p,row$spec,tau),error=function(e){write_json(list(error=conditionMessage(e)),file.path(dest,'geometry_failure.json'),pretty=TRUE);NULL})
   if(!is.null(geom)){
    for(n in c('B','PSI','LAMBDA','THETA','G','SIGMA','partial'))write.csv(geom[[n]],file.path(dest,paste0('matrix_',n,'.csv')))
    write_json(list(checks=geom$checks,diagnostic=geom$diagnostic,negative=geom$negative,passed=geom$passed),file.path(dest,'geometry.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
    r$geometry_passed<-geom$passed;r$negative<-geom$negative;r$SY_residual<-geom$diagnostic$SY_residual
    txt<-paste(readLines(file.path(dest,'model.out'),warn=FALSE),collapse=' ');flat<-gsub('[[:space:]]+',' ',txt)
    fatal<-grepl('SADDLE POINT|STANDARD ERRORS.*COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED|NON-POSITIVE DEFINITE FIRST-ORDER DERIVATIVE',flat)
    # 只有预定tau=0、全部矩阵几何及信息验收通过，才解释PSD警告为预期边界。
    boundary<-!is.na(tau)&&tau==0
    warning_ok<-!r$matrix_warning||(boundary&&geom$passed&&!fatal)
    r$usable<-x$valid&&geom$passed&&!fatal&&warning_ok
    r$status<-if(r$usable)if(boundary)'CONDITIONAL_FIXED_ZERO'else'CONDITIONAL_REVIEWABLE'else'INADMISSIBLE'
    r$expected_boundary_warning<-boundary&&r$matrix_warning&&r$usable
   }
  }
 }
 write_json(r,f,pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null')
 progress2(paste0(row$id,'_assessed'),r$status);r
}
