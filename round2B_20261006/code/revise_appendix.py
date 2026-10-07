"""修订附录版本与术语；保留历史数值，逐表登记采用状态。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,hashlib,re
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
repo=Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/cfps_review_20261005/github_publish')
src=repo/'round2A_appendix_v38_20261006/PP_LGCM_appendix_review_v38_NOT_RELEASED.docx'
dst=root/'manuscript/PP_LGCM_appendix_review_v39_round2B_build02_NOT_RELEASED.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
with zipfile.ZipFile(src) as z: parts={n:z.read(n) for n in z.namelist()}
t=E.fromstring(parts['word/document.xml']);body=t.find('w:body',ns);changes=[]
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=ns))
def replace(p,old,new):
 nodes=p.findall('.//w:t',ns);texts=[n.text or '' for n in nodes];flow=''.join(texts)
 if old not in flow:return
 start=flow.index(old);end=start+len(old);pos=0;done=False
 for n,s in zip(nodes,texts):
  right=pos+len(s)
  if right>start and pos<end:
   n.text=s[:max(0,start-pos)]+(new if not done else '')+(s[end-pos:] if end<right else '');done=True
  pos=right
 changes.append({'before':old,'after':new})
pairs=[('非线性调节','给定切点的二分得分交互'),('线性调节','连续得分交互'),('（完全不显著）','（历史结果，具体交互待修正数据核验）'),('稳健性检验——','历史替代规格（不构成修正数据稳健性证据）——'),('0=中低收入，1=高收入','0=无个人收入，1=有个人收入'),('0=中位数及以下，1=中位数以上','0=无个人收入，1=有个人收入'),('Direction effect analysis 直接效应：轨迹对轨迹的影响','直接关联：轨迹之间的关联（历史估计）')]
for p in body.findall('.//w:p',ns):
 for old,new in pairs:
  while old in text(p):replace(p,old,new)
tables=body.findall('w:tbl',ns);assert len(tables)==103
header_changes=[]
for ordinal,tbl in enumerate(tables,1):
 expected=None
 if ordinal in [7,8,19,20,27,28]:expected=['I1I4','I1S4','S1I4','S1S4']
 if 37<=ordinal<=100:
  j=(ordinal-37)%32
  if j<16:
   k=2 if j<4 else (3 if j<8 else 4)
   expected=[f'I1I{k}',f'I1S{k}',f'S1I{k}',f'S1S{k}']
  elif j>=20:
   k=3 if j<24 else 4
   expected=[f'I{k}I1',f'I{k}S1',f'S{k}I1',f'S{k}S1']
 if expected:
  cells=tbl.find('w:tr',ns).findall('w:tc',ns);assert len(cells)==5
  oldheaders=[text(c) for c in cells[1:]]
  assert oldheaders in [['I1I3','I1S3','S1I3','S1S3'],['I2I1','I2S1','S2I1','S2S1']],(ordinal,oldheaders)
  for c,oldh,newh in zip(cells[1:],oldheaders,expected):replace(c,oldh,newh)
  header_changes.append({'table_ordinal':ordinal,'before':oldheaders,'after':expected,'basis':'table growth-factor row labels and reviewer section 5.8; estimates unchanged'})
assert len(header_changes)==62
index=[]
for i,tbl in enumerate(tables,1):
 status='混合版本：CESD8为前轮未聚类的修正计分估计；其他行为历史估计。尺度沿用本表原规格，非本轮统一重估' if i<=2 else ('历史计分与插补版本：仅供追溯，不用于当前假设判定' if i<=100 else '前轮修正数据补充审计：保留原模型合法性与样本限制，不代表稳健性通过')
 p=E.Element(W+'p');pr=E.SubElement(p,W+'pPr');E.SubElement(pr,W+'keepNext');r=E.SubElement(p,W+'r');rp=E.SubElement(r,W+'rPr');E.SubElement(rp,W+'b');E.SubElement(r,W+'t').text=f'【附录第{i}表｜{status}】'
 body.insert(body.index(tbl),p);index.append({'table_ordinal':i,'status':status,'first_cells':text(tbl)[:140]})
intro=E.Element(W+'p');r=E.SubElement(intro,W+'r');E.SubElement(r,W+'t').text='附录v39：Round2B复核候选，非正式实证定稿。本附录保留历史系数与模型编号供追溯；第3—100表共98张为历史表。旧星号、模型比较和切点不作为修正数据的新推断。表头、异常估计及引文未完成全量再验证的项目另列审读清单；不得将本次版本标记理解为这些问题已全部解决。修正得分SE缺口已补齐，但第一阶段不确定性与正式调节推断仍须分别核验。'
body.insert(0,intro)
old=E.fromstring(parts['word/document.xml'])
for tag in ['instrText','fldChar','drawing','footnoteReference']:
 assert [E.tostring(n) for n in old.findall('.//w:'+tag,ns)]==[E.tostring(n) for n in t.findall('.//w:'+tag,ns)],tag
parts['word/document.xml']=E.tostring(t,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in parts.items():z.writestr(n,b)
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as b:
 assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
(root/'manuscript/appendix_table_status.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf8')
(root/'manuscript/appendix_header_corrections.json').write_text(json.dumps(header_changes,ensure_ascii=False,indent=2),encoding='utf8')
receipt={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'historical_tables':98,'all_tables':103,'text_changes':changes,'other_zip_parts_identical':True,'native_pdf_review':'PENDING'}
(root/'manuscript/appendix_revision_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'tables':103,'historical':98,'text_changes':len(changes),'path':str(dst)},ensure_ascii=False))
