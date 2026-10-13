"""最终发布需对应同一PDF版本的视觉与NLM原始证据，不能仅依据完成标签。"""
import hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check(root):
 root=Path(root);delivery=root/'manuscript/delivery'
 visual=read(delivery/'visual_review.json');assert visual['status']=='PASS'
 reviewed={d['pdf']:d['pdf_sha256'] for d in visual['documents']}
 assert len(reviewed)==2
 for name,h in reviewed.items():assert sha(delivery/name)==h,('visual hash',name)
 validation=read(delivery/'manuscript_validation.json');assert validation['status']=='PASS'
 for r in validation['results']:
  name='PP_LGCM_scoped_final_candidate' if r['kind']=='main' else 'PP_LGCM_scoped_supplement'
  assert sha(delivery/(name+'.docx'))==r['docx_sha256']
  assert sha(delivery/(name+'.pdf'))==r['pdf_sha256']
 audit=read(root/'reports/NLM_FINAL_AUDIT.json');assert audit['status']=='PASS' and audit['pdf_only']
 assert {d['pdf']:d['sha256'] for d in audit['pdfs']}==reviewed,'NLM PDF pair mismatch'
 assert set(audit['completed_passes'])=={'structure','methods','final'}
 assert audit['open_actionable_issues']==0
 rounds=audit['rounds'];assert len(rounds)>=3
 numbers=[r['round'] for r in rounds]
 assert numbers==list(range(numbers[0],numbers[-1]+1)), 'Review rounds must be consecutive and ordered'
 assert {r['focus'] for r in rounds}==set(audit['completed_passes'])
 for r in rounds:
  assert {s['pdf']:s['sha256'] for s in r['sources']}==reviewed
  assert len(set(s['id'] for s in r['sources']))==2
  raw=root/r['raw_path'];assert sha(raw)==r['raw_sha256']
  response=read(raw);ids={s['id'] for s in r['sources']}
  counts=re.findall(r'NEW_ISSUES_COUNT\s*:\s*(\d+)',response['answer'])
  markers=re.findall(r'A5_NO_NEW_ISSUES\s*:\s*(YES|NO)',response['answer'])
  assert len(counts)==len(markers)==1, 'Unambiguous raw review markers required'
  assert int(counts[0])==r['new_issues_count'] and markers[0]==r['a5_no_new_issues'], 'Raw review and metadata disagree'
  assert ids<=set(response['sources_used']) and response['answer'].strip()
  assert ids<=set(response['citations'].values()),'Native source citations missing'
  assert ids<={x['source_id'] for x in response['references']},'Source excerpts missing'
  assert r['returncode']==0
  assert r['review_validated']
 a5=audit['a5'];tail=rounds[-2:]
 if a5['termination']=='TWO_CONSECUTIVE_NO_NEW':
  assert a5['rounds']==numbers[-2:], 'A5 round identities disagree'
  assert all(r['full_scan'] and r['new_issues_count']==0 and r['a5_no_new_issues']=='YES' for r in tail)
  assert {s['id'] for s in tail[0]['sources']}.isdisjoint({s['id'] for s in tail[1]['sources']}),'A5 requires fresh uploads'
 elif a5['termination']=='THREE_SAME_ADJUDICATED':
  assert a5['rounds']==numbers[-3:], 'A5 round identities disagree'
  last=rounds[-3:];assert all(r['full_scan'] for r in last)
  assert last[0]['issue_keys']==last[1]['issue_keys']==last[2]['issue_keys']
  assert a5['supervisor_adjudication']
 else:raise AssertionError('A5 termination missing')
 return {'status':'PASS','pdfs':reviewed,'rounds':len(rounds),'a5':a5['termination'],'audit_sha256':sha(root/'reports/NLM_FINAL_AUDIT.json')}
if __name__=='__main__':print(json.dumps(check(Path(__file__).resolve().parents[1]),ensure_ascii=False))
