"""Windows单槽资源检查；只读其他进程，不修改或结束用户会话。"""
import ctypes
import datetime
import json
import sys
from pathlib import Path
import psutil

class PerformanceInfo(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong)] + [(n, ctypes.c_size_t) for n in
        ['CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable','SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize']] + [(n, ctypes.c_ulong) for n in ['HandleCount','ProcessCount','ThreadCount']]

info = PerformanceInfo()
info.cb = ctypes.sizeof(info)
assert ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info), ctypes.sizeof(info))
vm = psutil.virtual_memory()
cpu = psutil.cpu_percent(interval=1)
mp = [p.info for p in psutil.process_iter(['pid','name']) if 'mplus' in (p.info['name'] or '').lower()]
headroom = (info.CommitLimit-info.CommitTotal)*info.PageSize/2**30
maintenance = Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008/runtime/PAUSE_FOR_CODE_UPDATE').exists()
ok = vm.available/2**30 >= .5 and headroom >= 1 and cpu < 85 and not mp and not maintenance
out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           available_physical_gib=vm.available/2**30,commit_headroom_gib=headroom,
           system_cpu_percent=cpu,external_mplus_count=len(mp),admit=ok,
           maintenance_hold=maintenance, action='READ_ONLY_NO_PROCESS_CHANGE')
Path(sys.argv[1]).write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
