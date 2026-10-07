"""原生Windows单槽位资源准入；不结束或调整其他任务。"""
from pathlib import Path
import ctypes,json,datetime,psutil
root=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007')
class PerformanceInfo(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable','SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize']]+[(n,ctypes.c_ulong) for n in ['HandleCount','ProcessCount','ThreadCount']]
info=PerformanceInfo();info.cb=ctypes.sizeof(info)
assert ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info),ctypes.sizeof(info))
cpu=psutil.cpu_percent(interval=3);vm=psutil.virtual_memory()
mp=[p.info for p in psutil.process_iter(['pid','name','create_time']) if 'mplus' in (p.info['name'] or '').lower()]
headroom=(info.CommitLimit-info.CommitTotal)*info.PageSize/2**30
ok=vm.available/2**30>=.5 and headroom>=1 and cpu<85 and not mp
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'available_physical_gib':vm.available/2**30,'commit_headroom_gib':headroom,'system_cpu_percent':cpu,'external_mplus_count':len(mp),'decision':'ADMIT_ONE_SERIAL_WORKER' if ok else 'HOLD_RESOURCE_REVIEW','action':'READ_ONLY_NO_PROCESS_CHANGE'}
(root/'runtime/resource_admission.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
