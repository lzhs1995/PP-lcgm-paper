"""仅在本任务导出和上传期间阻止空闲休眠；完成标记或两小时后释放。"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes
import json
import os
import time

root=Path(__file__).resolve().parents[1]
start=time.time()
flag=0x80000001
result=ctypes.windll.kernel32.SetThreadExecutionState(flag)
assert result,'SetThreadExecutionState failed'
(root/'runtime/delivery_awake.json').write_text(json.dumps(dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
  duration_limit_seconds=7200,scope='thread execution state; system required during export/upload')),encoding='utf-8')
print('DELIVERY_AWAKE_ACTIVE',flush=True)
try:
    while time.time()-start<7200 and not (root/'runtime/DELIVERY_DONE').exists():time.sleep(10)
finally:
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    print('DELIVERY_AWAKE_RELEASED',flush=True)
