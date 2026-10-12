"""简短只读快照；不启动作业、不改写队列。"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
S=read(ROOT/'runtime/selection_2f.json')
out={'progress':read(ROOT/'runtime/progress.json'),'decision':S.get('decision'),'terminal':S.get('terminal')}
for step in ['F1','F2']:
 P=S.get(step,{})
 out[step]={'passed':P.get('passed'),'start':P.get('start_check'),
    'integration_a':P.get('integration_a'),'integration_b':P.get('integration_b'),
    'runs':[{k:v for k,v in r.items() if k in ['id','status','LL','sy','seconds']} for r in P.get('runs',{}).values()]}
out['families']={k:{'status':f['status'],'members':{i:r['status'] for i,r in f['members'].items()}} for k,f in (S.get('families') or {}).items()}
out['budget']={k:v for k,v in read(ROOT/'runtime/budget_status.json').items() if k!='rows'}
print(json.dumps(out,ensure_ascii=False,indent=2))
