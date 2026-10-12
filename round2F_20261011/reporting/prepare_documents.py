"""只读母版，提取可审阅的段落与XML；不更新Word域，不改写母版。"""
from pathlib import Path
import json, zipfile, hashlib
from lxml import etree as E

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'round2E_20261010/manuscript/delivery'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
SOURCES={'main':'PP_LGCM_review_v50_round2E.docx',
         'appendix':'PP_LGCM_appendix_review_v42_round2E.docx'}

def prepare():
    for kind,name in SOURCES.items():
        dest=ROOT/'manuscript/working'/kind
        dest.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(BASE/name) as z:
            raw=z.read('word/document.xml')
            tree=E.fromstring(raw)
            body=tree.find('w:body',NS)
            rows=[]
            for i,node in enumerate(body):
                row=dict(index=i,kind=E.QName(node).localname,
                    text=''.join(node.xpath('.//w:t/text()',namespaces=NS)),
                    fields=len(node.findall('.//w:instrText',NS)),
                    footnotes=len(node.findall('.//w:footnoteReference',NS)))
                if row['kind']=='tbl':
                    row['rows']=[[''.join(c.xpath('.//w:t/text()',namespaces=NS)) for c in r.findall('w:tc',NS)] for r in node.findall('w:tr',NS)]
                rows.append(row)
                if row['kind']=='p' and row['fields']:
                    p=dest/f'paragraph_{i:03d}.xml'
                    if not p.exists():p.write_bytes(E.tostring(node,encoding='utf-8',pretty_print=True))
            (dest/'index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            (dest/'index.txt').write_text('\n'.join(f"{r['index']:03d} [{r['kind']};fields={r['fields']};notes={r['footnotes']}] {r['text']}" for r in rows),encoding='utf-8')
            (dest/'source.json').write_text(json.dumps(dict(source=str(BASE/name),sha256=hashlib.sha256((BASE/name).read_bytes()).hexdigest(),parts=z.namelist()),indent=2),encoding='utf-8')
        print(kind,len(rows),'nodes',sum(r['fields'] for r in rows),'field code nodes')

if __name__=='__main__':prepare()
