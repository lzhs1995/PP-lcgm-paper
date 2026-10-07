"""逐页提取原生PDF文本、渲染缩略图并生成可审阅证据。"""
from pathlib import Path
import fitz,json,hashlib,sys
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');records=[]
suffix='_build03' if '--build03' in sys.argv else ('_build02' if '--build02' in sys.argv else '')
for stem,short in [(f'PP_LGCM_review_v47_round2B{suffix}_NOT_RELEASED','main'),(f'PP_LGCM_appendix_review_v39_round2B{suffix}_NOT_RELEASED','appendix')]:
 p=root/'manuscript'/f'{stem}.pdf'
 if not p.exists():continue
 out=root/('readable'+suffix)/short;out.mkdir(parents=True,exist_ok=True);renders=root/'manuscript'/('renders'+suffix)/short;renders.mkdir(parents=True,exist_ok=True)
 d=fitz.open(p);pages=[];full=[]
 for i,page in enumerate(d,1):
  s=page.get_text();assert s.strip(),f'Empty text {short} page {i}'
  md=f'# {short} — PDF物理页 {i}\n\n'+s
  (out/f'page-{i:03}.md').write_text(md,encoding='utf8');full.append(md)
  pix=page.get_pixmap(matrix=fitz.Matrix(.65,.65),alpha=False);pix.save(renders/f'page-{i:03}.png')
  pages.append({'page':i,'text_chars':len(s),'width':page.rect.width,'height':page.rect.height,'rendered':True})
 (out/'full.md').write_text('\n\n'.join(full),encoding='utf8')
 records.append({'pdf':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pages':pages,'visual_review':'rendered_not_equivalent_to_human_page_review'})
 print(short,len(d),'pages extracted and rendered',flush=True)
(root/f'manuscript/pdf_readback{suffix}.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
