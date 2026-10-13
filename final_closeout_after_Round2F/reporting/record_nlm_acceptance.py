"""仅在人工证据裁决与原始NLM结果均满足合同后，记录最终PDF验收。"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
adjudication=read(ROOT/'reports/NLM_ADJUDICATION.json')
rounds=[]
for entry in adjudication['accepted_rounds']:
 number=entry['round'];rd=ROOT/'runtime/nlm'/f'round_{number:02d}';result=read(rd/'result.json')
 assert result['result']['status']=='PASS' and entry['status']=='ACCEPTED'
 attempt=result['result']['attempts'][-1];assert attempt['exit_code']==0 and attempt['validation']['status']=='PASS'
 raw=rd/'query/attempt-01.raw.txt';data=read(raw)
 count=int(re.search(r'NEW_ISSUES_COUNT\s*:\s*(\d+)',data['answer']).group(1))
 no_new=re.search(r'A5_NO_NEW_ISSUES\s*:\s*(YES|NO)',data['answer']).group(1)
 assert count==entry['new_issues_count'] and no_new==entry['a5_no_new_issues']
 dest=ROOT/'reports/nlm'/f'round_{number:02d}';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(raw,dest/'raw_response.json');shutil.copy2(rd/'sources.json',dest/'sources.json');shutil.copy2(rd/'prompt.txt',dest/'prompt.txt')
 rounds.append({'round':number,'focus':result['focus'],'full_scan':True,'sources':result['sources'],
  'raw_path':(dest/'raw_response.json').relative_to(ROOT).as_posix(),'raw_sha256':sha(raw),'returncode':0,
  'review_validated':True,'new_issues_count':count,'a5_no_new_issues':no_new,'issue_keys':entry['issue_keys']})
assert {r['focus'] for r in rounds}=={'structure','methods','final'}
assert all(r['new_issues_count']==0 and r['a5_no_new_issues']=='YES' for r in rounds[-2:])
pdfs=[{'pdf':p.name,'sha256':sha(p)} for p in sorted((ROOT/'manuscript/delivery').glob('*.pdf'))]
assert len(pdfs)==2
audit={'status':'PASS','pdf_only':True,'pdfs':pdfs,'completed_passes':['structure','methods','final'],
 'open_actionable_issues':0,'rounds':rounds,'a5':{'termination':'TWO_CONSECUTIVE_NO_NEW','rounds':[r['round'] for r in rounds[-2:]]},
 'excluded_attempts':adjudication['excluded_attempts'],'review_limits':'NLM审阅不代替本地逐格/来源验证或逐页视觉审查；不证明原最大研究目标已完成。',
 'recorded_utc':datetime.now(timezone.utc).isoformat()}
dump(ROOT/'reports/NLM_FINAL_AUDIT.json',audit)
import publication_gate
check=publication_gate.check(ROOT)
print(json.dumps(check,ensure_ascii=False))
