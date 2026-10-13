from prepare_closeout import *
from collections import Counter
for kind in ['main','appendix']:
    items=json.loads((ROOT/'working'/kind/'index.json').read_text(encoding='utf-8'))
    for row in items:
        n=E.parse(str(ROOT/'working'/kind/f"{row['index']:03d}.xml")).getroot()
        if n.findall('.//w:footnoteReference',NS): print('FOOTNOTE',kind,row['index'])
    name='PP_LGCM_review_v51_round2F.docx' if kind=='main' else 'PP_LGCM_appendix_review_v43_round2F.docx'
    with zipfile.ZipFile(ROOT/'baseline/manuscripts'/name) as z:
        print(kind,'RELS',z.read('word/_rels/document.xml.rels').decode())
for i in [9,10,11,21,28,67,68,76]:
    n=E.parse(str(ROOT/'working/main'/f'{i:03d}.xml')).getroot()
    chunks=[];depth=0;field=[];plain=''
    for child in n:
        kinds=child.xpath('.//w:fldChar/@w:fldCharType',namespaces=NS)
        if 'begin' in kinds and depth==0:
            if plain:chunks.append(plain);plain=''
        if depth or 'begin' in kinds:
            field.append(child)
            depth+=kinds.count('begin')-kinds.count('end')
            if depth==0:
                chunks.append({'field':''.join(''.join(x.xpath('.//w:t/text()',namespaces=NS)) for x in field)});field=[]
        else:
            plain+=''.join(child.xpath('.//w:t/text()',namespaces=NS))
    if plain:chunks.append(plain)
    print('PARA',i,json.dumps(chunks,ensure_ascii=False))
