"""同版XML、Word导出及PDF逐格核对；跨稿字段迁移按总清单核对。"""
from pathlib import Path
from collections import Counter
import json,re,zipfile
from lxml import etree as E
import pdf_checks as pc
import document_support as ds
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'manuscript/delivery';NS=ds.NS;W=ds.W
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  parts={n:z.read(n) for n in z.namelist()}
 return parts,E.fromstring(parts['word/document.xml'])
def instructions(tree):
 depth=0;current=[];out=[]
 for el in tree.iter():
  if el.tag==W+'fldChar':
   k=el.get(W+'fldCharType')
   if k=='begin':depth+=1
   elif k=='end':
    depth-=1;assert depth>=0
    if not depth:out.append(''.join(current));current=[]
  elif el.tag==W+'instrText':current.append(el.text or '')
 assert depth==0
 return Counter(out)
def note_inventory(parts,tree):
 out=Counter()
 for kind in ['footnote','endnote']:
  refs=tree.findall('.//w:'+kind+'Reference',NS)
  tr=E.fromstring(parts['word/'+kind+'s.xml'])
  for ref in refs:
   found=tr.xpath('./w:'+kind+'[@w:id="'+ref.get(W+'id')+'"]',namespaces=NS);assert len(found)==1
   out[(kind,ref.get(W+'id'),pc.text(found[0]))]+=1
 return out
def relationships(parts,tree):
 tr=E.fromstring(parts['word/_rels/document.xml.rels']);ids={r.get('Id') for r in tr};assert len(ids)==len(tr)
 refs={v for n in tree.iter() for k,v in n.attrib.items() if k in {ds.R+'id',ds.R+'embed',ds.R+'link'}}
 assert refs<=ids,(refs-ids)
 for name,data in parts.items():
  if name.endswith('.rels'):
   for rel in E.fromstring(data):
    if rel.get('TargetMode')!='External':assert ds.resolve_part(name,rel.get('Target','')) in parts
 starts={n.get(W+'id') for n in tree.findall('.//w:bookmarkStart',NS)}
 ends={n.get(W+'id') for n in tree.findall('.//w:bookmarkEnd',NS)}
 assert starts==ends,(starts-ends,ends-starts)
 return dict(referenced_relationships=len(refs),bookmarks=len(starts))
def main():
 expected=read(OUT/'expected_tables.json');export=read(OUT/'native_word_export.json')
 bp,bt=load(ROOT/'baseline/manuscripts/PP_LGCM_review_v51_round2F.docx')
 allcodes=Counter();allnotes=Counter();results=[]
 for i,entry in enumerate(export):
  kind='main' if 'candidate' in entry['document'] else 'appendix';doc=OUT/entry['document'];pdf=OUT/entry['pdf']
  assert pc.sha(doc)==entry['docx_sha256'];assert pc.sha(pdf)==entry['pdf_sha256']
  parts,tree=load(doc);allcodes+=instructions(tree);allnotes+=note_inventory(parts,tree)
  rels=relationships(parts,tree);want=[t for t in expected if t['document']==kind];tables=tree.findall('.//w:tbl',NS)
  assert len(tables)==len(want)==entry['tables']
  for t,e in zip(tables,want):assert pc.xml_rows(t)==[e['headers']]+e['rows']
  result=pc.validate_pdf_tables(pdf,want,kind);dump(OUT/(kind+'_pdf_cell_validation.json'),result)
  assert result['passed'],result['errors'][:3]
  renders=pc.render(pdf,OUT/'visual',kind)
  results.append(dict(kind=kind,pages=entry['pages'],tables=len(tables),cells=sum(sum(len(r) for r in [e['headers']]+e['rows']) for e in want),fields=entry['fields'],footnotes=entry['footnotes'],relationships=rels,render=renders,docx_sha256=pc.sha(doc),pdf_sha256=pc.sha(pdf)))
 assert allcodes==instructions(bt),'Original complex instruction inventory changed'
 assert allnotes==note_inventory(bp,bt),'Footnote content lost or duplicated'
 assert sum(x['fields'] for x in results)==sum(instructions(bt).values())+len(bt.findall('.//w:hyperlink',NS))
 dump(OUT/'manuscript_validation.json',dict(status='PASS',mode='NO_NEW_ESTIMATION',results=results,combined_fields=sum(allcodes.values()),combined_footnotes=sum(allnotes.values()),visual_review='PENDING'))
 print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':main()
