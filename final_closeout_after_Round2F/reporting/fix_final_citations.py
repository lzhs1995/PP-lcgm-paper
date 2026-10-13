"""只修两处已核实引文问题；保留原复杂引文域、表格和基线文件。"""
from pathlib import Path
from copy import deepcopy
import json,shutil,zipfile
from lxml import etree as E
import document_support as ds
import pdf_checks as pc
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'manuscript/delivery';W=ds.W;NS=ds.NS
receipt=ROOT/'reports/FINAL_CITATION_REPAIR.json'
assert not receipt.exists(),'Already repaired; reuse receipt instead of editing twice'
archive=ROOT/'runtime/before_citation_repair';archive.mkdir(exist_ok=True)
for p in OUT.iterdir():
 if p.is_file():shutil.copy2(p,archive/p.name)
repairs=[]
for stem,kind in [('PP_LGCM_scoped_final_candidate','main'),('PP_LGCM_scoped_supplement','appendix')]:
 p=OUT/(stem+'.docx');before=ds.sha(p)
 with zipfile.ZipFile(p) as z:parts={n:z.read(n) for n in z.namelist()}
 tree=E.fromstring(parts['word/document.xml']);codes=tree.xpath('.//w:instrText/text()',namespaces=NS)
 tables=[E.tostring(t) for t in tree.findall('.//w:tbl',NS)]
 if kind=='main':
  hits=[t for t in tree.findall('.//w:t',NS) if 'Davey et al., 1998' in (t.text or '')];assert len(hits)==1
  hits[0].text=hits[0].text.replace('Davey et al., 1998','Davey & Eggebeen, 1998')
 else:
  body=tree.find(W+'body');nodes=list(body)
  heading=next(i for i,n in enumerate(nodes) if ds.text(n)=='补充材料参考文献')
  bib=[n for n in nodes[heading+1:] if n.tag==W+'p' and ds.text(n)]
  assert not any(ds.text(n).startswith('Raudenbush') for n in bib)
  value='Raudenbush S. W.、Chan W.-S.（1992）。Growth Curve Analysis in Accelerated Longitudinal Designs。Journal of Research in Crime and Delinquency，29(4)，387–411。https://doi.org/10.1177/0022427892029004001'
  new=E.Element(W+'p');template=bib[0]
  if template.find(W+'pPr') is not None:new.append(deepcopy(template.find(W+'pPr')))
  run=E.SubElement(new,W+'r');rp=template.find('.//w:rPr',NS)
  if rp is not None:run.append(deepcopy(rp))
  E.SubElement(run,W+'t').text=value
  after=next((n for n in bib if ds.text(n).lower()>'raudenbush'),None)
  if after is not None:body.insert(list(body).index(after),new)
  else:body.insert(list(body).index(bib[-1])+1,new)
 assert codes==tree.xpath('.//w:instrText/text()',namespaces=NS)
 assert tables==[E.tostring(t) for t in tree.findall('.//w:tbl',NS)]
 parts['word/document.xml']=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
 temp=p.with_suffix('.tmp')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in parts.items():z.writestr(name,data)
 temp.replace(p)
 md=pc.readable_markdown(tree,False).split('\n',1)[1]
 (OUT/(kind+'_readable.md')).write_text('范围收缩候选稿；零新增估计。\n'+md,encoding='utf-8')
 repairs.append({'document':p.name,'before_sha256':before,'after_sha256':ds.sha(p),'tables_unchanged':True,'field_instructions_unchanged':True})
status=json.loads((OUT/'build_status.json').read_text(encoding='utf-8'))
for r in status['documents']:r['sha256']=ds.sha(OUT/r['document'])
(OUT/'build_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
record={'status':'APPLIED_PENDING_NEW_PDF_REVIEW','repairs':repairs,'new_mplus_calls':0,
 'finding_1':{'decision':'Fix two-author citation display; preserve editable Zotero instructions','source':'https://pubmed.ncbi.nlm.nih.gov/9520925/'},
 'finding_2':{'decision':'Add verified accelerated-longitudinal-design reference. Reject NLM suggested depressive-symptoms title and pagination.',
 'source':'https://journals.sagepub.com/doi/10.1177/0022427892029004001','verified_year':1992,'verified_pages':'387–411'},
 'archive':'runtime/before_citation_repair','old_review_status':'SUPERSEDED_BY_PDF_CHANGE'}
receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
