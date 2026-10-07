"""比较同一渲染设置下的build02与build03页面，定位需重新目视检查的页。"""
from pathlib import Path
from PIL import Image,ImageChops
import json,hashlib
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006/manuscript')
records=[]
for kind in ['main','appendix']:
    old=sorted((root/'renders_build02'/kind).glob('page-*.png'))
    new=sorted((root/'renders_build03'/kind).glob('page-*.png'))
    assert old and len(old)==len(new)
    pages=[]
    for a,b in zip(old,new):
        assert a.name==b.name
        with Image.open(a) as ia,Image.open(b) as ib:
            assert ia.size==ib.size
            box=ImageChops.difference(ia.convert('RGB'),ib.convert('RGB')).getbbox()
        pages.append({'page':int(a.stem.split('-')[-1]),'pixel_identical':box is None,
                      'difference_bbox':box,'new_render_sha256':hashlib.sha256(b.read_bytes()).hexdigest()})
    records.append({'document':kind,'pages':len(pages),'changed_pages':[p['page'] for p in pages if not p['pixel_identical']],
                    'page_comparison':pages,'status':'CHANGED_PAGES_REQUIRE_VISUAL_REVIEW'})
(root/'build03_pixel_comparison.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps([{k:r[k] for k in ['document','pages','changed_pages']} for r in records]))
