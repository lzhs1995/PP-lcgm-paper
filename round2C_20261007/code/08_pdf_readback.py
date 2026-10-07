"""提取当前PDF全文并渲染全部页面；视觉验收须另行人工完成。"""
from pathlib import Path
import fitz,json,hashlib
from PIL import Image,ImageOps,ImageDraw
root=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');out=root/'readable';out.mkdir(exist_ok=True)
records=[]
for src in sorted((root/'manuscript').glob('*round2C_NOT_RELEASED.pdf')):
 label='appendix' if 'appendix' in src.name else 'main';d=out/label;d.mkdir(exist_ok=True);images=[];texts=[]
 with fitz.open(src) as doc:
  for i,page in enumerate(doc):
   text=page.get_text(sort=True);texts.append(f'# 第{i+1}页\n\n{text}')
   (d/f'page_{i+1:03}.md').write_text(texts[-1],encoding='utf8')
   pix=page.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False);p=d/f'page_{i+1:03}.png';pix.save(p);images.append(p)
  rec={'file':src.name,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pages':len(doc),'rendered_pages':len(images),'page_text_lengths':[len(t) for t in texts],'visual_review':'PENDING'}
 (out/f'{label}_fulltext.md').write_text('\n\n'.join(texts),encoding='utf8')
 for offset in range(0,len(images),9):
  canvas=Image.new('RGB',(1200,1740),'#cccccc');draw=ImageDraw.Draw(canvas)
  for j,path in enumerate(images[offset:offset+9]):
   with Image.open(path) as im:thumb=ImageOps.contain(im,(390,540))
   x=(j%3)*400;y=(j//3)*580;canvas.paste(thumb,(x,y+25));draw.text((x+10,y+5),f'{label} page {offset+j+1}',fill='black')
  canvas.save(out/f'{label}_contact_{offset//9+1:02}.jpg',quality=85)
 records.append(rec)
(root/'manuscript/pdf_readback.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(records,ensure_ascii=False))
