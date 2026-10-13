"""对引用修复前后PDF逐页作像素比较，限定需放大复看的页面。"""
from pathlib import Path
import hashlib,json,fitz
ROOT=Path(__file__).resolve().parents[1];out=[]
for name in ['PP_LGCM_scoped_final_candidate.pdf','PP_LGCM_scoped_supplement.pdf']:
 old=ROOT/'runtime/before_citation_repair'/name;new=ROOT/'manuscript/delivery'/name
 with fitz.open(old) as a,fitz.open(new) as b:
  assert len(a)==len(b)
  rows=[]
  for i in range(len(a)):
   hashes=[]
   for pdf in [a,b]:
    pix=pdf[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
    hashes.append(hashlib.sha256(pix.samples).hexdigest())
   rows.append({'page':i+1,'old_pixel_sha256':hashes[0],'new_pixel_sha256':hashes[1],'unchanged':hashes[0]==hashes[1]})
 out.append({'pdf':name,'pages':rows,'changed_pages':[r['page'] for r in rows if not r['unchanged']]})
(ROOT/'reports/PDF_PAGE_COMPARISON.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps([{'pdf':r['pdf'],'changed_pages':r['changed_pages']} for r in out]))
