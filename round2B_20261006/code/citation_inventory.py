"""提取现有Zotero域中的文献信息，核对域完整性，不伪造原生刷新或原文审读。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,csv,re
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
src=root/'manuscript/PP_LGCM_review_v47_round2B_build02_NOT_RELEASED.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};items={};count=0;errors=[];bib=0
with zipfile.ZipFile(src) as z:
 for name in ['word/document.xml','word/footnotes.xml','word/endnotes.xml']:
  if name not in z.namelist():continue
  t=E.fromstring(z.read(name));s=''.join(t.xpath('.//w:instrText/text()',namespaces=ns));bib+=s.count('ZOTERO_BIBL')
  for m in re.finditer(r'ADDIN\s+ZOTERO_ITEM\s+CSL_CITATION\s*',s):
   try:obj,_=json.JSONDecoder().raw_decode(s[m.end():].lstrip())
   except Exception as e:errors.append({'part':name,'error':str(e)});continue
   count+=1
   for item in obj.get('citationItems',[]):
    d=item.get('itemData',{});key=str(d.get('id',item.get('id')))
    if key in items:items[key]['citation_occurrences']+=1;continue
    issued=d.get('issued',{}).get('date-parts',[[]]);year=issued[0][0] if issued and issued[0] else ''
    authors=d.get('author',[]);author='; '.join(a.get('literal') or ' '.join(filter(None,[a.get('family'),a.get('given')])) for a in authors)
    items[key]={'item_key':key,'title':d.get('title',''),'author':author,'author_count':len(authors),'year':year,'type':d.get('type',''),'container':d.get('container-title',''),'DOI':d.get('DOI',''),'citation_occurrences':1,'source':'existing_embedded_CSL_metadata_not_fulltext_verification'}
rows=list(items.values())
with (root/'audit/citation_inventory.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['item_key']);w.writeheader();w.writerows(rows)
report={'citation_fields_parsed':count,'unique_items':len(rows),'parse_errors':errors,'bibliography_fields':bib,'missing_titles':sum(not r['title'] for r in rows),'native_plugin_refresh':'NOT_PERFORMED','fulltext_verification':'NOT_PERFORMED_BY_THIS_SCRIPT','interpretation':'Metadata completeness and field parsing do not establish citation support.'}
(root/'audit/citation_inventory_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
