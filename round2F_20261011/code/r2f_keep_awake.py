"""Round2F 批次级保持唤醒与挂起记录。
run_round2F.ps1 在 P0 之前启动、汇总之后写 runtime/KEEP_AWAKE_STOP 结束；父进程消失或超过合同墙钟上限也会释放。
只调用 SetThreadExecutionState（ES_CONTINUOUS|ES_SYSTEM_REQUIRED），不改电源计划；不能阻止用户主动休眠或合盖。
每 5 秒轮询一次，两次轮询墙钟相差超过合同阈值即登记为挂起间隙，写入 runtime/keep_awake_2f.json。
用法：python r2f_keep_awake.py <R2F_ROOT> [parent_pid]
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def utc(t=None):
    return dt.datetime.fromtimestamp(time.time() if t is None else t, dt.timezone.utc).isoformat()


def alive(pid):
    if pid is None:
        return True
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        return True


def main():
    root = Path(sys.argv[1]); parent = int(sys.argv[2]) if len(sys.argv) > 2 else None
    c = json.loads((root / 'contracts/RUN_CONTRACT_2F.json').read_text(encoding='utf-8'))['budget']
    threshold, limit = float(c['suspend_gap_seconds']), float(c['wall_seconds']) + 3600
    stop, out = root / 'runtime/KEEP_AWAKE_STOP', root / 'runtime/keep_awake_2f.json'
    state = 'NOT_WINDOWS'
    if os.name == 'nt':
        import ctypes
        state = 'ON' if ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) else 'FAILED'
    start = prev = time.time(); gaps = []; reason = 'running'
    rec = lambda: {'pid': os.getpid(), 'parent_pid': parent, 'state': state, 'started_utc': utc(start), 'heartbeat_utc': utc(),
                   'gap_threshold_seconds': threshold, 'suspend_gaps': gaps, 'end_reason': reason}
    try:
        while True:
            now = time.time()
            if now - prev > threshold:
                gaps.append({'from_utc': utc(prev), 'to_utc': utc(now), 'seconds': now - prev})
            prev = now
            if stop.exists():
                reason = 'stop_flag'; break
            if not alive(parent):
                reason = 'parent_exited'; break
            if now - start > limit:
                reason = 'time_limit'; break
            tmp = out.with_suffix('.tmp'); tmp.write_text(json.dumps(rec(), indent=2), encoding='utf-8'); os.replace(tmp, out)
            time.sleep(5)
    finally:
        if os.name == 'nt' and state == 'ON':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            state = 'RELEASED'
        out.write_text(json.dumps(rec(), indent=2), encoding='utf-8')
        print('KEEP_AWAKE_END', reason, state, len(gaps), flush=True)


if __name__ == '__main__':
    main()
