"""只创建并关闭本脚本的独立Word实例，原生导出当前两份候选。"""
from pathlib import Path
import win32com.client,pythoncom,json,hashlib
root=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');pythoncom.CoInitialize()
app=None;records=[]
try:
 app=win32com.client.DispatchEx('Word.Application')
 if app.Documents.Count:
  # 若COM意外路由到已有文档实例，释放引用但绝不退出该用户实例。
  app=None;raise RuntimeError('DispatchEx returned an instance with existing documents; preserve it and review export routing')
 app.Visible=False;app.DisplayAlerts=0
 for name in ['PP_LGCM_review_v48_round2C_NOT_RELEASED','PP_LGCM_appendix_review_v40_round2C_NOT_RELEASED']:
  src=root/'manuscript'/f'{name}.docx';dst=src.with_suffix('.pdf');print('OPEN',name,flush=True)
  doc=app.Documents.Open(str(src),ReadOnly=True,AddToRecentFiles=False,ConfirmConversions=False)
  try:
   fields=doc.Fields.Count;footnotes=doc.Footnotes.Count;revisions=doc.Revisions.Count
   doc.Repaginate();pages=doc.ComputeStatistics(2);doc.ExportAsFixedFormat(str(dst),17)
   rec={'document':src.name,'pdf':dst.name,'pages':pages,'fields':fields,'footnotes':footnotes,'revisions':revisions,'docx_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'Word_version':str(app.Version),'export':'native_Word','Zotero_refresh':'NOT_PERFORMED_no_new_citations','visual_review':'PENDING'}
   records.append(rec);(root/'manuscript/native_word_export.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(rec),flush=True)
  finally:doc.Close(False)
finally:
 if app is not None:app.Quit()
 pythoncom.CoUninitialize()
