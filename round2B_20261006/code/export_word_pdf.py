"""独立Word实例原生导出；仅关闭本脚本打开的文档和创建的实例。"""
from pathlib import Path
import win32com.client,pythoncom,json,hashlib,time,sys
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');pythoncom.CoInitialize()
app=None;records=[]
try:
 app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0
 suffix='_build03' if '--build03' in sys.argv else ('_build02' if '--build02' in sys.argv else '')
 for name in [f'PP_LGCM_review_v47_round2B{suffix}_NOT_RELEASED',f'PP_LGCM_appendix_review_v39_round2B{suffix}_NOT_RELEASED']:
  src=root/'manuscript'/f'{name}.docx';dst=src.with_suffix('.pdf');print('OPEN',name,flush=True)
  doc=app.Documents.Open(str(src),ReadOnly=True,AddToRecentFiles=False,ConfirmConversions=False)
  try:
   fields=doc.Fields.Count;footnotes=doc.Footnotes.Count;revisions=doc.Revisions.Count
   doc.Repaginate();pages=doc.ComputeStatistics(2);doc.ExportAsFixedFormat(str(dst),17)
   rec={'document':src.name,'pdf':dst.name,'pages':pages,'fields':fields,'footnotes':footnotes,'revisions':revisions,'docx_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'Word_version':str(app.Version),'export':'native_Word','Zotero_refresh':'NOT_PERFORMED_no_new_citations','visual_review':'PENDING'}
   records.append(rec);(root/f'manuscript/native_word_export{suffix}.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(rec),flush=True)
  finally:doc.Close(False)
finally:
 if app is not None:app.Quit()
 pythoncom.CoUninitialize()
