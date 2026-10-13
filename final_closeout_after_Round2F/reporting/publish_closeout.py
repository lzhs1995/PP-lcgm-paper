"""在用户指定仓库发布可核验交付；禁止强推；固定提交匿名下载后重跑随包验证器。"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,io,json,shutil,subprocess,sys,zipfile
import requests
import publication_gate
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'public_stage'
REPO=Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/cfps_review_20261005/github_publish')
GIT='C:/Program Files/Git/cmd/git.exe';PREFIX='final_closeout_after_Round2F';TAG='scoped-closeout-20261012';REMOTE='lzhs1995/PP-lcgm-paper'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(ROOT/'runtime'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def git(*args):
 r=subprocess.run([GIT,'-C',str(REPO),*args],capture_output=True)
 if r.returncode:raise RuntimeError(r.stderr.decode('utf-8',errors='replace'))
 return r.stdout
def origin():
 url=git('remote','get-url','origin').decode().strip().lower().rstrip('/').removesuffix('.git')
 assert url in {'https://github.com/'+REMOTE.lower(),'git@github.com:'+REMOTE.lower()}
def safe(n):assert not n.startswith(('/','\\')) and '\\' not in n and ':' not in n and '..' not in n.split('/');return n
def payload(folder):
 rr=list(csv.DictReader((folder/'FILE_MANIFEST.csv').open(encoding='utf-8-sig')))
 assert len(rr)==len({r['path'] for r in rr})
 for r in rr:
  p=folder/safe(r['path']);assert p.stat().st_size==int(r['bytes']) and sha(p)==r['sha256'],r['path']
 return rr
def check():
 publication_gate.check(STAGE)
 origin();r=read(ROOT/'runtime/package_validation.json');assert r['status']=='PASS'
 assert sha(STAGE/'PACKAGE_MANIFEST.json')==r['package_manifest_sha256']
 assert read(STAGE/'audit/public_privacy_scan.json')['status']=='PASS'
 receipt=read(STAGE/'CLOSEOUT_RECEIPT.json');assert receipt['new_mplus_calls']==0 and receipt['status']=='SCOPED_CLOSEOUT_COMPLETE'
 entries=payload(STAGE);seen=set()
 for p in r['packages']:
  path=STAGE/p['path'];assert path.stat().st_size==p['bytes']<=25_000_000 and sha(path)==p['sha256']
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None and len(z.namelist())==p['files']
   for n in z.namelist():assert n not in seen and hashlib.sha256(z.read(n)).hexdigest()==sha(STAGE/safe(n));seen.add(n)
 assert seen=={e['path'] for e in entries}|{'FILE_MANIFEST.csv'}
 for d in read(STAGE/'manuscript/delivery/visual_review.json')['documents']:
  assert sha(STAGE/'manuscript/delivery'/d['pdf'])==d['pdf_sha256']
 print('PUBLICATION_PREFLIGHT_PASS',len(seen),flush=True)
 return r
def commit():
 r=check();record=ROOT/'runtime/github_local_commit.json'
 if record.exists():
  x=read(record);assert x['package_manifest_sha256']==r['package_manifest_sha256'];assert git('rev-parse','HEAD').decode().strip()==x['commit'];print('REUSE_COMMIT',x['commit']);return
 assert not git('status','--porcelain').strip(),'Existing local changes'
 assert git('branch','--show-current').decode().strip()=='main'
 head=git('rev-parse','HEAD').decode().strip();refs={s.split()[1]:s.split()[0] for s in git('ls-remote','origin','refs/heads/main','refs/tags/'+TAG).decode().splitlines()}
 assert refs['refs/heads/main']==head and 'refs/tags/'+TAG not in refs
 dst=REPO/PREFIX;assert not dst.exists();shutil.copytree(STAGE,dst)
 rp=REPO/'README.md';old=rp.read_bytes();(ROOT/'runtime/repository_README_before_closeout.md').write_bytes(old)
 notice=f'最新交付：[PP-LGCM范围收缩收尾稿（2026-10-12）]({PREFIX}/README.md)。零新增估计，保留SW与SD E0；四项调节与H4的未完成状态完整披露，原稿及历史结果保留。\n\n'
 rp.write_bytes(notice.encode()+old)
 expected={p.relative_to(REPO).as_posix() for p in dst.rglob('*') if p.is_file()}|{'README.md'}
 git('-c','core.autocrlf=false','add','-f','--',PREFIX,'README.md')
 changed=set(filter(None,git('diff','--cached','--name-only','-z').decode().split('\0')));assert changed==expected
 blobs={}
 for item in git('ls-files','--stage','-z').split(b'\0'):
  if item:
   h,p=item.split(b'\t',1);blobs[p.decode()]=h.decode().split()[1]
 for n in changed:
  d=(REPO/n).read_bytes();assert hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()==blobs[n]
 name,email=git('show','-s','--format=%an%n%ae',head).decode().strip().splitlines()
 git('-c','user.name='+name,'-c','user.email='+email,'commit','-m','Close PP-LGCM revision with scoped manuscript and zero new estimation')
 new=git('rev-parse','HEAD').decode().strip();git('tag',TAG,new)
 save('github_local_commit.json',dict(commit=new,previous=head,tag=TAG,files=len(changed),package_manifest_sha256=r['package_manifest_sha256']))
 print('LOCAL_COMMIT',new,flush=True)
def push():
 check();r=read(ROOT/'runtime/github_local_commit.json');assert git('rev-parse','HEAD').decode().strip()==r['commit'];assert not git('status','--porcelain').strip()
 refs={s.split()[1]:s.split()[0] for s in git('ls-remote','origin','refs/heads/main','refs/tags/'+TAG).decode().splitlines()}
 assert refs['refs/heads/main'] in {r['previous'],r['commit']} and refs.get('refs/tags/'+TAG,r['commit'])==r['commit']
 helper='!"C:/Program Files/GitHub CLI/gh.exe" auth git-credential'
 git('-c','credential.helper=','-c','credential.helper='+helper,'push','--atomic','origin',r['commit']+':refs/heads/main','refs/tags/'+TAG+':refs/tags/'+TAG)
 save('github_push_receipt.json',dict(status='PUSHED',**r,utc=datetime.now(timezone.utc).isoformat()));print('PUSHED',r['commit'],flush=True)
def verify():
 origin();r=read(ROOT/'runtime/github_local_commit.json');c=r['commit'];session=requests.Session();session.trust_env=False
 session.headers['User-Agent']='PP-LGCM-anonymous-closeout-verification'
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f');dest=ROOT/'runtime/github_anonymous_download'/stamp;dest.mkdir(parents=True)
 manifest=read(STAGE/'PACKAGE_MANIFEST.json');checked=[];seen=set()
 names=['README.md','REPORT.md','FOR_WEB_REVIEWERS.md','CLOSED_AND_UNTESTED.md','CLOSEOUT_RECEIPT.json','FINAL_EVIDENCE_MAP.csv','FILE_MANIFEST.csv','PACKAGE_MANIFEST.json','manuscript/delivery/main_readable.md','manuscript/delivery/appendix_readable.md']+[p['path'] for p in manifest['packages']]
 for n in names:
  response=session.get(f'https://raw.githubusercontent.com/{REMOTE}/{c}/{PREFIX}/{n}',timeout=60);response.raise_for_status();data=response.content
  assert hashlib.sha256(data).hexdigest()==sha(STAGE/n),n
  checked.append(dict(path=n,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
  if n.endswith('.zip'):
   assert len(data)<=25_000_000
   with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert z.testzip() is None
    for member in z.namelist():
     safe(member);assert member not in seen;seen.add(member);p=dest/member;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(member))
  print('ANONYMOUS_READBACK_PASS',n,flush=True)
 rr=payload(dest);assert seen=={x['path'] for x in rr}|{'FILE_MANIFEST.csv'}
 validators=[]
 for script in ['verify_evidence.py','validate_manuscripts.py']:
  log=ROOT/'runtime'/('download_'+script+'.log')
  with log.open('w',encoding='utf-8') as f:result=subprocess.run([sys.executable,'-X','utf8','-B',str(dest/'reporting'/script)],cwd=dest,stdout=f,stderr=subprocess.STDOUT)
  assert result.returncode==0,(script,'see saved log');validators.append(dict(script=script,returncode=0,log_sha256=sha(log)))
  print('DOWNLOADED_VALIDATOR_PASS',script,flush=True)
 receipt=dict(status='PASS',commit=c,tag=TAG,repository=REMOTE,prefix=PREFIX,anonymous=True,authenticated_headers=False,packages=manifest['packages'],payload_files=len(seen),manifest_entries=len(rr),checked_urls=checked,validators=validators,download_directory=str(dest),verified_at=datetime.now(timezone.utc).isoformat())
 save('github_anonymous_readback.json',receipt);print('ANONYMOUS_VERIFICATION_COMPLETE',c,flush=True)
def proof():
 r=read(ROOT/'runtime/github_anonymous_readback.json');assert r['status']=='PASS';assert not git('status','--porcelain').strip()
 # 公共证明不改变已验证ZIP，故与资料清单分开：它记录的是前一个不可变载荷提交。
 public={k:v for k,v in r.items() if k!='download_directory'}
 p=REPO/PREFIX/'PUBLICATION_RECEIPT.json';p.write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
 git('-c','core.autocrlf=false','add','--',PREFIX+'/PUBLICATION_RECEIPT.json')
 assert git('diff','--cached','--name-only').decode().strip()==PREFIX+'/PUBLICATION_RECEIPT.json'
 name,email=git('show','-s','--format=%an%n%ae','HEAD').decode().strip().splitlines();git('-c','user.name='+name,'-c','user.email='+email,'commit','-m','Record anonymous verification of PP-LGCM closeout delivery')
 c=git('rev-parse','HEAD').decode().strip();helper='!"C:/Program Files/GitHub CLI/gh.exe" auth git-credential'
 git('-c','credential.helper=','-c','credential.helper='+helper,'push','origin',c+':refs/heads/main')
 s=requests.Session();s.trust_env=False;x=s.get(f'https://raw.githubusercontent.com/{REMOTE}/{c}/{PREFIX}/PUBLICATION_RECEIPT.json',timeout=60);x.raise_for_status();assert hashlib.sha256(x.content).hexdigest()==sha(p)
 save('github_publication_proof.json',dict(status='PASS',payload_commit=r['commit'],proof_commit=c,proof_sha256=sha(p)));print('PUBLIC_PROOF_VERIFIED',c,flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['check','commit','push','verify','proof']);args=parser.parse_args();globals()[args.action]()
