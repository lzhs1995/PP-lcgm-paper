"""逐份独立Word导出v45/v38，并验证标签映射与核心新增内容。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import fitz, win32com.client, shutil, re

root = OUT/'manuscript'
records, checks, images = [], [], []
for i, row in enumerate(readj(root/'v45_v38_assembly_receipt.json')['records']):
    src = Path(row['output']); pdf = src.with_suffix('.pdf')
    short = OUT / ('v45_export.docx' if i==0 else 'v38_appendix_export.docx')
    shortpdf = short.with_suffix('.pdf')
    assert not pdf.exists() and not short.exists() and not shortpdf.exists()
    shutil.copy2(src,short)
    word=win32com.client.DispatchEx('Word.Application'); word.Visible=False; word.DisplayAlerts=0
    try:
        doc=word.Documents.Open(str(short),ReadOnly=True,AddToRecentFiles=False,Visible=False,OpenAndRepair=False)
        try:
            print('LABEL_PDF_OPEN',i,doc.ComputeStatistics(2),flush=True)
            doc.Repaginate()
            doc.SaveAs2(str(shortpdf),FileFormat=17,AddToRecentFiles=False)
        finally:doc.Close(False)
    finally:word.Quit()
    assert shortpdf.exists() and shortpdf.stat().st_size>1000
    shutil.copy2(shortpdf,pdf)
    assert sha(src)==row['output_sha256']
    norm=lambda s:re.sub(r'\s+','',s)
    with fitz.open(pdf) as f:
        text='\n'.join(p.get_text() for p in f); compact=norm(text)
        markers=['Process-4为排行差过程族的历史编号','Siblingdiff4表示排行差（长子）']
        markers += ['全部USEVARIABLES缺失929人','不能仅凭上述人数解释'] if i==0 else ['Sibling_diff2表示排行差（老小），Sibling_diff3表示排行差（幼子）','补表R1','补表R2','补表R3']
        checks += [{'document':i,'text':s,'pass':s in compact} for s in markers]
        for p in f:
            if any(s in norm(p.get_text()) for s in [markers[0], 'Sibling_diff2表示排行差（老小）']):
                path=root/f'final_labels_{i}_page_{p.number+1}.png'
                p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(path)
                images.append({'document':i,'page':p.number+1,'path':str(path)})
        pages=len(f)
    pdf.with_suffix('.txt').write_text(text,encoding='utf-8')
    records.append({'docx':str(src),'docx_sha256':sha(src),'pdf':str(pdf),'pdf_sha256':sha(pdf),'pages':pages})
    print('LABEL_PDF_READY',i,pages,flush=True)
assert all(c['pass'] for c in checks), checks
writej(root/'final_pdf_receipt.json',{'status':'PASS','records':records,'checks':checks,'images':images,'scientific_release':False})
print('FINAL_PDF_PAIR_PASS',len(checks),images,flush=True)
