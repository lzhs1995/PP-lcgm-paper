"""用已安装共享 harness 保留本轮执行证据，不改变配置。"""
import runpy
import sys
import json
import subprocess
from pathlib import Path
sys.path.insert(0, r"C:\Users\LZHS\.agents\skills\clauder-rstudio-workbench")
if sys.argv[1:] == ["record-review-smoke"]:
    root=Path(r"C:\Users\LZHS\pp_lgcm_review\20261005\native")
    for step, raw, extra in [
        ("list_sessions", "list_sessions_raw.json", []),
        ("execute_r", "execute_r_raw.json", ["--marker", "NATIVE_EXECUTE_OK", "--pid", "28936"]),
        ("execute_r_async", "execute_r_async_raw.json", ["--job-id", "15583b06"]),
        ("get_async_result", "get_async_result_raw.json", ["--job-id", "15583b06", "--marker", "NATIVE_ASYNC_DONE"]),
    ]:
        args=[sys.executable,"-X","utf8",__file__,"native-smoke","record","--task-key","cfps-review-20261005","--step",step,"--ok","--session-name","default","--raw-file",str(root/raw)]+extra
        r=subprocess.run(args,capture_output=True,text=True,encoding="utf-8",check=True)
        value=json.loads(r.stdout);print(step,value["decision"])
    sys.argv=[__file__,"native-smoke","complete","--task-key","cfps-review-20261005"]
runpy.run_module("clauder_workbench", run_name="__main__")
