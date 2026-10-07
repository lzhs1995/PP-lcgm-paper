"""仅发布已通过本地验收的Round2B资料，原子推送并匿名读回。"""
from pathlib import Path
import subprocess,shutil,json,hashlib,sys,requests
from datetime import datetime,timezone
ROOT=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');STAGE=ROOT/'public_stage'
REPO=Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/cfps_review_20261005/github_publish')
GIT='C:/Program Files/Git/cmd/git.exe';PREFIX='round2B_20261006';TAG='review-round2B-20261006';OLD='20225eb97b4cf630440001c1f351dbabb4b84f56'
def git(*args):
 r=subprocess.run([GIT,'-C',str(REPO),*args],capture_output=True)
 if r.returncode:raise RuntimeError(r.stderr.decode('utf8',errors='replace'))
 return r.stdout
def save(name,obj):(ROOT/'runtime'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def prepare_commit():
 assert json.loads((ROOT/'runtime/package_validation.json').read_text(encoding='utf8'))['status']=='PASS'
 assert json.loads((STAGE/'DELIVERY_SCOPE.json').read_text(encoding='utf8'))['ready_for_publication'] is True
 assert git('rev-parse','HEAD').decode().strip()==OLD
 assert git('ls-remote','origin','refs/heads/main').decode().split()[0]==OLD
 assert not git('ls-remote','origin',f'refs/tags/{TAG}').strip()
 assert not git('diff','--cached','--name-only').strip(),'Unrelated staged changes'
 assert not git('status','--porcelain').strip(),'Working tree changed; review before publishing'
 dest=REPO/PREFIX;assert not dest.exists(),'Existing target requires explicit resume review'
 shutil.copytree(STAGE,dest)
 (dest/'.gitattributes').write_bytes(b'* -text\n')
 readme=REPO/'README.md';old=readme.read_bytes();(ROOT/'runtime/repository_README_before.md').write_bytes(old)
 notice=f'最新复核资料：[PP-LGCM Round2B报告与读取说明]({PREFIX}/README.md)。统计状态以该目录的REPORT和DELIVERY_SCOPE为准；历史资料继续保留。\n\n'
 readme.write_bytes(notice.encode('utf8')+old)
 expected={p.relative_to(REPO).as_posix() for p in dest.rglob('*') if p.is_file()}|{'README.md'}
 git('-c','core.autocrlf=false','add','-f','--',PREFIX,'README.md')
 changed=set(filter(None,git('diff','--cached','--name-only','-z').decode().split('\0')));assert changed==expected
 blobs={}
 for item in git('ls-files','--stage','-z').split(b'\0'):
  if item:
   header,path=item.split(b'\t',1);blobs[path.decode()]=header.decode().split()[1]
 for name in changed:
  b=(REPO/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blobs[name],name
 name,email=git('show','-s','--format=%an%n%ae',OLD).decode().strip().splitlines()
 git('-c',f'user.name={name}','-c',f'user.email={email}','commit','-m','Publish PP-LGCM Round 2B verification evidence and review candidates')
 commit=git('rev-parse','HEAD').decode().strip();git('tag',TAG,commit)
 save('github_local_commit.json',{'commit':commit,'tag':TAG,'previous':OLD,'files':len(changed)})
 print('LOCAL_COMMIT',commit,flush=True)
def push():
 r=json.loads((ROOT/'runtime/github_local_commit.json').read_text(encoding='utf8'));commit=r['commit']
 assert git('rev-parse',TAG).decode().strip()==commit
 remote=git('ls-remote','origin','refs/heads/main').decode().split()[0];assert remote in {OLD,commit}
 helper='!"C:/Program Files/GitHub CLI/gh.exe" auth git-credential'
 git('-c','credential.helper=','-c',f'credential.helper={helper}','push','--atomic','origin',f'{commit}:refs/heads/main',f'refs/tags/{TAG}:refs/tags/{TAG}')
 save('github_push_receipt.json',{'status':'PUSHED',**r,'utc':datetime.now(timezone.utc).isoformat()});print('PUSHED',commit,flush=True)
def verify():
 r=json.loads((ROOT/'runtime/github_local_commit.json').read_text(encoding='utf8'));commit=r['commit']
 refs=git('ls-remote','origin','refs/heads/main',f'refs/tags/{TAG}').decode().splitlines();assert len(refs)==2 and all(x.split()[0]==commit for x in refs)
 s=requests.Session();s.trust_env=False;s.headers['User-Agent']='PP-LGCM-public-evidence-verifier'
 url=f'https://api.github.com/repos/lzhs1995/PP-lcgm-paper/git/trees/{commit}?recursive=1'
 response=s.get(url,timeout=60);response.raise_for_status();data=response.json();assert not data.get('truncated')
 remote={x['path']:x['sha'] for x in data['tree'] if x['type']=='blob'};local={}
 for item in git('ls-tree','-r','-z',commit).split(b'\0'):
  if item:
   info,path=item.split(b'\t',1);mode,kind,oid=info.decode().split()
   if kind=='blob':local[path.decode()]=oid
 assert local==remote
 pkg=json.loads((REPO/PREFIX/'PACKAGE_MANIFEST.json').read_text(encoding='utf8'))
 selected=['README.md']+[f'{PREFIX}/{p}' for p in ['README.md','REPORT.md','FOR_WEB_REVIEWERS.md','DELIVERY_SCOPE.json','SEVEN_ISSUES.csv','MODEL_INDEX.md','FILE_MANIFEST.csv','PACKAGE_MANIFEST.json']+[x['path'] for x in pkg['packages']]]
 checked=[]
 for name in selected:
  response=s.get(f'https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/{commit}/{name}',timeout=60);response.raise_for_status()
  h=hashlib.sha256(response.content).hexdigest();assert h==hashlib.sha256((REPO/name).read_bytes()).hexdigest(),name
  checked.append({'path':name,'bytes':len(response.content),'sha256':h});print('READBACK_PASS',name,flush=True)
 save('github_anonymous_readback.json',{'status':'PASS','commit':commit,'tag':TAG,'anonymous':True,'git_blobs_verified':len(remote),'files':checked,'utc':datetime.now(timezone.utc).isoformat()})
 print('VERIFIED',commit,flush=True)
if __name__=='__main__':{'commit':prepare_commit,'push':push,'verify':verify}[sys.argv[1]]()
