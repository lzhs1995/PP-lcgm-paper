"""核对真实PDF中的新修订及新增表；渲染关键页面供人工审阅。"""
from review_workspace import OUT, readj, writej
import csv,re,fitz
from pathlib import Path
root=OUT/'manuscript';receipt=readj(root/'pdf_receipt.json')
norm=lambda s:re.sub(r'\s+','',s).replace('\u2212','-').replace('\u2013','-')
changes=list(csv.DictReader((root/'change_log.csv').open(encoding='utf-8-sig')))
checks=[];images=[]
for i,row in enumerate(receipt['records']):
 with fitz.open(row['pdf']) as pdf:
  text='\n'.join(p.get_text() for p in pdf);compact=norm(text)
  if i==0:
   for c in changes:
    if c['new']:checks.append({'type':'changed_text','paragraph':c['paragraph_index'],'pass':norm(c['new']) in compact,'new_text':c['new']})
   phrases=['2016年同时包含','其时间载荷依次','四个历史截距得分','假设4.2b保留','不能据此断言结论必然保守']
  else:
   phrases=['补充审计：测量','补表R1','补表R2','补表R3','-0.427','-0.440','-0.743']
   for s in phrases:checks.append({'type':'supplement_marker','text':s,'pass':norm(s) in compact})
  pages=sorted({p.number for p in pdf for s in phrases if norm(s) in norm(p.get_text())})
  for n in pages:
   path=root/f'review_{i}_page_{n+1}.png';pdf[n].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(path)
   images.append({'document':i,'page':n+1,'path':str(path)})
result={'status':'PASS' if all(r['pass'] for r in checks) else 'REVIEW','checks':checks,'images':images}
writej(root/'pdf_local_validation.json',result)
print({'status':result['status'],'checks':len(checks),'failures':[r for r in checks if not r['pass']],'images':images})
