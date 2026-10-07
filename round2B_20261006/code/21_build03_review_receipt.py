"""校验实际PDF文本并记录已完成的差异页目视核查，不改文档。"""
from pathlib import Path
import fitz,re,json,hashlib,sys
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
exports=json.loads((root/'manuscript/native_word_export_build03.json').read_text(encoding='utf8'))
comparisons=json.loads((root/'manuscript/build03_pixel_comparison.json').read_text(encoding='utf8'))
rows=[]
for e in exports:
    p=root/'manuscript'/e['pdf']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==e['pdf_sha256']
    with fitz.open(p) as d:
        text=''.join(page.get_text() for page in d)
        count=re.sub(r'\s+','',text).count('Thesehistoricalmodelswerealsoadjusted')
        assert count==2
        if 'appendix' in p.name:
            first=d[0];rect=first.rect
            first.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=fitz.Rect(0,0,rect.width,rect.height*.30),alpha=False).save(root/'manuscript/renders_build03/appendix_intro_detail.png')
    rows.append({'pdf':p.name,'sha256':e['pdf_sha256'],'historical_footnotes':count,'pages':e['pages']})
(root/'manuscript/build03_pdf_text_checks.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
if '--record-reviewed' in sys.argv:
    assert comparisons[0]['changed_pages']==[19,27]
    assert comparisons[1]['changed_pages']==list(range(1,17))
    receipt={'scope':'build03 editorial review, not a final statistical or citation audit',
        'documents':rows,'changed_pages_reviewed':{'main':[19,27],'appendix':list(range(1,17))},
        'unchanged_pages_pixel_identical_to_reviewed_build02':130,
        'review_method':'Main changed pages viewed individually; appendix changed pages viewed on contact sheets, with first-page note additionally inspected in detail.',
        'findings':'No new blank pages or gross cropping observed. Original colored highlighting and historical-table pagination remain.',
        'same_build_NotebookLM_review':'NOT_PERFORMED; prior build02 response must not be relabelled as a build03 review',
        'scientific_release':False}
    (root/'manuscript/build03_visual_review.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rows))
