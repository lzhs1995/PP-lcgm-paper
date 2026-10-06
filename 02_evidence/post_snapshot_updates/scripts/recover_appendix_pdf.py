"""仅恢复缺失的附录PDF；使用短ASCII路径与独立Word实例，保留前次失败事实。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import win32com.client, shutil, fitz, time
records=readj(OUT/'manuscript/assembly_receipt.json')['records']
row=records[1];src=Path(row['output']);pdf=src.with_suffix('.pdf')
assert not pdf.exists();short=OUT/'appendix_export.docx';shortpdf=OUT/'appendix_export.pdf'
assert not short.exists();shutil.copy2(src,short)
word=win32com.client.DispatchEx('Word.Application');word.Visible=False;word.DisplayAlerts=0
try:
 doc=word.Documents.Open(str(short),ReadOnly=True,AddToRecentFiles=False,Visible=False,OpenAndRepair=False)
 try:
  print('APPENDIX_OPEN pages=',doc.ComputeStatistics(2),'tables=',doc.Tables.Count,flush=True)
  doc.Repaginate();print('REPAGINATED',flush=True)
  doc.SaveAs2(str(shortpdf),FileFormat=17,AddToRecentFiles=False)
  print('SAVEAS_PDF_RETURNED exists=',shortpdf.exists(),flush=True)
 finally:doc.Close(False)
finally:word.Quit()
assert shortpdf.exists() and shortpdf.stat().st_size>1000
shutil.copy2(shortpdf,pdf)
done=[]
for r in records:
 p=Path(r['output']);f=p.with_suffix('.pdf');assert sha(p)==r['output_sha256']
 with fitz.open(f) as d:
  txt='\n'.join(page.get_text() for page in d);pages=len(d)
 f.with_suffix('.txt').write_text(txt,encoding='utf-8')
 done.append({'docx':str(p),'docx_sha256':sha(p),'pdf':str(f),'pdf_sha256':sha(f),'pages':pages})
writej(OUT/'manuscript/pdf_receipt.json',{'status':'PASS','records':done,'appendix_recovery':'Separate Word SaveAs2 PDF on identical short-path DOCX; first ExportAsFixedFormat returned without a PDF.','scientific_release':False})
print('PDF_PAIR_VERIFIED',done,flush=True)
