"""独立Word实例只读导出本轮副本，不附着或关闭用户文档。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import win32com.client
import fitz

records=readj(OUT/'manuscript/assembly_receipt.json')['records']
word=win32com.client.DispatchEx('Word.Application');word.Visible=False;word.DisplayAlerts=0
done=[]
try:
 for row in records:
  p=Path(row['output']);pdf=p.with_suffix('.pdf');assert not pdf.exists()
  doc=word.Documents.Open(str(p),ReadOnly=True,AddToRecentFiles=False,Visible=False)
  try:doc.ExportAsFixedFormat(OutputFileName=str(pdf),ExportFormat=17,OpenAfterExport=False,OptimizeFor=0,CreateBookmarks=0)
  finally:doc.Close(False)
  assert sha(p)==row['output_sha256']
  with fitz.open(pdf) as f:
   text='\n'.join(page.get_text() for page in f)
   pdf.with_suffix('.txt').write_text(text,encoding='utf-8')
   pages=len(f)
  done.append({'docx':str(p),'docx_sha256':sha(p),'pdf':str(pdf),'pdf_sha256':sha(pdf),'pages':pages})
  print(pdf.name,pages,'pages',flush=True)
finally:word.Quit()
writej(OUT/'manuscript/pdf_receipt.json',{'status':'PASS','records':done,'scientific_release':False})
