"""记录本轮已经实际执行的视觉检查范围，绑定相应PDF哈希。"""
from pathlib import Path
import json,hashlib
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
exports=json.loads((root/'manuscript/native_word_export_build02.json').read_text(encoding='utf8'))
rows=[]
for e in exports:
 p=root/'manuscript'/e['pdf'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['pdf_sha256']
 rows.append({'pdf':e['pdf'],'sha256':e['pdf_sha256'],'pages_overviewed':e['pages'],'page_overview':'all contact sheets viewed','selected_detail_pages':[17] if 'review_v47' in e['pdf'] else [7],'finding':'No blank pages or gross cropping observed at reviewed scales','limits':'Not a full-cell statistical audit or complete final proofreading; original highlights and duplicate historical appendix figures remain.'})
(root/'manuscript/final_visual_review.json').write_text(json.dumps({'scope':'build02 review candidates only','documents':rows,'scientific_release':False},ensure_ascii=False,indent=2),encoding='utf8')
print('Recorded review for',sum(r['pages_overviewed'] for r in rows),'pages')
