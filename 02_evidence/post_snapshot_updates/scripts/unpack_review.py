"""提取待编辑段落；保留原始ZIP及其他段落，供直接XML补丁与后续保真组装。"""
from review_workspace import OUT, MAIN, APP, NS, writej, sha
from lxml import etree as E
import zipfile

root=OUT/'manuscript/xml_edits';root.mkdir(parents=True,exist_ok=True)
for label,src,indices in [('main',MAIN,[65,1016,1186,2734,2745]),('appendix',APP,[])]:
    with zipfile.ZipFile(src) as z:
        xml=z.read('word/document.xml')
        (root/f'{label}_original.xml').write_bytes(xml)
    tree=E.fromstring(xml)
    for i in indices:
        p=tree.xpath('//w:p',namespaces=NS)[i]
        file=root/f'{label}_p{i}.xml'
        assert not file.exists(),file
        file.write_bytes(E.tostring(p,pretty_print=True,encoding='utf-8'))
writej(root/'unpack_receipt.json',{'main_sha256':sha(MAIN),'appendix_sha256':sha(APP),'paragraph_indices':[65,1016,1186,2734,2745]})
print(root)
