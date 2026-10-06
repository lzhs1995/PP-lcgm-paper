"""组装标签修订v45/v38；回退获准文本后XML与父版完全一致。"""
from review_workspace import OUT, NS, sha, writej, csvout
from lxml import etree as E
from copy import deepcopy, copy
import zipfile

root = OUT / 'manuscript'
canon = lambda e: E.tostring(e, method='c14n')
records, changes = [], []
for label, old, new in [('main','PP_LGCM_review_v44_NOT_RELEASED','PP_LGCM_review_v45_NOT_RELEASED'), ('appendix','PP_LGCM_appendix_review_v37_NOT_RELEASED','PP_LGCM_appendix_review_v38_NOT_RELEASED')]:
    src, dst = root / (old+'.docx'), root / (new+'.docx')
    assert not dst.exists(), dst
    with zipfile.ZipFile(src) as z:
        before = E.fromstring(z.read('word/document.xml'))
        tree = deepcopy(before)
        pp = tree.xpath('//w:p', namespaces=NS)
        indices = []
        for fragment in sorted((root/'labels_xml').glob(label+'_p*.xml')):
            i = int(fragment.stem.split('_p')[1])
            indices.append(i)
            edited = E.parse(str(fragment)).getroot()
            aa, bb = pp[i].xpath('.//w:t', namespaces=NS), edited.xpath('.//w:t', namespaces=NS)
            assert len(aa) == len(bb)
            for a, b in zip(aa, bb):
                assert a.attrib == b.attrib
                if a.text != b.text:
                    changes.append({'document':label,'paragraph_index':i,'old':a.text or '', 'new':b.text or ''})
                    a.text = b.text
        reverted = deepcopy(tree)
        rr, oo = reverted.xpath('//w:p', namespaces=NS), before.xpath('//w:p', namespaces=NS)
        for i in indices:
            for a, b in zip(rr[i].xpath('.//w:t', namespaces=NS), oo[i].xpath('.//w:t', namespaces=NS)):
                a.text = b.text
        assert canon(reverted) == canon(before)
        for tag in ['instrText','fldSimple','fldChar','drawing','footnoteReference']:
            assert [canon(e) for e in tree.xpath('//w:'+tag,namespaces=NS)] == [canon(e) for e in before.xpath('//w:'+tag,namespaces=NS)]
        text = ''.join(tree.xpath('//w:t/text()', namespaces=NS))
        assert 'Sibling diff4表示排行差（老小）' not in text
        assert '排行差（老小）对均值的调节效应' not in text
        assert '均值对排行差（老小）的调节效应' not in text
        assert 'Process-4为排行差过程族的历史编号' in text
        if label == 'appendix':
            assert 'Sibling_diff2表示排行差（老小），Sibling_diff3表示排行差（幼子）' in text
        payload = E.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
        with zipfile.ZipFile(dst,'x') as out:
            for entry in z.infolist():
                out.writestr(copy(entry), payload if entry.filename=='word/document.xml' else z.read(entry.filename))
        with zipfile.ZipFile(dst) as out:
            assert out.testzip() is None
            assert all(z.read(n)==out.read(n) for n in z.namelist() if n!='word/document.xml')
    records.append({'document':label,'source':str(src),'source_sha256':sha(src),'output':str(dst),'output_sha256':sha(dst),'paragraph_indices':indices,'table_count':len(tree.xpath('//w:tbl',namespaces=NS)),'text_only_edits':True,'all_other_content_preserved':True,'fields_media_preserved':True,'other_zip_parts_byte_identical':True})
csvout(root/'v45_v38_change_log.csv', changes)
writej(root/'v45_v38_assembly_receipt.json',{'status':'PASS','records':records,'changed_text_nodes':len(changes),'scientific_release':False})
print('LABEL_REVISION_ASSEMBLY_PASS',len(changes),flush=True)
