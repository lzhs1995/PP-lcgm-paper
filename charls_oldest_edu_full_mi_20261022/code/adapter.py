"""完整潜交互家族的有界引擎准入；仅操作本调用直接子进程。"""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,sys,time,psutil
from bounded_child_awake import run_child
from active_clock import BudgetClock
from engine_slots import admit
R=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,j):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(j,indent=2))
 for attempt in range(20):
  try:os.replace(tmp,p);return
  except PermissionError:
   if attempt==19:raise
   time.sleep(.05*(attempt+1))
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ['total','avail','commit_limit','commit_avail','virtual','virtual_avail','extended']]
def resource():
 m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 return dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),available_gib=m.avail/2**30,commit_available_gib=m.commit_avail/2**30,cpu_percent=psutil.cpu_percent(.3),mplus_pids=[p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='mplus.exe'])
def main():
 d=Path(sys.argv[1]).resolve().parent;j=read(d/'job.json');c=read(R/'contracts/RUN_CONTRACT.json');z=j['indicator']
 assert d.parent==R/'models' and Path(sys.argv[2]).name=='model.inp'
 assert not (d/'execution').exists() and not (d/'engine_receipt.json').exists()
 for n,h in j['hashes'].items():assert sha(d/n)==h
 assert sha(c['executable'])==c['executable_sha256']
 for name,h in c['source_hashes'].items():assert sha(Path(c['source'])/name)==h
 assert j['id'] in c['sequence']
 with (d/'RESERVATION.json').open('x') as f:json.dump(dict(pid=os.getpid(),created_exact=format(psutil.Process().create_time(),'.17g')),f)
 clock=BudgetClock()
 while True:
  okay,rec=admit(R,d,j,c,resource())
  if okay:break
  with (d/'ADMISSION_HISTORY.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
  if rec['reason']=='BATCH_BUDGET' or clock.sample()['active_seconds']>=c['resource_wait_seconds']:
   save(d/'engine_receipt.json',dict(status='NOT_RUN_RESOURCE_HOLD',actual_engine_calls=0,admission=rec));return 75
  time.sleep(2)
 save(d/'RESOURCE_ADMITTED.json',rec)
 awake=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
 try:
  out=run_child([c['executable'],'model.inp'],d/'execution',j['cap_seconds'],working_directory=d)
  out.update(status=out['state'],actual_engine_calls=1,input_sha256=j['hashes']['model.inp'],data_sha256=j['hashes']['data.dat'],stdout_sha256=sha(d/'execution/stdout.log'),stderr_sha256=sha(d/'execution/stderr.log'))
  save(d/'engine_receipt.json',out);return 124 if out['state']=='TIMEOUT' else out['exitcode']
 finally:
  if awake:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
if __name__=='__main__':raise SystemExit(main())
