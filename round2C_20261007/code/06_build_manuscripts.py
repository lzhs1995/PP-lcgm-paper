"""保留原稿母版和保留段落的Word对象；当前结果与历史审计材料分开。
只在本批独立复算通过后生成v48/v40；不创建新估计或伪称Zotero刷新。
"""
from pathlib import Path
from copy import deepcopy
from lxml import etree as E
import zipfile,csv,json,re,hashlib,shutil
ROOT=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');OLD=ROOT.parent/'round2B_20261006'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+NS['w']+'}'
OUT=ROOT/'manuscript';OUT.mkdir(exist_ok=True)
def readcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(e):return ''.join(e.xpath('.//w:t/text()',namespaces=NS))
def p(s,style=None):
 x=E.Element(W+'p');pr=E.SubElement(x,W+'pPr')
 if style:
  E.SubElement(pr,W+'pStyle').set(W+'val',style)
  E.SubElement(pr,W+'keepNext')
 E.SubElement(pr,W+'spacing').set(W+'after','100')
 r=E.SubElement(x,W+'r');t=E.SubElement(r,W+'t');t.text=str(s);return x
def table(headers,rows):
 x=E.Element(W+'tbl');pr=E.SubElement(x,W+'tblPr');E.SubElement(pr,W+'tblW',attrib={W+'w':'9000',W+'type':'dxa'})
 borders=E.SubElement(pr,W+'tblBorders')
 for edge in ['top','left','bottom','right','insideH','insideV']:E.SubElement(borders,W+edge,attrib={W+'val':'single',W+'sz':'4',W+'color':'B7B7B7'})
 grid=E.SubElement(x,W+'tblGrid');width=9000//len(headers)
 for _ in headers:E.SubElement(grid,W+'gridCol').set(W+'w',str(width))
 for i,row in enumerate([headers]+rows):
  tr=E.SubElement(x,W+'tr');trpr=E.SubElement(tr,W+'trPr');E.SubElement(trpr,W+'cantSplit')
  if i==0:E.SubElement(trpr,W+'tblHeader')
  for value in row:
   tc=E.SubElement(tr,W+'tc');cp=E.SubElement(tc,W+'tcPr');E.SubElement(cp,W+'tcW',attrib={W+'w':str(width),W+'type':'dxa'})
   tc.append(p(value))
 return x
def num(x,n=3):
 try:return f'{float(x):.{n}f}'
 except (ValueError,TypeError):return '—'
def interval(r):return f'[{num(r["lower"])}, {num(r["upper"])}]'
LABEL={'bii':'亲近度起点→抑郁起点','bis':'亲近度起点→抑郁变化','bss':'亲近度变化→抑郁变化','bsyiy':'抑郁起点→抑郁变化'}
NAME={'C1':'自由形状X／线性Y，SY残差固定0','SW':'自由形状X／线性Y，同期残差关联','XLIN':'双过程日历线性，SY残差自由'}
def bibliography(nodes):
 s=''.join(''.join(x.xpath('.//w:instrText/text()',namespaces=NS)) for x in nodes);items={};errors=[]
 for m in re.finditer(r'ADDIN\s+ZOTERO_ITEM\s+CSL_CITATION\s*',s):
  try:o,_=json.JSONDecoder().raw_decode(s[m.end():].lstrip())
  except Exception as e:errors.append(str(e));continue
  for item in o.get('citationItems',[]):
   d=item.get('itemData',{});items[str(d.get('id',item.get('id')))]=d
 assert not errors,errors
 out=[]
 for d in items.values():
  a='、'.join(v.get('literal') or ' '.join(filter(None,[v.get('family'),v.get('given')])) for v in d.get('author',[]))
  dp=d.get('issued',{}).get('date-parts',[[]]);year=str(dp[0][0]) if dp and dp[0] else '年份待核'
  s=f'{a}（{year}）。{d.get("title", "题名待核")}。{d.get("container-title", "")}'
  for key in ['volume','issue','page']:
   if d.get(key):s+=f'，{d[key]}'
  if d.get('DOI'):s+=f'。https://doi.org/{d["DOI"]}'
  out.append((a,year,s))
 return [v[2] for v in sorted(out)],items
