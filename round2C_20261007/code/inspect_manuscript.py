"""建立原稿正文节点索引，为保留母版及定点迁移历史结果提供依据。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json
r=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');old=r.parent/'round2B_20261006'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for p in (old/'manuscript').glob('*build03_NOT_RELEASED.docx'):
    label='appendix' if 'appendix' in p.name else 'main'
    with zipfile.ZipFile(p) as z: body=E.fromstring(z.read('word/document.xml')).find('w:body',ns)
    rows=[]
    for i,node in enumerate(body):
        txt=''.join(node.itertext()) if False else ''.join(node.xpath('.//w:t/text()',namespaces=ns))
        st=node.find('w:pPr/w:pStyle',ns)
        rows.append({'index':i,'type':E.QName(node).localname,'style':st.get('{'+ns['w']+'}val') if st is not None else '', 'text':txt,'fields':len(node.findall('.//w:instrText',ns)),'drawings':len(node.findall('.//w:drawing',ns))})
    (r/'runtime'/f'{label}_body_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    (r/'runtime'/f'{label}_body_outline.txt').write_text('\n'.join(f"{x['index']:03} {x['type']} [{x['style']}] F{x['fields']} D{x['drawings']} {x['text'][:220]}" for x in rows),encoding='utf8')
    print(label,len(rows),'body nodes')
