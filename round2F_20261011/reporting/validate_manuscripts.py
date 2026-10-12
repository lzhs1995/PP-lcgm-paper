"""逐格核对当前Word/PDF，检查母版部件与字段保留；渲染供人工视觉检查。"""
from pathlib import Path
import json,zipfile
from lxml import etree as E
import pdf_checks as p

ROOT=Path(__file__).resolve().parents[1]
def read(q):return json.loads(q.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'manuscript/delivery';expected=read(out/'expected_tables.json');exports=read(out/'native_word_export.json');receipts=read(out/'revision_receipts.json');results=[]
 for export,receipt in zip(exports,receipts):
  kind='appendix' if 'appendix' in export['document'] else 'main'
  src=out/export['document'];pdf=out/export['pdf'];old=ROOT/'baseline/manuscripts'/receipt['source']
  assert p.sha(src)==export['docx_sha256']==receipt['docx_sha256'] and p.sha(pdf)==export['pdf_sha256']
  with zipfile.ZipFile(src) as z,zipfile.ZipFile(old) as original:
   assert z.testzip() is None and z.namelist()==original.namelist()
   assert all(z.read(n)==original.read(n) for n in z.namelist() if n!='word/document.xml')
   tree=E.fromstring(z.read('word/document.xml'));ot=E.fromstring(original.read('word/document.xml'))
  assert tree.xpath('.//w:instrText/text()',namespaces=p.NS)==ot.xpath('.//w:instrText/text()',namespaces=p.NS)
  assert p.citations(tree)==p.citations(ot)
  want=[t for t in expected if t['document']==kind];ts=tree.findall('.//w:body/w:tbl',p.NS)
  assert len(ts)==len(want)==export['tables']
  for actual,e in zip(ts,want):
   a=[[p.norm(c) for c in row] for row in p.xml_rows(actual)]
   b=[[p.norm(c) for c in row] for row in [e['headers']]+e['rows']]
   assert a==b,e['title']
  check=p.validate_pdf_tables(pdf,want,kind)
  (out/(kind+'_pdf_cell_validation.json')).write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
  rendered=p.render(pdf,out/'visual',kind)
  result=dict(document=export['document'],pdf=export['pdf'],pages=export['pages'],tables=len(ts),
   cells=sum(len(row) for t in want for row in [t['headers']]+t['rows']),docx_sha256=p.sha(src),pdf_sha256=p.sha(pdf),
   docx_tables_match=True,pdf_tables_match=check['passed'],citations_preserved=True,other_parts_byte_identical=True,
   fields=export['fields'],footnotes=export['footnotes'],rendering=rendered)
  results.append(result);print(kind,'pages',export['pages'],'tables',len(ts),'PDF_CELLS',check['passed'],flush=True)
  if check['errors']:print(json.dumps(check['errors'][:1],ensure_ascii=False),flush=True)
 status='PASS' if all(r['pdf_tables_match'] for r in results) else 'FAIL'
 (out/'manuscript_validation.json').write_text(json.dumps(dict(status=status,documents=results,
  stage='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW',visual_review='PENDING'),ensure_ascii=False,indent=2),encoding='utf-8')
 if status!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
