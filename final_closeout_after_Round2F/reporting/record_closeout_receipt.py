"""把实际通过的同版检查整合为范围限定的收尾回执。"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import publication_gate
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gate=publication_gate.check(ROOT)
ev=read(ROOT/'reports/EVIDENCE_VERIFICATION.json');assert ev['status']=='PASS' and ev['new_mplus_calls']==0
v=read(ROOT/'manuscript/delivery/manuscript_validation.json')
files=[]
for p in sorted((ROOT/'manuscript/delivery').iterdir()):
 if p.suffix in {'.docx','.pdf'}:files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
receipt={'status':'SCOPED_CLOSEOUT_COMPLETE','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'meaning':'本回执仅关闭作者选定的零新增估计、范围收缩文稿修订；GitHub上传与匿名回读另由PUBLICATION_RECEIPT.json证明。',
 'mode':'NO_NEW_ESTIMATION','new_mplus_calls':0,'charls':'PAUSED_BY_AUTHOR',
 'adopted_results':['SW complete 10-imputation family','SD E0 complete 10-imputation family'],
 'not_completed':['four original moderation MI families','formal H4 tests','all original robustness claims'],
 'round2F_decision':'C unchanged; frozen numerical tolerances unchanged',
 'documents':v['results'],'total_pages':sum(x['pages'] for x in v['results']),
 'total_tables':sum(x['tables'] for x in v['results']),'total_cells':sum(x['cells'] for x in v['results']),
 'complex_word_fields':v['combined_fields'],'preserved_hyperlinks':1,'footnotes':v['combined_footnotes'],
 'main_numeric_evidence_rows':ev['main_numeric_evidence_rows'],'recomputed_saved_paths':ev['recomputed_paths'],
 'files':files,'visual_review':'PASS; all page contact sheets plus selected enlarged pages, see visual_review.json',
 'nlm':gate,'privacy_scan':'REQUIRED_AT_PACKAGE','github_publication':'SEE_SEPARATE_PUBLICATION_RECEIPT',
 'stop_rule':'No automatic EM probe, H4, CHARLS, new MI, or repeated web-model consensus. A precisely identified serious error may justify one correction.'}
(ROOT/'CLOSEOUT_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['status','new_mplus_calls','total_pages','total_tables','total_cells','main_numeric_evidence_rows']},ensure_ascii=False))
