"""只在审阅副本添加三处证据边界；其他DOCX组件保持字节一致。"""
from pathlib import Path
import re,zipfile,copy,json,hashlib,html,shutil
from lxml import etree as E
ROOT=Path(r'C:\Users\LZHS\pp_lgcm_review\round2_20261006')
SRC=Path(r'C:\Users\LZHS\Desktop\cnm\tasks\01_R_analysis\work\cfps_review_20261005\github_publish\01_current_review\current_manuscript\PP_LGCM_review_v45_NOT_RELEASED.docx')
dest=ROOT/'manuscript';dest.mkdir(exist_ok=True)
OUT=dest/'PP_LGCM_review_v46_round2A_NOT_RELEASED.docx'
if OUT.exists():
 backup=dest/'build01';backup.mkdir(exist_ok=True)
 for p in [OUT,OUT.with_suffix('.pdf')]:
  if p.exists() and not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
with zipfile.ZipFile(SRC) as zin:
 original=zin.read('word/document.xml').decode('utf8');changes=[];blocks=[]
 def repl(m):
  s=m[0];t=''.join(html.unescape(x) for x in re.findall(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>',s,re.S))
  note=None
  if t.startswith('Table 4.3.1:'):note='【历史结果：修正数据正式重估前，仅作审计对照，不用于当前假设判定。】'
  if t.startswith('Table 4.2.2:'):note='【混合版本：CESD8为上一轮修正计分估计，其余行为历史估计；本轮统一家庭聚类的诊断结果见第二轮核验报告。】'
  if note:
   changes.append({'before':t,'addition':note})
   newblock=s[:-6]+'<w:r><w:rPr><w:b/><w:color w:val="9C0006"/></w:rPr><w:t>'+html.escape(note)+'</w:t></w:r></w:p>'
   if t.startswith('Table 4.2.2:'):
    assert '</w:pPr>' in newblock
    newblock=newblock.replace('</w:pPr>','<w:pageBreakBefore/></w:pPr>',1)
    changes[-1]['layout']='page break before caption to prevent orphaned header'
   blocks.append((s,newblock))
   return newblock
  return s
 updated=re.sub(r'<w:p(?:\s[^>]*)?>.*?</w:p>',repl,original,flags=re.S)
 old='以下启示均以观测性关联为依据，不等同于已经识别的干预效果。'
 new='以下内容为研究视角与待检验线索，不作为修正数据后的已验收实证结论，也不等同于已经识别的干预效果。'
 assert updated.count(old)==1 and len(changes)==2
 updated=updated.replace(old,new);changes.append({'before':old,'after':new})
 E.fromstring(updated.encode('utf8'))
 with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED) as zout:
  for info in zin.infolist():zout.writestr(copy.copy(info),updated.encode('utf8') if info.filename=='word/document.xml' else zin.read(info.filename))
 with zipfile.ZipFile(OUT) as z:
  assert z.testzip() is None
  assert all(zin.read(n)==z.read(n) for n in zin.namelist() if n!='word/document.xml')
  # 域代码、图片、表格原数字等均未改写；只允许三处指定增量。
  undo=updated.replace(new,old)
  for oldblock,newblock in blocks:undo=undo.replace(newblock,oldblock,1)
  assert undo==original
(dest/'revision_receipt.json').write_text(json.dumps({'source':str(SRC),'source_sha256':sha(SRC),'output':OUT.name,'output_sha256':sha(OUT),'changes':changes,'other_zip_members_byte_identical':True,'reverse_patch_exact':True,'final_manuscript_release':False},ensure_ascii=False,indent=2),encoding='utf8')
print(OUT)
