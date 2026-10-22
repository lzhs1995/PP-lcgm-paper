"""原生工具回执登记；绝不代造原生调用。"""
from pathlib import Path
import contextlib, io, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, 'C:/Users/LZHS/.codex/skills/clauder-rstudio-workbench')
from clauder_workbench.cli import main
label, *args = sys.argv[1:]
target = ROOT / 'audit' / (label + '.json')
target.parent.mkdir(parents=True, exist_ok=True)
assert not target.exists(), 'Preserve existing evidence; do not overwrite'
capture = io.StringIO()
with contextlib.redirect_stdout(capture):
    result = main(args)
target.write_text(capture.getvalue(), encoding='utf-8')
doc = json.loads(capture.getvalue())
print(json.dumps({k: doc.get(k) for k in ('decision','evidence_id','reasons','policy_violations')}, ensure_ascii=False), flush=True)
raise SystemExit(result)
