"""直接子进程句柄+清醒时间预算；墙钟和实际睡眠排除量同时保留。"""
from pathlib import Path
import math,subprocess,time
from active_clock import BudgetClock
def run_child(command,directory,timeout_seconds,working_directory=None):
 if not math.isfinite(timeout_seconds) or timeout_seconds<=0:raise ValueError('Positive finite limit required')
 d=Path(directory);d.mkdir(parents=True,exist_ok=False);clock=BudgetClock();started=time.monotonic();detected=None;kill_requested=None;state='EXITED'
 with (d/'stdout.log').open('xb') as out,(d/'stderr.log').open('xb') as err:
  p=subprocess.Popen(command,cwd=working_directory or d,stdin=subprocess.DEVNULL,stdout=out,stderr=err,shell=False);launched=time.monotonic()
  while p.poll() is None:
   timing=clock.sample();remaining=timeout_seconds-timing['active_seconds']
   if remaining<=0:
    detected=time.monotonic();state='TIMEOUT';kill_requested=time.monotonic();p.kill();p.wait(timeout=10);break
   try:p.wait(timeout=min(1,remaining))
   except subprocess.TimeoutExpired:pass
  exited=time.monotonic();timing=clock.sample()
 return dict(state=state,pid=p.pid,exitcode=p.returncode,configured_seconds=timeout_seconds,configured_timebase='Windows awake time with recorded Modern Standby exclusion',launch_seconds=launched-started,detected_seconds=None if detected is None else detected-started,kill_requested_seconds=None if kill_requested is None else kill_requested-started,exit_confirmed_seconds=exited-started,process_exited=p.poll() is not None,direct_child_only=True,**timing)
