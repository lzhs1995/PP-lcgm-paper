"""将已直接编辑的局限段XML组装到v44；仅转移w:t，不改其他部件。"""
from review_workspace import OUT, NS, writej, sha, csvout
from lxml import etree as E
from copy import deepcopy, copy
import zipfile

root = OUT / 'manuscript'
src = root / 'PP_LGCM_review_v43_NOT_RELEASED.docx'
dst = root / 'PP_LGCM_review_v44_NOT_RELEASED.docx'
assert not dst.exists(), dst
fragment = root / 'xml_edits/main_p2746.xml'
canon = lambda e: E.tostring(e, method='c14n')
changes = []
with zipfile.ZipFile(src) as z:
    before = E.fromstring(z.read('word/document.xml'))
    tree = deepcopy(before)
    p = tree.xpath('//w:p', namespaces=NS)[2746]
    edited = E.parse(str(fragment)).getroot()
    aa, bb = p.xpath('.//w:t', namespaces=NS), edited.xpath('.//w:t', namespaces=NS)
    assert len(aa) == len(bb)
    for a, b in zip(aa, bb):
        assert a.attrib == b.attrib
        if a.text != b.text:
            changes.append({'paragraph_index': 2746, 'old': a.text, 'new': b.text})
            a.text = b.text
    reverted = deepcopy(tree)
    for a, b in zip(reverted.xpath('//w:p', namespaces=NS)[2746].xpath('.//w:t', namespaces=NS), before.xpath('//w:p', namespaces=NS)[2746].xpath('.//w:t', namespaces=NS)):
        a.text = b.text
    assert canon(reverted) == canon(before)
    for tag in ['tbl', 'instrText', 'fldSimple', 'fldChar', 'drawing', 'footnoteReference']:
        assert [canon(x) for x in tree.xpath('//w:' + tag, namespaces=NS)] == [canon(x) for x in before.xpath('//w:' + tag, namespaces=NS)]
    text = ''.join(p.xpath('.//w:t/text()', namespaces=NS))
    assert all(x in text for x in ['2345', '3266', '2995', '929', '279', '不能仅凭上述人数解释'])
    assert all(x not in text for x in ['2339', '2894', '2573', '28.56%', '11.61%', '21.41%'])
    payload = E.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
    with zipfile.ZipFile(dst, 'x') as out:
        for entry in z.infolist():
            out.writestr(copy(entry), payload if entry.filename == 'word/document.xml' else z.read(entry.filename))
    with zipfile.ZipFile(dst) as out:
        assert out.testzip() is None
        assert z.namelist() == out.namelist()
        assert all(z.read(n) == out.read(n) for n in z.namelist() if n != 'word/document.xml')
csvout(root / 'v44_change_log.csv', changes)
writej(root / 'v44_assembly_receipt.json', {'status': 'PASS', 'source': str(src), 'source_sha256': sha(src), 'output': str(dst), 'output_sha256': sha(dst), 'paragraph_index': 2746, 'changed_text_nodes': len(changes), 'text': text, 'tables_fields_media_preserved': True, 'other_zip_parts_byte_identical': True, 'scientific_release': False})
print('V44_ASSEMBLY_PASS', len(changes), str(dst))
