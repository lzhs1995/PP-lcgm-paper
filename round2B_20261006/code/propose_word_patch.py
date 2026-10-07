"""只生成可审核的XML补丁；不修改文档。实际修改通过apply_patch执行。"""
from pathlib import Path
import re,json,html,hashlib
from lxml import etree as E
ROOT=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
XML=ROOT/'manuscript/main_edit/word/document.xml'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
original=XML.read_text(encoding='utf8')
tree=E.fromstring(original.encode());changes=[];replacements={}
pairs=[
 ('“60–69岁”“70–79岁”“80岁及以上”','“61—75岁”“76岁及以上”'),
 ('最后，还控制了受访者参与调查的总次数，以控制样本流失和数据贡献量的潜在影响','历史模型曾控制受访者参与调查的总次数；该变量属于基期后的追访信息，不能据此声称控制了样本流失。修正后主模型不将其作为基期控制'),
 ('先按既定变量规则进行跨期预处理，对可跨期代填的缺失项使用最靠近2012年的可用调查记录代填，这不等于该个体基期的直接观测','历史版本曾使用其他年份记录补齐部分缺失项；本轮主分析恢复2012年原始缺失，不把这些代填值当作基期观测'),
 ('对于预处理后仍有缺失的七个变量，拟使用多重插补法（MI）进行填补','对重建后缺失的协变量采用家庭—个人分层多重插补（MI）'),
 ('个人年收入高于基期中位数的二分类项','个人年收入是否大于零的二分类项'),
 ('收入不高于中位数/高于中位数','无个人收入/有个人收入'),
 ('TIC变化','TVC变化'),
 ('“代际亲近度家内差异对长者抑郁症状的影响机理”','代际亲近度家内差异与长者抑郁症状的轨迹关联，不能据此识别影响机理'),
 ('Direction effect analysis直接效应：轨迹对轨迹的影响','直接关联分析：轨迹之间的关联'),
 ('这些历史估计与假设1.1的预期方向相符，但修复后的假设判定仍待完成','这些历史估计不用于当前假设1.1的判定，修复后的假设判定须依据合法的新模型'),
 ('其均值、方差及相关性等在均值标准化前后均未发生明显变化','其均值、方差及相关性不能仅凭显著性符号判断跨尺度稳健性'),
 ('其中，标准差、性别差、排行差（老大、长子）的参数估计结果基本稳健，均值、方差及相关性等在均值标准化前后均未发生明显变化。','上述亲近度各行均为历史估计，不能据此宣布修正数据的跨尺度稳健性成立。'),
 ('“联合交互检验+条件效应估计”验收','针对具体交互参数及条件效应的正式合并推断'),
]
for pi,p in enumerate(tree.findall('.//w:body/w:p',NS)):
 nodes=p.findall('.//w:t',NS);texts=[n.text or '' for n in nodes];before=''.join(texts);after=before
 for old,new in pairs:
  if old not in after:continue
  while old in ''.join(texts):
   flow=''.join(texts);start=flow.index(old);end=start+len(old);pos=0;first=None
   for j,t in enumerate(texts):
    right=pos+len(t)
    if right>start and pos<end:
     prefix=t[:max(0,start-pos)];suffix=t[max(0,end-pos):] if end<right else ''
     texts[j]=prefix+(new if first is None else '')+suffix
     if first is None:first=j
    pos=right
   changes.append({'paragraph':pi,'before':old,'after':new});after=''.join(texts)
 # 标题逐组标明历史状态；保留表格本体、图像与域，避免将它们当成新结果。
 if re.match(r'^(Table|Figure|表|图)\s*4\.(3|4|5)[.\d]*(?:\s|[:：])',before) and '历史' not in before and '待修复' not in before:
  texts[0]='【历史计分／插补版本：仅供追溯，不用于当前假设判定】'+texts[0]
  changes.append({'paragraph':pi,'before':before[:100],'after':'Add historical-version caption marker'})
 for n,old,new in zip(nodes,[n.text or '' for n in nodes],texts):
  if old!=new:replacements[n.sourceline]=(old,new)
lines=original.splitlines(keepends=True)
for line,(old,new) in replacements.items():
 s=lines[line-1];m=re.search(r'(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)',s)
 assert m and html.unescape(m[2])==old,(line,old[:80])
 lines[line-1]=s[:m.start(2)]+html.escape(new,quote=False)+s[m.end(2):]
updated=''.join(lines);E.fromstring(updated.encode())
(ROOT/'manuscript/main_editorial_expected_sha256.txt').write_text(hashlib.sha256(updated.encode()).hexdigest(),encoding='utf8')
patch='*** Begin Patch\n*** Update File: /mnt/c/Users/LZHS/pp_lgcm_review/round2B_20261006/manuscript/main_edit/word/document.xml\n'
oldlines=original.splitlines();newlines=updated.splitlines()
# 已知修改行，不对数十万行重复空白执行全局SequenceMatcher。
for line in sorted(replacements):
 i=line-1;patch+='@@\n'
 for j in range(max(0,i-2),i):patch+=' '+oldlines[j]+'\n'
 patch+='-'+oldlines[i]+'\n'+'+'+newlines[i]+'\n'
 for j in range(i+1,min(len(oldlines),i+3)):patch+=' '+oldlines[j]+'\n'
patch+='*** End Patch\n'
(ROOT/'manuscript/main_editorial.patch').write_text(patch,encoding='utf8')
(ROOT/'manuscript/main_editorial_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'replacements':len(changes),'text_nodes':len(replacements),'patch_bytes':len(patch.encode()),'changes':changes},ensure_ascii=False))
