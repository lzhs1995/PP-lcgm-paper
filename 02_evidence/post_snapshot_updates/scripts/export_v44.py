"""独立Word实例导出v44；保留DOCX原字节，复用已验证附录PDF。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import fitz, win32com.client, shutil, re

root = OUT / 'manuscript'
row = readj(root / 'v44_assembly_receipt.json')
src = Path(row['output'])
pdf = src.with_suffix('.pdf')
short = OUT / 'v44_export.docx'
shortpdf = OUT / 'v44_export.pdf'
assert not pdf.exists() and not short.exists() and not shortpdf.exists()
shutil.copy2(src, short)
word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
word.DisplayAlerts = 0
try:
    doc = word.Documents.Open(str(short), ReadOnly=True, AddToRecentFiles=False, Visible=False, OpenAndRepair=False)
    try:
        print('V44_OPEN', doc.ComputeStatistics(2), flush=True)
        doc.Repaginate()
        doc.SaveAs2(str(shortpdf), FileFormat=17, AddToRecentFiles=False)
    finally:
        doc.Close(False)
finally:
    word.Quit()
assert shortpdf.exists() and shortpdf.stat().st_size > 1000
shutil.copy2(shortpdf, pdf)
assert sha(src) == row['output_sha256']
checks = []
images = []
with fitz.open(pdf) as f:
    text = '\n'.join(p.get_text() for p in f)
    compact = re.sub(r'\s+', '', text)
    phrases = ['全部USEVARIABLES缺失929人', '有效样本量为2345人', '有效样本量为3266人', '有效样本量为2995人', '不能仅凭上述人数解释模型结果不显著的原因']
    checks = [{'text': s, 'pass': s in compact} for s in phrases]
    for page in f:
        if '需要分别评估' in re.sub(r'\s+', '', page.get_text()):
            path = root / f'v44_limitation_page_{page.number+1}.png'
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(path)
            images.append({'page': page.number+1, 'path': str(path)})
    pages = len(f)
pdf.with_suffix('.txt').write_text(text, encoding='utf-8')
assert all(r['pass'] for r in checks)
records = [{'docx': str(src), 'docx_sha256': sha(src), 'pdf': str(pdf), 'pdf_sha256': sha(pdf), 'pages': pages}]
app = readj(root / 'pdf_receipt.json')['records'][1]
assert sha(app['docx']) == app['docx_sha256'] and sha(app['pdf']) == app['pdf_sha256']
records.append(app)
writej(root / 'v44_pdf_receipt.json', {'status': 'PASS', 'records': records, 'checks': checks, 'images': images, 'scientific_release': False})
print('V44_PDF_PASS', pages, images, flush=True)
