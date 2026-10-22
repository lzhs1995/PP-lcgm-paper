"""Windows互斥准入：原子预留两个本批引擎槽，拒绝未知Mplus。"""
from pathlib import Path
from contextlib import contextmanager
import ctypes,datetime,hashlib,json,os,psutil
from ctypes import wintypes
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];K.CreateMutexW.restype=wintypes.HANDLE
K.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];K.WaitForSingleObject.restype=wintypes.DWORD
K.ReleaseMutex.argtypes=[wintypes.HANDLE];K.CloseHandle.argtypes=[wintypes.HANDLE]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

@contextmanager
def exclusive(root):
 name='Local\\PP_LGCM_INCOME_'+hashlib.sha256(str(root.resolve()).lower().encode()).hexdigest()[:24]
 h=K.CreateMutexW(None,False,name)
 if not h:raise ctypes.WinError(ctypes.get_last_error())
 acquired=False
 try:
  rc=K.WaitForSingleObject(h,30000)
  if rc not in (0,0x80):raise TimeoutError('Engine admission mutex was not acquired')
  acquired=True;yield
 finally:
  if acquired:K.ReleaseMutex(h)
  K.CloseHandle(h)

def alive(j):
 try:return abs(psutil.Process(j['pid']).create_time()-float(j['created_exact']))<1e-6
 except psutil.NoSuchProcess:return False

def admit(root,d,job,contract,profile):
 """在锁内复核实际完成及在途预留；True才允许启动一个引擎。"""
 root=Path(root);d=Path(d);leases=root/'runtime/engine_slots';leases.mkdir(parents=True,exist_ok=True)
 with exclusive(root):
  active=[]
  for p in leases.glob('*.json'):
   j=read(p)
   if (Path(j['dest'])/'engine_receipt.json').exists():continue
   if alive(j):active.append(j)
  foreign=[]
  for pid in profile['mplus_pids']:
   try:
    parents={x.pid for x in psutil.Process(pid).parents()}
    if not any(x['pid'] in parents for x in active):foreign.append(pid)
   except psutil.NoSuchProcess:pass
  calls=[read(p) for p in (root/'models').glob('*/engine_receipt.json')]
  count=sum(x.get('actual_engine_calls',0) for x in calls)
  charged=sum(x.get('active_seconds',x.get('exit_confirmed_seconds',0)) for x in calls)
  reserved=sum(x['cap_seconds'] for x in active)
  reason='ADMITTED'
  if count+len(active)>=contract['max_mplus_calls'] or charged+reserved+job['cap_seconds']>contract['total_engine_seconds']:reason='BATCH_BUDGET'
  elif len(active)>=contract['maximum_parallel_mplus']:reason='ENGINE_SLOTS_BUSY'
  elif foreign:reason='FOREIGN_OR_UNRESOLVED_MPLUS'
  # 当前测得余量已经包含现有分配，另预留尚未分配的最大增量。
  elif profile['available_gib']<contract['minimum_available_gib']+(len(active)+1)*contract['engine_incremental_gib']:reason='PHYSICAL_HEADROOM'
  elif profile['commit_available_gib']<contract['minimum_commit_available_gib']+(len(active)+1)*contract['engine_incremental_commit_gib']:reason='COMMIT_HEADROOM'
  elif profile['cpu_percent']>contract['max_cpu_percent']:reason='CPU_BUSY'
  rec=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=reason,profile=profile,active_slots=len(active),foreign_mplus=foreign,completed_calls=count,charged_seconds=charged,reserved_seconds=reserved)
  if reason=='ADMITTED':
   p=psutil.Process();lease=dict(pid=p.pid,created_exact=format(p.create_time(),'.17g'),dest=str(d),id=job['id'],cap_seconds=job['cap_seconds'])
   with (leases/(job['id']+'.json')).open('x') as f:json.dump(lease,f,indent=2)
  return reason=='ADMITTED',rec
