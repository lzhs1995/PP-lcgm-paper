"""依据人工撰写的内容清单组装候选稿；迁移原XML引文域，不刷新Zotero。"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import csv,hashlib,json,re,zipfile
from lxml import etree as E
import document_support as ds
import pdf_checks as pc

ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/'baseline/manuscripts'; OUT=ROOT/'manuscript/delivery'
NS=ds.NS;W=ds.W;R=ds.R
MAIN='PP_LGCM_scoped_final_candidate';APP='PP_LGCM_scoped_supplement'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvrows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def load_doc(name):
 with zipfile.ZipFile(BASE/name) as z:parts={n:z.read(n) for n in z.namelist()}
 tree=E.fromstring(parts['word/document.xml'])
 return parts,tree,list(tree.find('w:body',NS))
MP,MT,M=load_doc('PP_LGCM_review_v51_round2F.docx')
AP,AT,A=load_doc('PP_LGCM_appendix_review_v43_round2F.docx')
T={t['title'].split()[0]:t for t in read(BASE/'expected_tables.json')}
SW={r['label']:r for r in csvrows(ROOT/'evidence/SW_paths.csv') if r['spec']=='SW'}
SD={r['label']:r for r in csvrows(ROOT/'evidence/SD_E0_paths.csv')}
EVIDENCE=[];MIGRATION=[];PARA_RECORDS=[]

def p(text,kind=None):
 n=ds.paragraph(text,size=22)
 pr=n.find(W+'pPr')
 pr.find(W+'spacing').attrib.update({W+'after':'100',W+'line':'300',W+'lineRule':'auto'})
 if kind in ['heading','subheading','title']:
  E.SubElement(pr,W+'keepNext')
  E.SubElement(pr,W+'pStyle',{W+'val':'affe' if kind=='heading' else 'afff0' if kind=='subheading' else 'a3'})
  for rp in n.findall('.//w:rPr',NS):
   E.SubElement(rp,W+'b')
   rp.find(W+'sz').set(W+'val','30' if kind=='title' else '26' if kind=='heading' else '23')
 if kind=='title':E.SubElement(pr,W+'jc',{W+'val':'center'})
 return n

def fields(n):
 blocks=[];current=[];depth=0
 for ch in n:
  kinds=ch.xpath('.//w:fldChar/@w:fldCharType',namespaces=NS)
  if depth or 'begin' in kinds:
   current.append(deepcopy(ch));depth+=kinds.count('begin')-kinds.count('end')
   if depth==0:blocks.append(current);current=[]
 assert depth==0
 return blocks

def cited(i,template):
 original=M[i];blocks=fields(original);n=p('')
 for ch in list(n):
  if ch.tag!=W+'pPr':n.remove(ch)
 used=[]
 for x in re.split(r'(\{\{(?:\d+|note\d+)\}\})',template):
  if re.fullmatch(r'\{\{\d+\}\}',x):
   j=int(x[2:-2]);used.append(j);n.extend(deepcopy(blocks[j]))
  elif x.startswith('{{note'):
   j=x[6:-2];ref=original.xpath('.//w:footnoteReference[@w:id="'+j+'"]',namespaces=NS)[0]
   n.append(deepcopy(ref.getparent()))
  elif x:
   n.append(deepcopy(p(x).find(W+'r')))
 assert sorted(used)==list(range(len(blocks)))
 assert original.xpath('.//w:instrText/text()',namespaces=NS)==n.xpath('.//w:instrText/text()',namespaces=NS)
 MIGRATION.append(dict(source_body_index=i,destination='main',fields=len(blocks)))
 return n

def result_macro(match,location):
 fam,label,field=match.group(1).split('.');r=(SW if fam=='SW' else SD)[label]
 value=ds.interval(r) if field=='interval' else ds.number(r[field])
 source='evidence/'+('SW_paths.csv' if fam=='SW' else 'SD_E0_paths.csv')
 EVIDENCE.append(dict(location=location,label=label,field=field,display=value,estimate=r['estimate'],se=r['se'],lower=r['lower'],upper=r['upper'],model=fam if fam=='SW' else 'SD E0',N=3274,households=2410,MI=10,source=source,source_sha256=ds.sha(ROOT/source),selector=json.dumps({'spec':'SW','label':label} if fam=='SW' else {'label':label}),adoption='可报告：条件MI'))
 return value

def table(title,headers,rows,kind,widths=None):
 return ds.table(title,headers,rows,kind,widths=widths,total_width=9000,size=18 if len(headers)>5 else 20)

def add_table(key):
 if key=='definitions':
  return table('表1 本文采用的亲近度指标',['指标','定义','分析尺度'],[
   ['总体亲近度','每位父母与有效报告子女的亲近度平均分','按共同队列基期均值及SD标准化的纵向X'],
   ['基期亲近度离散','100 × 各有效子女评分的SD / 同波均值','仅取2012年相对SD，基期标准化为Z₀']], 'main',[1500,3600,3900])
 if key=='fit':
  t=T['表2'];return table('表2 父工作模型与结构敏感性的采用情况',t['headers'],t['rows'],'main',[700,750,1100,1100,1100,2050,2200])
 if key in ['sw','sd']:
  fam='SW' if key=='sw' else 'SD';source=SW if key=='sw' else SD
  rows=[];labels={'bii':'亲近度初始水平→抑郁初始水平','bis':'亲近度初始水平→抑郁变化','bss':'亲近度变化→抑郁变化','bsyiy':'抑郁初始水平→抑郁变化','gi0':'基期相对SD→抑郁潜在初始水平','gs0':'基期相对SD→抑郁变化'}
  for label in labels:
   if label not in source:continue
   r=source[label];row=[labels[label],ds.number(r['estimate']),ds.number(r['se']),ds.interval(r),ds.pvalue(r['p'])]
   rows.append(row)
   for f,display in [('estimate',row[1]),('se',row[2]),('interval',row[3]),('p',row[4])]:
    match=re.match(r'(.+)',fam+'.'+label+'.'+f)
    result_macro(match,'表3' if key=='sw' else '表4');EVIDENCE[-1]['display']=display
  title=('表3 SW主要工作模型的条件MI关系' if key=='sw' else '表4 SD E0无交互模型的条件MI关系')
  out=table(title,['路径','估计','SE','95%区间','P'],rows,'main',[3200,900,900,3000,1000])
  out.append(p('注：3274人、2410个家庭，10份同规格插补；基期24列调整，家庭聚类稳健估计。所有系数为工作模型下的条件关联。'+('SD的gi0与gs0沿用原四项家族校正，Holm P均为1.000；其余路径的P为未校正值。' if key=='sd' else '区间不含模型选择不确定性。')))
  return out
 if key=='hypotheses':
  return table('表5 本文保留命题的证据范围',['原假设','当前对应分析','判断边界'],[
   ['H1.1','SW与SD E0的初始水平关联','与负向预测相容；不能替代变化关联或因果效应。'],
   ['H1.2','基期相对SD的两条条件路径','未获明确支持；宽区间不是无关联的证据，且未检验潜在离散轨迹。'],
   ['H5.1','初始水平、初始水平与变化、变化共变','仅部分关系获得明确证据，不能判为三类关系同时成立。']], 'main',[800,2700,5500])+[p('注：编号沿用原假设。完整原预测、调节及异质性状态见附表A30；原假设全文见补充材料审计说明。')]
 raise KeyError(key)

def style_import(parts,nodes):
 """附录样式前缀化，避免与正文母版同名异义；无外部关系的表格原样迁移。"""
 source=E.fromstring(AP['word/styles.xml']);target=E.fromstring(parts['word/styles.xml'])
 ids={n.get(W+'styleId') for n in source.findall(W+'style')}
 for st in source.findall(W+'style'):
  st=deepcopy(st);st.set(W+'styleId','ap_'+st.get(W+'styleId'))
  st.attrib.pop(W+'default',None)
  for ref in st.findall('.//w:basedOn',NS)+st.findall('.//w:next',NS)+st.findall('.//w:link',NS):
   if ref.get(W+'val') in ids:ref.set(W+'val','ap_'+ref.get(W+'val'))
  target.append(st)
 for n in nodes:
  assert not n.xpath('.//@r:id|.//@r:embed|.//@r:link',namespaces=NS)
  for ref in n.findall('.//w:pStyle',NS)+n.findall('.//w:rStyle',NS)+n.findall('.//w:tblStyle',NS):
   if ref.get(W+'val') in ids:ref.set(W+'val','ap_'+ref.get(W+'val'))
 parts['word/styles.xml']=E.tostring(target,encoding='UTF-8',xml_declaration=True,standalone=True)

def write_doc(stem,nodes,appendix=False,imported=None):
 parts=dict(MP);tree=deepcopy(MT);body=tree.find('w:body',NS);section=deepcopy(M[-1]);body.clear()
 if appendix:
  section.find(W+'pgSz').attrib.update({W+'w':'15840',W+'h':'12240',W+'orient':'landscape'})
  for edge in ['top','bottom','left','right']:section.find(W+'pgMar').set(W+edge,'720')
  if imported:style_import(parts,imported)
 body.extend(nodes);body.append(section)
 # 两稿都以原正文包为母版，故迁移的注释、关系和书签ID已有同一命名空间。
 for kind in ['footnote','endnote']:
  key='word/'+kind+'s.xml';tr=E.fromstring(parts[key]);used={r.get(W+'id') for r in tree.findall('.//w:'+kind+'Reference',NS)}
  for n in list(tr):
   if int(n.get(W+'id'))>0 and n.get(W+'id') not in used:tr.remove(n)
  parts[key]=E.tostring(tr,encoding='UTF-8',xml_declaration=True,standalone=True)
 # 禁用自动链接更新；页面导出也不会保存或刷新正文引文。
 settings=E.fromstring(parts['word/settings.xml'])
 for x in settings.findall(W+'updateFields'):settings.remove(x)
 E.SubElement(settings,W+'updateFields',{W+'val':'false'})
 parts['word/settings.xml']=E.tostring(settings,encoding='UTF-8',xml_declaration=True,standalone=True)
 # 书签与段落标识保持每稿唯一，原成对书签ID不跨文档引用。
 for tag in ['bookmarkStart','bookmarkEnd']:
  ids=[x.get(W+'id') for x in tree.findall('.//w:'+tag,NS)];assert len(ids)==len(set(ids)),(stem,tag)
 parts['word/document.xml']=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
 dest=OUT/(stem+'.docx')
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in parts.items():
   info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,data)
 md=pc.readable_markdown(tree,False).split('\n',1)[1]
 (OUT/('appendix_readable.md' if appendix else 'main_readable.md')).write_text('范围收缩候选稿；零新增估计。\n'+md,encoding='utf-8')
 return tree,dict(document=dest.name,sha256=ds.sha(dest),tables=len(tree.findall('.//w:tbl',NS)),fields=sum(pc.citations(tree).values()),footnotes=len(tree.findall('.//w:footnoteReference',NS)))

def main():
 ds.TABLE_EVIDENCE.clear();content=read(ROOT/'reporting/main_content.json');main=[]
 for i,c in enumerate(content):
  if 'table' in c:main.extend(add_table(c['table']));continue
  value=re.sub(r'\[\[([^\]]+)\]\]',lambda m:result_macro(m,f'正文内容段{i}'),c['text'])
  node=cited(c['citation_from'],value) if 'citation_from' in c else p(value,c.get('kind'))
  if 56 in c.get('baseline_nodes',[]):
   node.append(deepcopy(p('调查介绍：').find(W+'r')))
   node.extend(deepcopy(M[56].findall('w:hyperlink',NS)))
  main.append(node);PARA_RECORDS.append(dict(content_index=i,body_index=len(main)-1,text=ds.text(node),sources=c.get('sources',[]),baseline_nodes=c.get('baseline_nodes',[]),kind=c.get('kind','prose')))
 main.append(p('参考文献','heading'))
 refs,inventory=ds.bibliography(main,extra=[('bartlett','2015',ds.text(M[138])),('van buuren','2011',ds.text(M[184]))])
 main.extend(p(x) for x in refs)
 # 原附录A1—A26继续保留；仅修已定位问题与版本说明。
 imported=deepcopy(A[:-1]);imported[0]=p('补充材料：采用结果、未检验范围与历史审计','title')
 imported[1]=p('本补充材料对应范围收缩候选稿。附表A1—A26保留Round2F及更早轮次的聚合证据，原正文表5a、5b、6和完整假设状态依次迁为A27—A30。历史表注中的“本轮”指其标明的估计轮次；本次收尾新增Mplus调用为零。原题v51/v43不覆盖。未获得可采用推断的记录不等于效应不存在。')
 imported[58]=p(ds.text(A[58]).replace('27次CFPS尝试，另有7次合成接口','28次CFPS尝试，另有6次合成接口'))
 imported[67]=p(ds.text(A[67])+' Round2F实际打印的EM绝对／相对LL变化准则为10⁻⁵／10⁻⁹，导数准则为0.001。F1/F2的a来源在54—57次迭代结束，b来源在83次结束且第65、81次有QN步；a来源也存在FS步，例如E1B q30a第34次，故不能概括为a没有加速。E1B q30a末次打印绝对变化为0.0000100，q30b为0.0000006；前者受打印舍入影响，不据此反推内部终止逻辑。30点b相对a的精确LL高约0.000412，自由E1相对对应E1B仅高约0.0018—0.0020。这提示停止精度可能解释微小差异，但不是已测得终点梯度、已证明不同最优点或已查清失败原因；非法负残差解的微小LL优势也不证明人口SY残差为零。')
 # A14更新为本次收尾的处理状态，不改动任何估计数值。
 old=T['附表A14'];issues=deepcopy(old['rows'])
 issues[4][1]='收缩稿完成表述收束';issues[4][2]='主文限SW与SD E0；长空表、原机制假设及失败记录移入补充材料，不将未检验写为无效应。'
 issues[5][2]=issues[5][2].replace('。 ','。')+' E0低FMI不能外推未运行E1B成员。'
 imported[43]=table('附表A14',old['headers'],issues,'appendix',[2000,2100,4900])[-1]
 app=list(imported)
 for key,new,title in [('表5a','A27','原自由SY残差调节家族状态'),('表5b','A28','原SY残差固定为零的强约束家族状态'),('表6','A29','H4原预测与操作化：未执行')]:
  t=T[key];app.extend(table('附表'+new+' '+title,t['headers'],t['rows'],'appendix'))
  if new=='A28':app.append(p('仅完整通过验收的家族才能报告MI估计。单份参数见附表A22—A23；支持点见A11，单份条件斜率见A23，A24说明没有完整家族。E1B固定给定IX、SX、IY、Z₀、SX×Z₀及控制后额外的SY随机差异为零，不等于所有人的SY相同；其区间不包含约束选择不确定性，不进入核心δ的Holm家族。'))
  if new=='A29':app.append(p(ds.text(M[125]).replace('理论部分','下列原假设审计部分')))
 hyp=deepcopy(T['表7']['rows'])
 for r in hyp:
  r[2]=r[2].replace('表4无估计','无可采用估计（见附表A10）').replace('见表6','见附表A29').replace('。 ','。')
 app.extend(table('附表A30 完整原假设与证据状态',T['表7']['headers'],hyp,'appendix',[850,2500,5650]))
 app.append(p('审计说明B：原研究问题、假设与扩展理论','heading'))
 app.append(p('以下保留原题阶段稿的研究问题、全部原假设与移出的扩展理论，不代表本候选稿已经完成相应检验。原假设中的因果措辞是历史预测的原文，不是当前研究结论。与当前分析直接相关的理论引注已迁入正文；未删失原引文域。完整未改动的理论上下文另见归档v51。'))
 main_fields={c['citation_from'] for c in content if 'citation_from' in c}
 archive=list(range(11,54))
 for i in archive:
  if i in main_fields or i in [12,19,20,26,27,53]:continue
  app.append(deepcopy(M[i]))
  if fields(M[i]):MIGRATION.append(dict(source_body_index=i,destination='appendix',fields=len(fields(M[i]))))
 # 迁移上述范围以外仍未使用的域，不能静默丢失。
 assigned={x['source_body_index'] for x in MIGRATION}
 for i,node in enumerate(M):
  if fields(node) and i not in assigned:
   app.append(deepcopy(node));MIGRATION.append(dict(source_body_index=i,destination='appendix',fields=len(fields(node))))
 app.append(p('审计说明C：原样本筛选与未执行分析的方法边界','heading'))
 app.append(p('本节保存v51的样本筛选及Round2F分析规则。这里的运行预算、未来批次和“本轮”用语均属历史记录，不是本次收尾的执行计划；零新增估计的停止规则优先。'))
 app.extend(deepcopy(M[i]) for i in range(58,63))
 for i in [73,74,79,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97]:app.append(deepcopy(M[i]))
 app.append(p('本次收尾不依据E0的低FMI预测未运行E1B的九份结果；不执行可选导数准则小试，不自动启动H4、其他差异分支、增长形状、窗口、量尺或新插补。'))
 app.append(p('补充材料参考文献','heading'))
 refs,_=ds.bibliography(app,extra=[('bartlett','2015',ds.text(M[138])),('van buuren','2011',ds.text(M[184]))]);app.extend(p(x) for x in refs)
 # 表格期望值从保留原表与人工定义的新表各自建立，不依赖PDF反向生成。
 expected=[]
 for kind,nodes in [('main',main),('appendix',app)]:
  title=''
  for node in nodes:
   if node.tag==W+'p' and re.match(r'^(?:附)?表(?:\d|A)',ds.text(node)):title=ds.text(node)
   if node.tag==W+'tbl':
    r=pc.xml_rows(node);expected.append(dict(document=kind,title=title,headers=r[0],rows=r[1:]))
 mt,mr=write_doc(MAIN,main)
 at,ar=write_doc(APP,app,True,imported)
 assert pc.citations(MT)==pc.citations(mt)+pc.citations(at),'引文域总清单变化'
 dump(OUT/'expected_tables.json',expected);dump(OUT/'citation_migration.json',MIGRATION)
 dump(OUT/'main_paragraph_sources.json',PARA_RECORDS);dump(OUT/'result_claims.json',EVIDENCE)
 dump(OUT/'build_status.json',dict(preview=False,mode='NO_NEW_ESTIMATION',new_mplus_calls=0,documents=[mr,ar],citations_original=sum(pc.citations(MT).values())))
 dump(OUT/'hypothesis_status.json',hyp)
 print(json.dumps([mr,ar],ensure_ascii=False))
if __name__=='__main__':main()
