"""Windows原生解释器核验待发布guide；不启动R或Mplus。"""
from pathlib import Path
import importlib.util,inspect,json,sys,tempfile,time,unittest,os,shutil
ROOT=Path(__file__).resolve().parents[1]
REPO=Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/mplusautomation_closeout_20261013')
sys.path.insert(0,str(REPO/'skills/clauder-rstudio-workbench'))
os.chdir(REPO)
# 复用已有工具环境中的纯Python依赖，不变更系统环境。
extra=Path('C:/Users/LZHS/AppData/Roaming/uv/tools/notebooklm-mcp-cli/Lib/site-packages')
if extra.exists():sys.path.append(str(extra))
for old in [ROOT/'runtime/guide_unittest.log', ROOT/'reports/GUIDE_UNITTEST.json']:
 if old.exists():shutil.copy2(old,ROOT/'runtime'/(str(time.time_ns())+'_'+old.name))
started=time.monotonic()
suite=unittest.defaultTestLoader.discover(str(REPO/'tests'),pattern='test_*.py')
with (ROOT/'runtime/guide_unittest.log').open('w',encoding='utf-8') as log:
 result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
record={'status':'PASS' if result.wasSuccessful() else 'FAIL','runner':'Windows Python unittest discovery',
 'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
 'elapsed_seconds':round(time.monotonic()-started,2),'log':'runtime/guide_unittest.log','new_mplus_calls':0,
 'failed_tests':[str(t) for t,_ in result.failures+result.errors]}
(ROOT/'reports/GUIDE_UNITTEST.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
sys.exit(0 if result.wasSuccessful() else 1)
