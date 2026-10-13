"""对新版PDF记录已查看的改变页面及38页像素一致的复用证据。"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'manuscript/delivery'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior=read(ROOT/'runtime/before_citation_repair/visual_review.json');assert prior['status']=='PASS'
diff=read(ROOT/'reports/PDF_PAGE_COMPARISON.json')
assert diff[0]['changed_pages']==[2] and diff[1]['changed_pages']==[31,32,33]
record={'status':'PASS','reviewed_utc':datetime.now(timezone.utc).isoformat(),
 'method':'Prior full 42-page contact-sheet visual review, byte-bound old PDFs, pixel-identical reuse of 38 pages, enlarged visual inspection of all 4 changed pages after native Word export.',
 'documents':[], 'findings':[], 'limitations':'Contact-sheet review of unchanged pages does not claim every page was inspected at full resolution. Changed pages were enlarged. NLM acceptance is separate.'}
for i,stem in enumerate(['PP_LGCM_scoped_final_candidate','PP_LGCM_scoped_supplement']):
 old=next(x for x in prior['documents'] if x['pdf']==stem+'.pdf')
 assert old['pdf_sha256']==sha(ROOT/'runtime/before_citation_repair'/(stem+'.pdf'))
 record['documents'].append({'pdf':stem+'.pdf','pdf_sha256':sha(OUT/(stem+'.pdf')),
 'pages_reviewed':list(range(1,len(diff[i]['pages'])+1)),'enlarged_pages':diff[i]['changed_pages'],
 'unchanged_pages_reused':[r['page'] for r in diff[i]['pages'] if r['unchanged']],
 'prior_pdf_sha256':old['pdf_sha256'],'result':'No clipping, overlap, missing content or footer collision found'})
(OUT/'visual_review.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('VISUAL_PASS_CHANGED_4_UNCHANGED_38')
