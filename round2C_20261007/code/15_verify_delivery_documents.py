"""核对最终Word/PDF版本绑定、保留域与数值出现；不替代逐页视觉检查。"""
from pathlib import Path
import json,csv,hashlib,zipfile,re,ast
from lxml import etree as E
import fitz
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007')
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):
 with zipfile.ZipFile(p) as z:return E.fromstring(z.read('word/document.xml'))
exports=json.loads((R/'manuscript/native_word_export.json').read_text())
receipts=json.loads((R/'manuscript/revision_receipts.json').read_text())
checked=[]
for x in exports:
 src=R/'manuscript'/x['document'];pdf=R/'manuscript'/x['pdf']
 assert sha(src)==x['docx_sha256'] and sha(pdf)==x['pdf_sha256']
 with fitz.open(pdf) as d:
  assert len(d)==x['pages']
  text=''.join(p.get_text() for p in d)
  assert all(len(p.get_text())>50 for p in d)
 checked.append({'document':src.name,'pdf':pdf.name,'pages':x['pages'],'sha256':sha(pdf)})
 if 'appendix' not in src.name:
  norm=re.sub(r'\s+','',text).replace('−','-')
  with (R/'results/conditional_MI_paths.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
  for row in rows:
   for key in ['estimate','se','lower','upper']:assert f'{float(row[key]):.3f}' in norm,(row['spec'],key)
  assert '本研究分以下四步进行' not in norm
  old=tree(Path(next(r['source'] for r in receipts if r['document']==src.name)))
  retained=list(old.find('w:body',W))[:75]+[list(old.find('w:body',W))[76]]
  expected=[s for n in retained for s in n.xpath('.//w:instrText/text()',namespaces=W)]
  actual=tree(src).xpath('.//w:instrText/text()',namespaces=W)
  assert expected==actual,'Retained field instructions changed'
for p in (R/'code').glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=p.name)
out={'status':'PASS','pdfs':checked,'retained_field_instructions':'BYTE_TEXT_IDENTICAL','pooled_values_in_PDF':'PASS','python_syntax':'PASS','scope':'Numerical text and document bindings; visual inspection recorded separately'}
(R/'evidence/delivery_document_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False))