def save_doc(source,name,nodes,changes):
 with zipfile.ZipFile(source) as z:
  tree=E.fromstring(z.read('word/document.xml'));body=tree.find('w:body',NS);sect=deepcopy(body.find('w:sectPr',NS))
  for child in list(body):body.remove(child)
  body.extend(nodes);body.append(sect)
  data=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
  dest=OUT/name
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as zz:
   for info in z.infolist():zz.writestr(deepcopy(info),data if info.filename=='word/document.xml' else z.read(info.filename))
  before={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
 with zipfile.ZipFile(dest) as z:
  after={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()};assert set(before)==set(after)
  modified=[n for n in before if before[n]!=after[n]];assert modified==['word/document.xml']
  E.fromstring(z.read('word/document.xml'));assert z.testzip() is None
  instr=tree.xpath('.//w:instrText/text()',namespaces=NS)
  depth=0;field_begins=0
  for field in tree.findall('.//w:fldChar',NS):
   typ=field.get(W+'fldCharType')
   if typ=='begin':depth+=1;field_begins+=1
   elif typ=='end':depth-=1;assert depth>=0,'Unmatched Word field end'
   elif typ=='separate':assert depth>0,'Word field separator outside field'
  assert depth==0,'Unclosed Word field after section migration'
  for tag in ['footnoteReference','endnoteReference']:
   part='word/footnotes.xml' if tag=='footnoteReference' else 'word/endnotes.xml'
   refs=tree.findall('.//w:'+tag,NS)
   if refs:
    rt=E.fromstring(z.read(part));ids={e.get(W+'id') for e in rt};assert all(e.get(W+'id') in ids for e in refs)
 rec={'source':str(source),'source_sha256':sha(source),'document':name,'sha256':sha(dest),'changed_zip_parts':modified,'non_document_parts_byte_identical':True,'retained_instruction_fragments':len(instr),'balanced_complex_fields':field_begins,'retained_footnotes':len(tree.findall('.//w:footnoteReference',NS)),'retained_drawings':len(tree.findall('.//w:drawing',NS)),'changes':changes,'status':'XML_CHECKED_NATIVE_WORD_PDF_PENDING','Zotero_refresh':'NOT_PERFORMED_existing_retained_citations_only','bibliography':'static rendering of retained embedded CSL metadata; not native plugin bibliography'}
 return rec
def main():
 assert json.loads((ROOT/'evidence/independent_verification.json').read_text())['status']=='PASS'
 assert json.loads((ROOT/'results/SUMMARY_CONTRACT.json').read_text())['status']=='CHECKPOINT_C_SUMMARIZED'
 gates=readcsv(ROOT/'audit/family_gates.csv');fits=readcsv(ROOT/'results/model_fit.csv');prof=readcsv(ROOT/'results/profile_MI01.csv')
 pooled=readcsv(ROOT/'results/conditional_MI_paths.csv') if (ROOT/'results/conditional_MI_paths.csv').exists() else []
 good=[g['spec'] for g in gates if g['eligible_for_conditional_pooling']=='TRUE']
 source=OLD/'manuscript/PP_LGCM_review_v47_round2B_build03_NOT_RELEASED.docx'
 with zipfile.ZipFile(source) as z:original=list(E.fromstring(z.read('word/document.xml')).find('w:body',NS))
 assert len(original)==266
 nodes=[deepcopy(n) for n in original[:75]];changes=[]
 def replace(i,s):
  old=txt(nodes[i]);assert not nodes[i].findall('.//w:instrText',NS),'Cannot flatten citation field'
  pr=nodes[i].find('w:pPr',NS);q=p(s)
  if pr is not None:q.remove(q.find('w:pPr',NS));q.insert(0,deepcopy(pr))
  rp=nodes[i].find('w:r/w:rPr',NS)
  if rp is not None:q.find('w:r',NS).insert(0,deepcopy(rp))
  nodes[i]=q;changes.append({'source_body_index':i,'before':old,'after':s})
 adopted='、'.join(good) if good else '无'
 replace(0,'代际亲近度与老年心理健康的纵向关联——基于家内差异的视角〔v48：检查点C审阅候选〕')
 bss=[r for r in pooled if r['label']=='bss']
 findings='；'.join(f'{r["spec"]}中变化关联为{num(r["estimate"])}，95%区间{interval(r)}' for r in bss) or '本批限定规格未形成满足全部采用门槛的合并结果'
 replace(2,'摘要：本文使用中国家庭追踪调查2012—2022年五期资料，以3274名老年人的非平衡面板考察代际亲近度与抑郁轨迹的关联。研究在修正CESD计分、恢复基期协变量真实缺失并完成家庭—个人分层多重插补后，对平行过程增长模型开展预定的零条件残差、同期测量残差关联与双线性对照。'+findings+'。这些结果仅解释相应增长形状与残差假设下的条件关联，不包含模型选择不确定性，也不等同于干预效果。家内差异的核心调节、社会经济组间差异和窗口复核尚未在当前修复数据上完成，本稿不据历史输出宣布其成立或不存在。')
 replace(57,'CFPS在2012、2016、2018、2020和2022年同时提供本研究所需的代际亲近度与抑郁测量，故使用这五期构建非平衡面板；各指标的可用人数分别报告。')
 replace(65,'本研究以CESD8衡量抑郁症状，使用8—32分编码，分数越高表示症状越重。2012年旧处理中的条目反向计分错误已修正，3274人中2593人的基期总分发生变化，基期均值由16.232变为13.575；2016年及以后原始总分未因此改写。各期Y统一使用修正后的2012年均值和标准差进行标准化，因此后续期标准化值也随基期参照更新。这项计分修复不等于证明跨期测量不变性。20题实际或官方等化分数属于后续敏感性口径，本批未执行其窗口对照。')
 for i in [43,44,45,46]:replace(i,txt(nodes[i]).replace('年收入','有无个人收入'))
 # 控制变量的金额、相对收入和二分指标不可混称。
 replace(72,'主调整集包含24项基期编码列。父母特征包括年龄（61—75岁与76岁及以上）、性别、城乡、户口、民族、教育、自评相对收入（1—5级）、个人收入金额（万元）、健康、婚姻与ADL。年龄、地区与健康等类别变量依实际虚拟变量编码进入模型。用于理论异质性分组的“有无个人收入”指个人收入是否大于零，与个人收入金额和自评相对收入不同。完整编码顺序见附录。')
 replace(73,'子女特征包括人数、性别构成、年龄极差、是否同住以及经济和工具性支持；家庭特征包括家庭收入（万元）与地区。当前分析已恢复被其他年份记录代填的2012年原始缺失，再按家庭和个人层级插补。追访总次数不作为基期混杂变量；生活满意度不属于本批24项主调整集。')
 nodes.extend([p('Analytical strategy 分析策略','afff0'),deepcopy(original[76]),
 p('当前联合模型以亲近度均值为X、修正CESD8为Y。十份插补的数据入口与上一批逐一哈希绑定，原队列为3274人、2410个家庭。两过程的截距参考2012年，线性变化因子的时间载荷为0、0.4、0.6、0.8、1，单位为十年；自由形状X固定首末载荷为0和1，中间载荷自由，不能解释成每年恒定变化。模型尺度沿用冻结输入，具体标准化入口及对应参数单位见附录。'),
 p('协变量缺失采用已完成的10份、30轮家庭—个人分层插补。家庭收入、城乡和地区按真实家庭单位处理，个人目标使用家庭层依赖结构；已观测值、家庭共同值、目标缺失和冻结纵向指标的完整性检查通过。纵向测量的实际缺失通过模型似然处理，并未将各期抑郁或亲近度逐人填满。该处理仍依赖缺失机制和模型设定；死亡后的结构性缺失不能自动解释为可忽略缺失。'),
 p('四条预定关系为亲近度起点到抑郁起点、亲近度起点到抑郁变化、亲近度变化到抑郁变化、抑郁起点到抑郁变化。四个增长因子均条件于24项基期控制，并保留亲近度截距与斜率、亲近度斜率与抑郁截距之间的条件残差关联。'),
 p('为评价联合变化分解，预定比较三类规格：C1在原自由形状X／线性Y结构中固定SY残差为零；SW增加五个同波X—Y测量残差协方差并保持SY残差自由；XLIN将两个过程均设为日历线性并保持SY残差自由。三类均估计全部十份插补，不按单份显著性选模型。C1的零残差限制规定给定预测量后SY不再有额外随机差异，是强工作假设，不意味着全体个体的抑郁变化相同。'),
 p('Mplus 9采用MLR估计及家庭聚类稳健标准误。采用判断同时检查自由方差、潜变量和测量残差协方差的合法性、预期秩、参数估计协方差及起点稳定性，不以正常结束或单一拟合指标放行。每个独立通过门槛的模型族，使用全部十份参数与对应协方差作Rubin合并，并采用完整数据大样本自由度近似；结果属于固定工作规格下的条件推断，不含模型选择不确定性或边界方差检验。'),
 p('另在预定第一份插补中，将SY条件残差固定为0、0.02、0.08、0.20、0.40，分别重估其他自由参数，评价主要关系对残差假设的敏感性。这些固定点不是置信集合，单份剖面也不是完整MI稳健性检验。本批不开展新的调节、H4.2b或窗口模型。'),
 p('Results 当前结果','affe'),p('样本与观测分布','afff0')])
 desc=readcsv(OLD/'audit/observed_longitudinal_descriptives.csv');dr=[]
 for year in ['2012','2016','2018','2020','2022']:
  y=next(r for r in desc if r['year']==year and r['variable'].startswith('ces8'));x=next(r for r in desc if r['year']==year and r['variable'].startswith('wfd_m'))
  dr.append([year,x['N'],num(x['mean']),y['N'],num(y['mean'])])
 nodes += [p('表1 原队列中各期实际观测人数与均值','af3'),table(['年份','亲近度N','亲近度均值','CESD8 N','CESD8均值'],dr),p('亲近度按1—5分原始量尺、CESD8按8—32分量尺描述。各期均值基于该期可用观测，样本构成不同，不可直接将均值之差视为同一批人的净变化。来源为已冻结修正数据的聚合描述表。'),p('增长形状与联合估计','afff0'),
 p('修正计分后的3274人家庭聚类自由形状CESD8模型，变化因子均值为0.037（SE=0.035，p=.290；沿用该单过程输出原时间参数化），不支持旧稿的显著下降判断。前批同样本聚类形状比较提示日历线性对自由形状的限制受到数据挑战（校正差异统计量8.452，df=3，p=.038）。本批将线性Y用于可解释的十年变化工作模型，不宣称它已成为最优形状；本批三类模型均共享这一限制。'),
 p('表2 预定模型族的采用状态','af3'),table(['规格','结构','合法成员／10','起点核查','可合并'],[[g['spec'],NAME[g['spec']],g['admissible'],g['start_stable'],g['eligible_for_conditional_pooling']] for g in gates]),
 p('采用门槛包含矩阵合法性与起点稳定性。未通过门槛的模型只进入诊断附件，不从中摘取显著系数作为实质结论。可合并表示固定模型下的估计可报告，不是认定该结构为真实机制。')]
 if pooled:
  nodes += [p('表3 固定工作模型下的四条条件关系','af3'),table(['规格','关系','估计','稳健MI SE','95%区间'],[[r['spec'],LABEL[r['label']],num(r['estimate']),num(r['se']),interval(r)] for r in pooled]),p('区间按全部十份参数与TECH3协方差合并；固定SY残差不作为一个待检验参数。不同增长形状的变化因子定义有所不同，不能仅比较显著性或系数绝对大小选择结构。'),p(findings+'。')]
 else:nodes += [p('本批没有模型族满足全部十份合法且起点稳定的采用要求，因此不生成正式MI路径表。该结果说明预定设计下的联合变化分解仍受限，不证明两过程不存在关联。')]
 nodes += [p('残差假设敏感性','afff0'),p('第一份插补的完整剖面见附录。每个固定残差点均重新估计其余参数，合法点与非法点分开标示。点估计同号、数值幅度接近和区间精确是三个不同判断；本稿不以“所有点都显著”定义稳健，也不合并不同固定点的区间构造95%区间。'),
 p('Discussion 讨论','affe'),p('本研究将代际关系的起点与后续变化分开考察。当前可报告的结果取决于明确的增长形状和残差设定；即使某一条件路径估计精确，也不能由此认定增加亲近度必然改善抑郁。观察性资料中的共同变化还可能涉及测量、共同访谈条件及未控制的时变因素。'),
 p('同期残差关联是一种允许共同时间因素进入测量层的结构对照。其拟合或参数改变可以提示增长层分解对残差结构的敏感性，但不能单独识别某个遗漏机制。零条件残差工作模型则通过强约束分配变化差异，必须与剖面共同解释；不能把约束后标准误缩小视为发现了隐藏机制。'),
 p('家内标准差、性别差和排行差的核心调节，以及H4.2b要求的社会经济组间调节差异，尚未在本批执行。原理论方向继续保留，现有历史输出不提供修正数据上的一致支持；未检验不等于效应为零。后续若恢复检验，应直接评价对应交互及其差异，不能比较两组星号。'),
 p('Limitations 局限','affe'),p('首先，亲近度量表的高分端堆积、各期样本流失和差异指标的资格总体，会限制可识别的变化信息。其次，本批仍以线性抑郁变化作为工作近似，尚未完成替代抑郁口径与四期／五期窗口对照。再次，家庭共同值和观测保持检查不证明MAR或插补与潜交互严格相容。最后，条件Rubin区间不纳入选模型的不确定性，剖面也不估计边界方差的置信区间。'),
 p('本稿据此报告合法工作假设下能够识别的关系及其限制，不将历史调节表、未执行检验或不合法父模型系数作为当前主结论。完整历史正文v47与附录v39保留在独立历史审计资料中，用于追溯而非替代当前证据。')]
 nodes += [p('本批采用判断与敏感性','afff0'),p('SW十份均合法，SY条件残差自由且为正，起点稳定，因此作为后续评审的主要工作模型候选；C1作为强约束敏感性对照，XLIN不合并。此判断依据结构与合法性，不依据P值。SW的基期亲近度—抑郁路径为−0.350，95%区间［−0.639，−0.061］，支持该工作模型下的负向基期关联。两类合法模型的变化关联均为负，但区间包含零且较宽。第一份插补五个固定残差点均合法，变化关联估计从−0.716到−0.479，区间宽度从约1.853变为0.458；其他两条预测变化的路径还发生符号改变。这说明估计与精度依赖残差假设，不能以某固定点较窄的区间替代完整MI推断。')]
 # 将本批实质裁定放在讨论前，避免埋入局限之后。
 decision=nodes[-2:];del nodes[-2:]
 pos=next(i for i,n in enumerate(nodes) if txt(n)=='Discussion 讨论')
 nodes[pos:pos]=decision
 nodes.insert(pos,p('前文保留测量说明中的附录表4.2.1、4.2.2指历史附录v39，现存于独立historical_audit资料；不作为本批修正数据的验证结果。'))
 for node in nodes:
  for t in node.findall('.//w:t',NS):
   if t.text:t.text=t.text.replace('本研究分以下四步进行。','本批按以下限定规格进行。').replace('如何影响后者的起始水平和变化趋势','与后者的起始水平和变化趋势有何关联')
 assert '本研究分以下四步进行' not in ''.join(txt(n) for n in nodes)
 refs,items=bibliography(nodes)
 nodes += [p('参考文献','affe'),p('以下按保留正文的既有Zotero引文字段元数据整理；本次未增加新引文，未将元数据解析称为原文核验或原生插件刷新。')]+[p(s) for s in refs]
 recs=[save_doc(source,'PP_LGCM_review_v48_round2C_NOT_RELEASED.docx',nodes,changes+['Historical body nodes75–264 replaced by current strategy/results/discussion; complete original archived unchanged'])]
 ap=[p('附录v40：检查点C模型证据与推断说明','affe'),p('本附录与正文v48使用同一检查点C结果。旧附录v39完整保留为历史审计附件；其中历史表不并入本批正式证据。'),p('A. 数据、尺度与控制','afff0'),p('每份模型使用3274人、2410家庭及24项基期编码列。CESD8使用2012年修正均值13.5754428833、标准差4.2592386459统一标准化；X沿用已冻结wfdms系列，入口尺度核对见input_scale_check.json。线性载荷0、.4、.6、.8、1，以十年为单位。自由形状X固定首末载荷0和1。'),p('控制变量映射','af3')]
 controls=json.loads((ROOT/'RUN_CONTRACT.json').read_text())['main_controls'];ap += [table(['模型列','源变量'],[[f'c{i+1}',v] for i,v in enumerate(controls)]),p('B. 完整模型采用表','afff0')]
 members=readcsv(ROOT/'results/member_dispositions.csv');ap += [table(['模型','状态','SY残差','可采用'],[[r['id'],r['status'],num(r['SY_residual'],6),r['usable']] for r in members]),p('C. 拟合指标','afff0'),table(['模型','CFI','TLI','RMSEA','SRMR'],[[r['id'],r['CFI'],r['TLI'],r['RMSEA_Estimate'],r['SRMR']] for r in fits]),p('D. 第一份插补的固定残差剖面','afff0'),table(['固定残差','路径','估计','SE','95%条件区间','合法'],[[num(r['tau'],2),r['label'],num(r['estimate']),num(r['se']),interval(r),r['usable']] for r in prof]),p('单份区间为固定规格下渐近Wald诊断。非法点仅保留定位信息；本表不是MI区间、置信集合或边界检验。')]
 if pooled:ap += [p('E. 条件MI合并与模拟精度','afff0'),table(['规格','路径','p','FMI','MCSE/SE','精度标记'],[[r['spec'],r['label'],num(r['p'],5),num(r['FMI'],5),num(r['MCSE_over_SE'],5),r['MCSE_flag']] for r in pooled]),p('MCSE/SE超过.05仅作报告标记，不自动追加插补。使用大样本完整数据自由度近似下的Rubin规则，协方差按同一参数顺序合并，不平均P值。')]
 ap += [p('F. 参数几何与追溯','afff0'),p('PSI为增长因子结构残差协方差，G为给定协变量后的增长因子联合协方差，THETA为测量残差协方差，SIGMA为模型蕴含的条件观测协方差。TECH3为参数估计协方差，不能替代上述潜变量几何检查。预定SY=0允许PSI/G的零特征值，其他负方差或额外秩亏仍不通过。'),p('完整输入、输出、TECH1/TECH3/TECH4、参数顺序绑定、局部残差、数据哈希、起点核查与独立复算记录见配套公开数据包。微观数据、真实人员／家庭标识和插补对象未公开。所有模型尝试与未采用结果均保留。')]
 aps=OLD/'manuscript/PP_LGCM_appendix_review_v39_round2B_build03_NOT_RELEASED.docx'
 recs.append(save_doc(aps,'PP_LGCM_appendix_review_v40_round2C_NOT_RELEASED.docx',ap,['Current appendix rebuilt; full v39 archived unchanged']))
 hist=OUT/'historical_audit';hist.mkdir(exist_ok=True);arch=[]
 for src in [source,source.with_suffix('.pdf'),aps,aps.with_suffix('.pdf')]:
  dest=hist/src.name;shutil.copy2(src,dest);assert sha(src)==sha(dest);arch.append({'file':dest.name,'source_sha256':sha(src),'bytes':dest.stat().st_size})
 (OUT/'historical_audit_manifest.json').write_text(json.dumps(arch,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'revision_receipts.json').write_text(json.dumps(recs,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/'audit/retained_citation_metadata.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'documents':len(recs),'eligible_families':good,'retained_references':len(refs),'historical_files':len(arch),'status':'XML_CHECKED_NATIVE_WORD_PENDING'},ensure_ascii=False))
if __name__=='__main__':main()
