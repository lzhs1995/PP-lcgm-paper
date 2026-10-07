"""原生Windows单槽位父模型准入；只读资源，不调整其他进程。"""
from pathlib import Path
import ctypes,json,datetime,psutil
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
class PerformanceInfo(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
      ['CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable','SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize']]+[(n,ctypes.c_ulong) for n in ['HandleCount','ProcessCount','ThreadCount']]
info=PerformanceInfo();info.cb=ctypes.sizeof(info)
assert ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info),ctypes.sizeof(info))
cpu=psutil.cpu_percent(interval=3)
vm=psutil.virtual_memory()
mplus=[]
for process in psutil.process_iter(['pid','name','create_time']):
    if 'mplus' in (process.info['name'] or '').lower():mplus.append(process.info)
headroom=(info.CommitLimit-info.CommitTotal)*info.PageSize/2**30
allowed=vm.available/2**30>=.5 and headroom>=1.0 and not mplus
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'available_physical_gib':vm.available/2**30,'commit_headroom_gib':headroom,
 'system_cpu_percent':cpu,'external_mplus_count':len(mplus),
 'decision':'ADMIT_ONE_SERIAL_PARENT_WORKER' if allowed else 'HOLD_RESOURCE_REVIEW',
 'scope':'One R worker and one Mplus process at a time; only after MI worker completes.',
 'rationale':'Small continuous growth parent, based on prior serial K-model calibration; not authorization for latent-interaction concurrency.',
 'action':'READ_ONLY_NO_PROCESS_CHANGE'}
(root/'runtime/resource_admission_parent.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
