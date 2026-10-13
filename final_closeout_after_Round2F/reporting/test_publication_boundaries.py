"""针对独立审计发现的发布边界，使用隔离复制验证拒绝行为。"""
from pathlib import Path
import copy, hashlib, json, shutil, tempfile
import publication_gate, public_file_selection
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,j): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
def reject(name, fn):
 try: fn()
 except (AssertionError,FileNotFoundError): results.append(dict(test=name,status='PASS',behavior='REJECTED'))
 else: raise AssertionError(name+' unexpectedly accepted')
with tempfile.TemporaryDirectory(prefix='release_gate_',dir=ROOT/'runtime') as temp:
 root=Path(temp);delivery=root/'manuscript/delivery';delivery.mkdir(parents=True)
 for p in (ROOT/'manuscript/delivery').iterdir():
  if p.suffix in {'.docx','.pdf'} or p.name in {'visual_review.json','manuscript_validation.json'}:shutil.copy2(p,delivery/p.name)
 audit=read(ROOT/'reports/NLM_FINAL_AUDIT.json')
 for r in audit['rounds']:
  dest=root/r['raw_path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/r['raw_path'],dest)
 target=root/'reports/NLM_FINAL_AUDIT.json';dump(target,audit)
 publication_gate.check(root);results.append(dict(test='actual_final_rounds_5_to_9',status='PASS',behavior='ACCEPTED'))
 gap=copy.deepcopy(audit);gap['rounds']=[r for r in gap['rounds'] if r['round']!=7];dump(target,gap)
 reject('omitted_intervening_round',lambda: publication_gate.check(root))
 dishonest=copy.deepcopy(audit);r=next(x for x in dishonest['rounds'] if x['round']==7);r['new_issues_count']=0;r['a5_no_new_issues']='YES';dump(target,dishonest)
 reject('metadata_disagrees_with_hashed_raw',lambda: publication_gate.check(root))
 wrong=copy.deepcopy(audit);wrong['a5']['rounds']=[6,8];dump(target,wrong)
 reject('a5_round_identity_mismatch',lambda: publication_gate.check(root))
 dump(target,audit);pdf=delivery/'PP_LGCM_scoped_final_candidate.pdf';pdf.write_bytes(pdf.read_bytes()+b'\nchanged')
 reject('pdf_changed_after_review',lambda: publication_gate.check(root))
 stage=root/'selection';stage.mkdir();aggregate=stage/'aggregate.csv';aggregate.write_text('parameter,estimate\nbii,-0.35\n')
 selection=dict(status='APPROVED_AGGREGATE_ONLY',files=[dict(path='aggregate.csv',bytes=aggregate.stat().st_size,sha256=sha(aggregate),classification='aggregate_evidence')])
 dump(stage/public_file_selection.NAME,selection);(stage/'.gitattributes').write_text('* -text\n')
 public_file_selection.verify_stage(stage);results.append(dict(test='exact_approved_aggregate_set',status='PASS',behavior='ACCEPTED'))
 unlisted=stage/'per_person.csv';unlisted.write_text('subject_key,factor_score\nsynthetic_a,0.2\n')
 reject('unlisted_file_with_unrecognized_identifier_alias',lambda: public_file_selection.verify_stage(stage));unlisted.unlink()
 aggregate.write_text('subject_key,factor_score\nsynthetic_a,0.2\n')
 reject('changed_previously_approved_file',lambda: public_file_selection.verify_stage(stage))
out=dict(status='PASS',tests=len(results),results=results,scope='No NLM, R, Mplus or publication; temporary synthetic/aggregate copies only',
 source_hashes={n:sha(ROOT/'reporting'/n) for n in ['publication_gate.py','public_file_selection.py','package_closeout.py','privacy_scan.py']})
dump(ROOT/'reports/PUBLICATION_BOUNDARY_TESTS.json',out)
print(json.dumps(out,ensure_ascii=False))
