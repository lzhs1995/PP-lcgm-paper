"""只读核查NLM问题；输出原文定位、脚注格式与实际PDF页码。"""
from review_workspace import OUT, NS, writej, sha
from lxml import etree as E
from pathlib import Path
import zipfile, re, fitz

root = OUT / 'manuscript'
records = []
for name in ['PP_LGCM_review_v43_NOT_RELEASED', 'PP_LGCM_appendix_review_v37_NOT_RELEASED']:
    docx = root / (name + '.docx')
    with zipfile.ZipFile(docx) as z:
        tree = E.fromstring(z.read('word/document.xml'))
    paragraphs = tree.xpath('//w:p', namespaces=NS)
    selected = []
    markers = []
    for i, p in enumerate(paragraphs):
        txt = ''.join(p.xpath('.//w:t/text()', namespaces=NS))
        if any(x in txt for x in ['A.1—A.32', 'A.33—A.64', 'Table 4.2.1', '不同测量尺度', '不同测量尺', '1Notes']):
            selected.append({'paragraph': i, 'text': txt})
        if re.search(r'\([\d.]+\)1', txt):
            runs = []
            for r in p.xpath('.//w:r', namespaces=NS):
                t = ''.join(r.xpath('.//w:t/text()', namespaces=NS))
                if t:
                    runs.append({'text': t, 'vertical_alignment': r.xpath('./w:rPr/w:vertAlign/@w:val', namespaces=NS)})
            markers.append({'paragraph': i, 'text': txt, 'runs': runs})
    pdf = docx.with_suffix('.pdf')
    locations = []
    with fitz.open(pdf) as f:
        for page in f:
            t = re.sub(r'\s+', '', page.get_text())
            terms = [s for s in ['A.1—A.32', 'A.33—A.64', 'Table4.2.1', '0.013)1', '0.019)1'] if s in t]
            if terms:
                locations.append({'pdf_page': page.number + 1, 'terms': terms})
            if '0.013)1' in t or '0.019)1' in t:
                if len([x for x in locations if 'image' in x]) == 0:
                    dest = root / f'{name}_footnote_page_{page.number+1}.png'
                    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(dest)
                    locations[-1]['image'] = str(dest)
        pages = len(f)
    records.append({'docx': str(docx), 'sha256': sha(docx), 'pdf_pages': pages, 'selected': selected, 'markers': markers, 'locations': locations})
writej(OUT / 'reviews/local_findings_evidence.json', {'records': records})
for row in records:
    print(row['docx'], 'pages', row['pdf_pages'])
    print('Cross references and captions:', row['selected'])
    print('Markers:', row['markers'][:2], 'total', len(row['markers']))
    print('PDF locations:', row['locations'])
