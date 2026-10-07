"""解包/回装已通过直接XML补丁审阅的候选；本脚本不执行文字替换。"""
from pathlib import Path
import zipfile,json,hashlib,sys
from lxml import etree as E
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
work=root/'manuscript/build03_xml'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
sources=sorted((root/'manuscript').glob('*build02_NOT_RELEASED.docx'))
assert len(sources)==2
receipts=[]
separator=b'>\n<!--R2B_EDIT_SEPARATOR-->\n<'
for src in sources:
    label='appendix' if 'appendix' in src.name else 'main'
    dest=work/label/'word/document.xml'
    with zipfile.ZipFile(src) as z:
        raw=z.read('word/document.xml')
        if sys.argv[1]=='prepare':
            assert separator not in raw
            assert not dest.exists()
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(raw.replace(b'><',separator))
            assert dest.read_bytes().replace(separator,b'><')==raw
            continue
        assert sys.argv[1]=='pack'
        edited=dest.read_bytes().replace(separator,b'><')
        before=E.fromstring(raw);after=E.fromstring(edited)
        for tag in ['instrText','fldChar','drawing','footnoteReference']:
            assert [E.tostring(n) for n in before.findall('.//w:'+tag,ns)]==[E.tostring(n) for n in after.findall('.//w:'+tag,ns)],tag
        beforetexts=before.findall('.//w:t',ns);aftertexts=after.findall('.//w:t',ns)
        assert len(beforetexts)==len(aftertexts)
        changes=[{'text_node':i,'before':a.text,'after':b.text} for i,(a,b) in enumerate(zip(beforetexts,aftertexts)) if a.text!=b.text]
        for a,b in zip(beforetexts,aftertexts):a.text='';b.text=''
        assert E.tostring(before)==E.tostring(after),'Non-text XML changed'
        out=src.with_name(src.name.replace('build02','build03'))
        assert not out.exists(),'Preserve existing candidate'
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as new:
            for info in z.infolist():
                new.writestr(info.filename,edited if info.filename=='word/document.xml' else z.read(info.filename))
        with zipfile.ZipFile(out) as new:
            assert new.testzip() is None
            assert all(z.read(n)==new.read(n) for n in z.namelist() if n!='word/document.xml')
        receipts.append({'source':src.name,'output':out.name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
            'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'changes':changes,
            'fields_and_nontext_xml_identical':True,'other_zip_parts_identical':True,'native_pdf_status':'PENDING'})
if receipts:
    (root/'manuscript/build03_editorial_receipt.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'stage':sys.argv[1],'documents':len(sources),'receipts':len(receipts)}))
