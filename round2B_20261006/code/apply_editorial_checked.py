"""从未修改的解包副本按XML节点位置生成修订，避免重复上下文补丁错位。"""
from pathlib import Path
import json, hashlib
from lxml import etree as E
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
src=(root/'code/propose_word_patch.py').read_text(encoding='utf8')
src=src.split("(ROOT/'manuscript/main_editorial_expected_sha256.txt')")[0]
src=src.replace("XML=ROOT/'manuscript/main_edit/word/document.xml'", "XML=ROOT/'manuscript/main_unpacked/word/document.xml'")
scope={};exec(compile(src,'propose_word_patch.py','exec'),scope)
assert len(scope['changes'])==29
original=scope['original']; updated=scope['updated'];ns=scope['NS']
a=E.fromstring(original.encode());b=E.fromstring(updated.encode())
for node in a.findall('.//w:t',ns)+b.findall('.//w:t',ns):node.text=''
assert E.tostring(a)==E.tostring(b),'Non-text XML changed'
dest=root/'manuscript/main_editorial_checked.xml'
dest.write_bytes(updated.encode('utf8'))
receipt={'status':'PASS','changes':len(scope['changes']),'changed_text_nodes':len(scope['replacements']),'non_text_XML_identical':True,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'prior_context_patch':'FAILED_HASH_NOT_ADOPTED'}
(root/'manuscript/editorial_checked_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt))
