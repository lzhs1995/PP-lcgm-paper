"""提取待核正的标签XML；修改由直接补丁完成，不重建Word对象。"""
from review_workspace import OUT, NS, writej
from lxml import etree as E
import zipfile

root = OUT / 'manuscript'
edits = root / 'labels_xml'
edits.mkdir(exist_ok=True)
specs = {'main': ('PP_LGCM_review_v44_NOT_RELEASED.docx', [1013,1088,1181]), 'appendix': ('PP_LGCM_appendix_review_v37_NOT_RELEASED.docx', [341,414,457,544,1041,1681,2242,2786,3326,3868,4409])}
rows = []
for label, (filename, indices) in specs.items():
    with zipfile.ZipFile(root / filename) as z:
        tree = E.fromstring(z.read('word/document.xml'))
    pp = tree.xpath('//w:p', namespaces=NS)
    for i in indices:
        path = edits / f'{label}_p{i}.xml'
        assert not path.exists(), path
        path.write_bytes(E.tostring(pp[i], encoding='UTF-8', xml_declaration=True, pretty_print=True))
        texts = pp[i].xpath('.//w:t/text()', namespaces=NS)
        rows.append({'document': label, 'paragraph': i, 'texts': texts})
        print(label, i, texts)
writej(root / 'labels_before.json', {'records': rows})
