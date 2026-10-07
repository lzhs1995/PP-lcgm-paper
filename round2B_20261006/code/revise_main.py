"""在已验收文本节点修订上同步聚类数值及本轮方法，保留所有域。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,hashlib
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
src=Path('C:/Users/LZHS/pp_lgcm_review/round2_20261006/manuscript/PP_LGCM_review_v46_round2A_NOT_RELEASED.docx')
dst=root/'manuscript/PP_LGCM_review_v47_round2B_build02_NOT_RELEASED.docx'
with zipfile.ZipFile(src) as z:parts={n:z.read(n) for n in z.namelist()}
t=E.fromstring((root/'manuscript/main_editorial_checked.xml').read_bytes());changes=[]
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=ns))
def replace(p,old,new):
 nodes=p.findall('.//w:t',ns);texts=[n.text or '' for n in nodes];flow=''.join(texts)
 if old not in flow:return
 start=flow.index(old);end=start+len(old);pos=0;done=False
 for n,s in zip(nodes,texts):
  right=pos+len(s)
  if right>start and pos<end:n.text=s[:max(0,start-pos)]+(new if not done else '')+(s[end-pos:] if end<right else '');done=True
  pos=right
 changes.append({'before':old,'after':new})
pairs=[('13.550（SE=0.096）','13.550（SE=0.101）'),('p=.284','p=.290'),('7.523（SE=0.635）','7.523（SE=0.657）'),('p=.180','p=.188'),('0.054（SE=0.011，p<.001）','0.054（SE=0.012，p<.001）'),('8.700（df=3，p=.034）','8.452（df=3，p=.038；由聚类输出打印的对数似然及校正因子计算）'),('乡村及收入不高于中位数','乡村及无个人收入'),('当前3274人的插补输入中','历史跨期补齐后的3274人插补输入中'),('婚姻不属于这七个插补变量','历史方案中婚姻不属于这七个插补变量'),('当前25组配对模板','历史25组配对模板'),('Estimator=ML与Estimator=Bayes法的适用性不能脱离具体模型判断','完整LMS与乘积指标法是不同估计路径，相关文献仅提供方法背景'),('目前尚无覆盖各规格的完整诊断证据支持两种估计法均无法收敛的断言','旧三过程潜交互尝试未保存可核对的输出，本稿不报告其收敛判定，也不以其他方法的应用文献作为本模型已经估计的证据'),('现有记录也不足以断言三过程联合模型的极大似然与贝叶斯估计均不收敛','旧三过程尝试未保存可核对输出，不报告其估计或收敛判定'),('见附表1、表2','见附录表4.2.1、4.2.2'),('截距得分的标准误汇总与连续得分、观测基期指标的交叉表见附录补充审计','截距得分的历史标准误汇总见附录补充审计；该处未提供连续得分与观测基期指标的交叉表')]
for p in t.findall('.//w:body/w:p',ns):
 for old,new in pairs:replace(p,old,new)
 # 新方法不覆盖历史轨迹的尺度；在相应段落明确来源。
 if text(p).startswith('初始修复方案的插补过程'):
  n=E.SubElement(E.SubElement(p,W+'r'),W+'t');n.text=' Round2B不复用这批存在家庭共同值冲突的旧插补。本轮恢复2012年教育、地区、城乡与婚姻的原始缺失后，家庭收入、城乡、地区按家庭单次插补，个人变量采用家庭随机截距预测均值匹配；纵向结果及结构性缺失保持原状。主结构控制集排除追访次数和生活满意度，后者另作敏感性。工程批次预定10份、30轮，是否形成正式MI结果须通过逐成员数据检查、链诊断、父模型合法性与合并精度核验。'
 if text(p).startswith('描述统计需要区分'):
  E.SubElement(E.SubElement(p,W+'r'),W+'t').text=' Round2B另恢复教育2人、地区1人、城乡7人及婚姻1人的基期缺失。家庭收入90人分属71个全缺失家庭；城乡7人分属6户，地区1人属1户。家庭层与个人层缺失数不能互换。'
 if text(p).startswith('需要区分增长形状'):
  E.SubElement(E.SubElement(p,W+'r'),W+'t').text=' 本段CESD8单变量参数已统一为3274人家庭聚类版本，沿用该输出的时间归一化。Round2B新条件模型另采用十年为日历时间单位；尺度变化不增加信息。四期线性模型已获得可继续审阅的解，但不据此认定四期自由形状或核心调节稳健性通过。'
for row in t.findall('.//w:tr',ns):
 if text(row).startswith('CESD8'):
  for p in row.findall('.//w:p',ns):
   for old,new in [('0.096','0.101'),('0.635','0.657'),('0.123','0.125')]:replace(p,old,new)
# 表4.2.1 CESD8自由形状拟合行：依据标签后的第一模型行，避免替换其他过程。
tables=t.findall('.//w:body/w:tbl',ns);rows=tables[2].findall('w:tr',ns)
for i,row in enumerate(rows):
 if 'Process-5(CESD-8; corrected)' in text(row):
  for nextrow in rows[i+1:i+5]:
   if '0.979' in text(nextrow) and '0.970' in text(nextrow):
    for p in nextrow.findall('.//w:p',ns):
     for old,new in [('0.979','0.980'),('0.970','0.971'),('0.038','0.037')]:replace(p,old,new)
old=E.fromstring(parts['word/document.xml'])
for tag in ['instrText','fldChar','drawing','footnoteReference']:
 assert [E.tostring(n,with_tail=False) for n in old.findall('.//w:'+tag,ns)]==[E.tostring(n,with_tail=False) for n in t.findall('.//w:'+tag,ns)],tag
parts['word/document.xml']=E.tostring(t,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in parts.items():z.writestr(n,b)
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as b:assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
receipt={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'changes':changes,'other_zip_parts_identical':True,'citation_fields_preserved':True,'native_pdf_review':'PENDING','scientific_release':False}
(root/'manuscript/main_revision_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'changes':len(changes),'path':str(dst)},ensure_ascii=False))
