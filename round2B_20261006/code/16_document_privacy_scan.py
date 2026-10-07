"""核对公开DOCX/PDF文本中的真实标识符；只输出文件、哈希和命中计数。"""
from pathlib import Path
import json, re, zipfile, hashlib
from lxml import etree
import fitz

root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
stage=root/'public_stage'
ids=set(json.loads((root/'private/identifier_tokens.json').read_text(encoding='utf8')))
rows=[]
for path in sorted(stage.rglob('*')):
    if path.suffix.lower() not in {'.docx','.pdf'}:
        continue
    texts=[]
    if path.suffix.lower()=='.pdf':
        with fitz.open(path) as doc:
            texts=[page.get_text() for page in doc]
    else:
        with zipfile.ZipFile(path) as doc:
            for name in doc.namelist():
                if name.endswith('.xml'):
                    xml=etree.fromstring(doc.read(name))
                    texts.append(''.join(xml.itertext()))
    tokens=set(re.findall(r'(?<![\w.])[0-9]{5,14}(?![\w.])','\n'.join(texts)))
    rows.append({'path':path.relative_to(stage).as_posix(),
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'text_units':len(texts),'potential_identifier_matches':len(tokens&ids)})
manuscripts=list((stage/'manuscript').glob('*.docx'))
paired=len(manuscripts)==2 and all(p.with_suffix('.pdf').exists() for p in manuscripts)
result={'status':'PASS' if rows and paired and all(r['potential_identifier_matches']==0 and r['text_units']>0 for r in rows)
        else 'REQUIRES_LOCAL_REVIEW','files':rows,
        'manuscript_pairs_complete':paired,
        'limitations':'Exact known numeric identifiers in extractable text; no image OCR. Document provenance and visual review remain necessary.'}
(root/'runtime/document_privacy_scan.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
assert result['status']=='PASS'
