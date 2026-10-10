"""Round2E 单槽资源检查（移植自Round2D resource_gate.py）：只读其他进程，不修改或结束任何进程。
用法：python r2e_resource_gate.py <输出json> <暂停标记文件>"""
import datetime
import json
import sys
from pathlib import Path
import psutil

vm = psutil.virtual_memory()
cpu = psutil.cpu_percent(interval=1)
mp = [p.info for p in psutil.process_iter(['pid', 'name']) if 'mplus' in (p.info['name'] or '').lower()]
pause = Path(sys.argv[2]).exists()
ok = vm.available / 2**30 >= .5 and cpu < 85 and not mp and not pause
out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), available_physical_gib=vm.available / 2**30,
           system_cpu_percent=cpu, external_mplus_count=len(mp), external_mplus=mp, pause_flag=pause, admit=ok,
           physical_cores=psutil.cpu_count(logical=False), logical_cores=psutil.cpu_count(logical=True),
           total_physical_gib=vm.total / 2**30, action='READ_ONLY_NO_PROCESS_CHANGE')
Path(sys.argv[1]).write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out))
