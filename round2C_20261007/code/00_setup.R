# 本轮独立工作区；只复制已核验输入，绝不改写上一轮。
local({
 library(jsonlite);library(digest)
 root<-'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
 old<-'C:/Users/LZHS/pp_lgcm_review/round2B_20261006'
 for(d in c('code','vendor','models','audit','evidence','runtime','private','manuscript'))dir.create(file.path(root,d),recursive=TRUE,showWarnings=FALSE)
 for(n in c('model_tools.R','collect_parameters.R','08_pool_parent.R')){
  dst<-file.path(root,'vendor',n);src<-file.path(old,'code',n)
  if(file.exists(dst))stopifnot(digest(file=dst,algo='sha256')==digest(file=src,algo='sha256')) else stopifnot(file.copy(src,dst))
 }
 m<-fromJSON(file.path(old,'audit/mi_member_manifest.json'))
 rows<-lapply(1:10,function(k){
  folder<-file.path(old,'models',sprintf('PARENT_MI%02d/attempt01',k))
  q<-fromJSON(file.path(folder,'input_contract.json'));dat<-file.path(folder,'data.dat')
  stopifnot(digest(file=dat,algo='sha256')==q$data_sha256,
   digest(file=file.path(folder,'model.inp'),algo='sha256')==q$input_sha256,
   digest(file=file.path(old,'private/mi10',sprintf('member_%02d.rds',k)),algo='sha256')==m$sha256[k])
  d<-read.table(dat,na.strings='.');stopifnot(nrow(d)==3274L,ncol(d)==35L,length(unique(d[[1]]))==2410L)
  data.frame(member=k,N=nrow(d),households=length(unique(d[[1]])),data_sha256=q$data_sha256,input_sha256=q$input_sha256,member_sha256=m$sha256[k])
 })
 write.csv(do.call(rbind,rows),file.path(root,'audit/source_members.csv'),row.names=FALSE)
 c<-list(source_commit='a666e0ea8a610159709bb504d3d275f6f582efb9',source_root=old,
  target_N=3274,households=2410,imputations=10,main_controls=fromJSON(file.path(old,'audit/target_parent_contract.json'))$covariates,
  estimator='MLR',cluster='fid',time_unit='decade',Y='CESD8 with frozen 2012 standardization',
  specifications=list(C1='Original X free/Y linear; SY@0; SX WITH IY retained',SW='Original model plus five separate same-wave X-Y residual covariances; SY free',XLIN='Original model with X calendar-linear; SY free'),
  profile_member=1,profile_tau=c(0,.02,.08,.20,.40),
  core_calls=34,max_start_checks=3,max_repairs_and_numeric_retries=3,max_total_calls=40,
  start_thresholds=list(absolute_LL=.01,max_absolute_key_path=.001),
  key_paths=c('bii','bis','bss','bsyiy'),mcse_over_se_flag=.05,
  family_selection='No p-based selection; run all three families on all ten members; pool each eligible family separately',
  inference='Fixed-specification conditional Rubin inference; no selection uncertainty or boundary variance test',
  stop_at='Checkpoint C; no moderation, H4.2b, windows, new MI or bootstrap',
  publish='Aggregate outputs only; ZIP <=25000000 bytes',created=as.character(Sys.time()))
 f<-file.path(root,'RUN_CONTRACT.json')
 if(!file.exists(f))write_json(c,f,pretty=TRUE,auto_unbox=TRUE,digits=NA)
 write_json(list(status='PASS',members=10,all_source_hashes_match=TRUE,created=as.character(Sys.time())),file.path(root,'audit/source_validation.json'),pretty=TRUE,auto_unbox=TRUE)
 cat('ROUND2C INPUT CONTRACT PASS: 10 members, N3274, 2410 households\n')
})
