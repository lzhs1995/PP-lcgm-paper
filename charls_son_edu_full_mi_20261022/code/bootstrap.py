"""原生 RStudio worker 身份与来源合同预检。"""
from pathlib import Path
import datetime,hashlib,json,os,sys,psutil
R=Path(__file__).resolve().parents[1]; read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig')); sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert len(sys.argv)==3
pid=int(sys.argv[1]); nonce=sys.argv[2]; c=read(R/'contracts/RUN_CONTRACT.json'); mi=Path(c['MI_root'])
p=psutil.Process(pid); assert p.is_running() and p.name().lower() in ('rscript.exe','rterm.exe')
assert p.ppid()==9652
args=p.cmdline(); assert '-f' in args and Path(args[args.index('-f')+1]).is_file()
assert read(mi/'audit/INDEPENDENT_MI.json')['status']=='PASS_INDEPENDENT_WORKING_MI'
assert sha(mi/'contracts/RUN_CONTRACT.json')==c['MI_contract_sha256'] and sha(mi/'audit/INDEPENDENT_MI.json')==c['MI_verification_sha256']
assert sha(c['executable'])==c['executable_sha256']
for n,h in c['source_hashes'].items(): assert sha(Path(c['source'])/n)==h
source_b=Path(c['source']).parent/'H42_GH15_B'
for n,h in c['source_B_hashes'].items(): assert sha(source_b/n)==h
out={'status':'PASS','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker':{'pid':pid,'created':p.create_time(),'name':p.name(),'parent':p.ppid(),'script':args[args.index('-f')+1]},'nonce':nonce,'source_hashes_verified':True,'MI_verification':'PASS_INDEPENDENT_WORKING_MI','N':2263,'communities':433,'m':20}
tmp=R/'audit/PREFLIGHT.tmp';tmp.write_text(json.dumps(out,indent=2),encoding='utf-8');os.replace(tmp,R/'audit/PREFLIGHT.json');print(json.dumps(out),flush=True)
