"""从终态结果和经审阅的编辑片段构建v51/v43；只替换document.xml。"""
from pathlib import Path
from copy import deepcopy,copy
import json,zipfile,re
from lxml import etree as E
import pandas as pd
import document_support as ds

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'baseline/manuscripts'
NS=ds.NS;W=ds.W

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def rows(node):return [['\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in c.findall('w:p',NS)) for c in r.findall('w:tc',NS)] for r in node.findall('w:tr',NS)]
def table(title,headers,data,widths=None):return dict(type='table',title=title,headers=headers,rows=data,widths=widths)
def fmt(x,d=3):return ds.number(x,d)
def estimate(row):return fmt(row['estimate'])+' ('+fmt(row['se'])+')'
def interval(row):return ds.interval(row)
def paragraph_like(node,value):
 # 无域、脚注、图形的文本段才允许重建；其他段使用人工编辑XML片段。
 assert not node.xpath('.//w:instrText|.//w:fldChar|.//w:footnoteReference|.//w:drawing',namespaces=NS)
 p=E.Element(W+'p',attrib=dict(node.attrib))
 old=node.find('w:pPr',NS)
 if old is not None:p.append(deepcopy(old))
 r=E.SubElement(p,W+'r')
 rp=node.find('.//w:rPr',NS)
 if rp is not None:r.append(deepcopy(rp))
 t=E.SubElement(r,W+'t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value
 return p

def dynamic():
 S=read(ROOT/'runtime/selection_2f.json');assert S['terminal']['status'] in ['FINISHED','STOPPED_WITH_REASON']
 summary=read(ROOT/'reports/SUMMARY.json');calls=pd.read_csv(ROOT/'reports/CALLS.csv');dp=pd.read_csv(ROOT/'reports/DIAGNOSTIC_PARAMETERS.csv')
 pooled=pd.read_csv(ROOT/'results/POOLED_KEY_PATHS_2F.csv');slopes=pd.read_csv(ROOT/'results/CONDITIONAL_SLOPES_2F.csv')
 old=read(BASE/'expected_tables.json');T={x['title'].split()[0]:x for x in old}
 def adopted(f):return (S.get('families') or {}).get(f,{}).get('status')=='COMPLETE_10_USABLE'
 def delta(f):return pooled[(pooled.family==f)&(pooled.label=='dc')].iloc[0].to_dict()
 def pilot_text(step):
  p=S.get(step,{})
  if not p:return '未执行'
  if p.get('passed'):return 'MI01积分与双起点通过'
  status=[r['status'] for r in p.get('runs',{}).values()]
  if any(s=='INADMISSIBLE_SY_ONLY' for s in status):return 'SY负残差，数值准入未通过'
  if status and all(s=='USABLE' for s in status):return '单次均合法；双起点一致性未通过'
  return '数值准入未通过；见附表A22'
 def final_text():
  if adopted('E1'):
   d=delta('E1');return f"SD自由E1完成十份同规格MI，δ={fmt(d['estimate'])}（95%区间{interval(d)}）；主检验及多重性见表5a。"
  if adopted('E1B'):
   d=delta('E1B');return f"SD仅E1B完成十份MI，在SY条件残差固定为0的强约束下，δ={fmt(d['estimate'])}（条件95%区间{interval(d)}）；没有形成自由残差的调节推断。"
  return 'SD自由E1与E1B均未形成通过预定数值及家族验收的十份MI调节结果；没有可报告的新调节合并估计。'
 new={k:{} for k in ['main','appendix']}
 conclusion=final_text()
 new['main']['2']=["摘要：本文使用中国家庭追踪调查2012—2022年五期资料，考察多子女家庭代际亲近度、家内相对差异与老年抑郁症状轨迹的关联。共同队列含3274名基期年龄大于60岁的受访者，复用10份家庭—个人分层协变量插补。SW父工作模型保留同波测量残差相关，亲近度采用自由形状，抑郁采用十年日历线性近似。SW基期亲近度与基期抑郁的关联为−0.350（95%区间[−0.639, −0.061]），变化关联为−0.246（[−1.442, 0.949]），估计不精确。既有SD E0十份可采用，但基期Z₀与抑郁潜在基期、变化的两条路径区间均包含0。本轮只对SD执行严格收敛、20/30点积分、双完整起点及约束敏感性。"+conclusion+"H4资源差异尚未执行。结果条件于工作模型和现有插补；观测Z₀不等同于潜IZ，数值失败或宽区间不表示效应不存在。"]
 new['main']['108']=["Round2E的SD E0十份结果继续保留，两条Z₀路径均未获统计支持且区间较宽；其他三分支仍含不合法成员，未合并。Round2F仅更新SD调节与有限敏感性。"+conclusion]
 formal=[]
 names=[('SD','标准差','3274 / 2410'),('SEXGAP','性别差','2339 / 1730'),('OLDEST','老大差','3159 / 2320'),('SONGAP','长子差','2894 / 2134')]
 for code,name,ng in names:
  if code=='SD' and adopted('E1'):
   d=delta('E1');m=pd.read_csv(ROOT/'results/MULTIPLICITY_2F.csv').iloc[0]
   formal.append([name,ng,'10/10',estimate(d),interval(d),ds.pvalue(d['p'])+' / '+ds.pvalue(m.holm),'30点／严格准则；通过'])
  else:formal.append([name,ng,'无合并','—','—','—',pilot_text('F2') if code=='SD' else 'Round2E首份未通过；本轮未重跑'])
 strong=[['SD：SY@0','3274 / 2410','无合并','—','—','—',pilot_text('F1')]]
 if adopted('E1B'):
  d=delta('E1B');strong=[['SD：SY@0','3274 / 2410','10/10',estimate(d),interval(d),ds.pvalue(d['p']),'30点／严格准则；通过']]
 new['main']['115']=[table('表5a',['分支','人数 / 户数','MI','δ (SE)','95%区间','P / Holm P','数值及采用状态'],formal,[800,1150,700,1100,1450,1250,2550]),
   '表5b SD的SY条件残差固定为0：强约束敏感性（条件MI）',
   table('表5b',['规格','人数 / 户数','MI','δ (SE)','条件95%区间','P','数值及采用状态'],strong,[900,1150,700,1100,1450,600,3100])]
 new['main']['116']=["表5只列完整通过验收的家族估计；单次诊断参数见附表A22—A23，不能替代MI。E1B区间条件于SY残差固定为0，不包含选择该限制的不确定性，亦不进入核心δ的Holm族。数值方法为一维30点积分、绝对/相对EM变化准则10⁻⁵/10⁻⁹；具体未通过项目逐项保留。SD原始零对应Z₀=−0.475926，−1不对应允许的原始SD，不作为主展示点。实际支持点及斜率可报告范围见附表A11、A24。"]
 hyp=deepcopy(T['表7']['rows'])
 for r in hyp:
  if r[0]=='H1.2':r[2]='SD E0：Z₀→IY −0.006 [−0.098, 0.086]；Z₀→SY 0.034 [−0.146, 0.213]，Holm P均1.000，未获支持；宽区间不是没有关联的证据。潜IZ/SZ未检验。'
  if r[0]=='H1.4':r[2]='老大差、长子差E0均含不合法成员，未合并，表4无估计；两分支不互相替代。'
  if r[0]=='H2.1':r[2]=conclusion+' 不将负向调节点估计命名为“弱化更强”。'
  if r[0]=='H2.2':r[2]='当前乘积仅含SX变化；较高IX水平的缓冲未检验。即使存在SX×Z₀，也须结合另一边际关系解释，不重复计为两个发现。'
 new['main']['123']=[table('表7',T['表7']['headers'],hyp,[850,2500,5650])]
 new['main']['126']=[conclusion+' E1B固定给定预测量后的额外SY差异为零；本轮不能因此确定人口残差为零，也不能用E0替代调节或H4。数值未通过是当前计算与验收事实，不等同于证明理论不可识别或真实调节为零。']
 pd.DataFrame(hyp,columns=['hypothesis','prediction','current_evidence']).to_csv(ROOT/'reports/HYPOTHESES.csv',index=False,encoding='utf-8-sig')
 # 累计家族状态；旧三分支按真实失败原因保留。
 fam=deepcopy(T['附表A9']['rows'])
 for r in fam:
  if r[0]=='性别差' and r[1]=='E1':r[4]='01首次估计失败（信息矩阵病态）；修复停滞、跨待机后超时；02—10未执行'
  if r[0]=='标准差' and r[1]=='E1':
   f=(S.get('families') or {}).get('E1',{});r[2]=str(sum(m['status']=='USABLE' for m in f.get('members',{}).values()))+'/10'
   r[3]='已合并' if adopted('E1') else '未合并';r[4]=pilot_text('F2')+('；02—10依合同完成' if adopted('E1') else '；未完成完整家族')
 f=(S.get('families') or {}).get('E1B',{});n_legal=sum(m['status']=='USABLE' for m in f.get('members',{}).values())
 if not f and any(r['status']=='USABLE' for r in S.get('F1',{}).get('runs',{}).values()):n_legal=1
 fam.insert(2,['标准差','E1B',str(n_legal)+'/10',
     '强约束条件MI' if adopted('E1B') else '未合并',pilot_text('F1')+'；单次诊断不计为完整家族'])
 family_headers=deepcopy(T['附表A9']['headers']);family_headers[2]='单份合法成员'
 new['appendix']['26']=[table('附表A9',family_headers,fam,[900,650,850,1400,5200])]
 # 支持点旧数据保留，只填入已采用家族的条件斜率。
 support=deepcopy(T['附表A11']['rows']);preferred='E1' if adopted('E1') else 'E1B' if adopted('E1B') else None
 for i,p in enumerate(['raw_zero','positive_median','P90']):
  support[i][-1]='无通过验收的调节家族'
  if preferred:
   d=slopes[(slopes.family==preferred)&(slopes.point==p)].iloc[0].to_dict();support[i][-1]=preferred+('（SY@0）' if preferred=='E1B' else '')+'：'+fmt(d['estimate'])+' '+interval(d)
 new['appendix']['32']=[table('附表A11',T['附表A11']['headers'],support,[700,1200,1150,1200,900,1050,2800])]
 # 完整控制样本，只列已实际调用。
 cc=calls[(calls['sample']=='CFPS')&(calls.data_tag=='CC')];ccrows=[]
 for _,r in cc.iterrows():
  if not len(dp[dp.id==r.id]):
   ccrows.append([r.spec,'全部',str(int(r.N))+' / '+str(int(r.households)),
     '标准误无法计算' if r.output_diagnosis=='STANDARD_ERRORS_UNAVAILABLE' else r.status,'—','—'])
  for l in ['gi0','gs0','dc']:
   x=dp[(dp.id==r.id)&(dp.label==l)]
   if len(x):
    d=x.iloc[0];ccrows.append([r.spec,l,str(int(r.N))+' / '+str(int(r.households)),r.status,estimate(d),interval(d)])
 if not ccrows:ccrows=[['—','—','2830 / 2105','未执行','—','—']]
 new['appendix']['38']=['本轮完整控制样本的实际调用如下，均为单份诊断；非法输出参数仅作诊断，不作可报告效应。',
    table('附表A13',['规格','路径','人数 / 户数','单次状态','估计 (SE)','单份95%区间'],ccrows,[650,750,1300,2000,1500,2800])]
 if any(cc.output_diagnosis=='STANDARD_ERRORS_UNAVAILABLE'):
  new['appendix']['38'].append('完整控制E0虽打印正常终止，但Mplus明确警告标准误无法计算、模型可能未识别，首先涉及参数126（SX残差），条件数为−0.280×10⁻⁶，并列出更多相关参数。未生成参数保存文件，TECH3为空；程序回执保留EXTRACTION_FAILED。没有可报告SE或区间；未据此证明总体结构不可识别。完整控制交互未获准入，不能把本次调用写成稳健性通过。')
 issues=[['1 趋势、时间、窗口','部分解决','错误计分下的旧下降撤回；时间单位明确。量尺、窗口、SW的Y形状仍待独立批次。'],
 ['2 CES-D计分与范围','计分及入口关闭','共同八题、反向题、完整作答及基期标准化已绑定；跨期测量不变性另列。'],
 ['3 增长方差与识别','SW与SD E0可采用；调节另判','F1：'+pilot_text('F1')+'；F2：'+pilot_text('F2')+'。'+conclusion],
 ['4 拟合不足','父模型已有依据；调节有限','绝对拟合不从父模型外推。严格积分/起点核查与参数协方差另验；旧SB缩放分母非正不作LR检验。'],
 ['5 过度表述','具体修订完成；仍为阶段稿','H1.2/H1.4、性别差失败归因、文献类型限定、强约束与条件路径解释已更新；不宣称七项全部关闭。'],
 ['6 得分、调节与MI','具体数据缺口关闭；推断未全部完成',conclusion+' 现有MI相容性、Z₀测量误差和模型选择不确定性仍有范围限制。'],
 ['7 H4.2b','未执行','理论成分与组间差异分开；SX变化不代替IX水平缓冲；不得用绝对幅度或星号比较判支持。']]
 new['appendix']['41']=[table('附表A14',T['附表A14']['headers'],issues,[2000,2100,4900])]
 pd.DataFrame(issues,columns=['issue','status','scope']).to_csv(ROOT/'reports/SEVEN_ISSUES.csv',index=False,encoding='utf-8-sig')
 historic=deepcopy(T['附表A19']);historic['headers'][2]='墙钟秒（含待机）'
 new['appendix']['55']=[table('附表A19',historic['headers'],historic['rows'],[2500,1250,1200,1150,1500,1400])]
 prior=[]
 for mid in ['CFPS_SD_E0_01_base','CFPS_SD_E0B_01_diagnostic','CFPS_SD_E1_01_q15','CFPS_SD_E1_01_q15_repair','CFPS_SD_E1B_01_diagnostic']:
  d=ROOT/'baseline/models'/mid;r=read(d/'receipt.json');k=pd.read_csv(d/'key_paths.csv');x=k[k.label=='dc']
  prior.append([mid.replace('CFPS_SD_',''),str(r.get('points')) if r['spec'].startswith('E1') else '—',r['status'],fmt(r.get('LL')),fmt(r.get('sy'),6),estimate(x.iloc[0]) if len(x) else '—'])
 new['appendix']['58']=[table('附表A20',['规格 / 尝试','积分点','单次状态','打印LL','SY残差','单份δ (SE)'],prior,[1800,650,2100,1600,1100,1750])]
 append=[]
 numeric=calls[(calls['sample']=='CFPS')&(calls.category=='NUMERIC')]
 nr=[[r.spec+' / '+r.attempt.split('_')[-1],str(int(r.points)),
      {'USABLE':'单次合法','INADMISSIBLE_SY_ONLY':'SY负残差'}.get(r.status,r.status),
      fmt(r.LL),fmt(r.sy,6),fmt(r.get('dc'))+' ('+fmt(r.get('dc_SE'))+')',fmt(r.exact_LL_difference,6)] for _,r in numeric.iterrows()]
 append+=['附表A22 Round2F严格准则下的SD／MI01积分与起点核查',table('附表A22',['规格 / 起点','积分点','单次状态','打印LL','SY残差','δ (SE)','精确LL−打印LL'],nr,[1500,600,1500,1350,1300,1500,1250]),
     'a来源为Round2E合法E1B，b来源为同份合法E0；自由E1的a来源将固定零释放为明确正初值0.02。两套30点结果分别比较，并分别检验20→30点。F1：'+pilot_text('F1')+'；F2：'+pilot_text('F2')+'。双起点差值和逐路径容差见NUMERIC_PATH_COMPARISONS.csv；近似LL相同不代表路径已达到容差。数值未过不等同于已证明形式上不可识别。']
 fixed=calls[(calls['sample']=='CFPS')&((calls.attempt=='F5')|(calls.id=='CFPS_SD_E1B_01_F1_q30b'))];fr=[]
 for _,r in fixed.iterrows():
  cols=[]
  for point in ['raw_zero','positive_median','P90']:
   x=dp[(dp.id==r.id)&(dp.label==point)];cols.append(fmt(x.iloc[0]['estimate'])+' ('+fmt(x.iloc[0]['se'])+')' if len(x) else '—')
  fr.append([fmt(r.sy,3),r.status,fmt(r.LL),fmt(r.get('dc'))+' ('+fmt(r.get('dc_SE'))+')',*cols])
 append+=['附表A23 当前交互结构的固定SY正残差敏感性（MI01）',table('附表A23',['固定SY','单次状态','打印LL','δ (SE)','原始零b(z) (SE)','正值中位b(z) (SE)','P90 b(z) (SE)'],fr,[650,1800,1450,1250,1300,1250,1300]),
    '0点展示F1的30点b起点候选，是否通过完整数值准入仍以附表A22为准，不能仅凭单次合法采用。0.020/0.034/0.080为事前固定点，每点重估其他参数；这是单份描述性敏感性，不是人口方差的置信区间或完整MI稳健性。不挑选显著点。']
 pr=[]
 if 'family' in pooled:
  for _,d in pooled.iterrows():pr.append([d.family,d.label,estimate(d),interval(d),ds.pvalue(d.p),fmt(d.FMI,6),fmt(d.MCSE_over_SE,6)])
 if not pr:pr=[['无家族','—','—','—','—','—','—']]
 append+=['附表A24 Round2F完整家族的MI结果与精度',table('附表A24',['规格','路径','估计 (SE)','条件95%区间','P','FMI','MCSE/SE'],pr,[900,850,1500,2500,850,1150,1250]),conclusion]
 if 'family' in slopes:
  sr=[[d.family,d.point,estimate(d),interval(d),ds.pvalue(d.p)] for _,d in slopes.iterrows()]
  append+=['附表A24（续） 完整家族的条件斜率',table('附表A24（续）',['规格','支持点 / 对比','估计 (SE)','条件95%区间','P'],sr,[1050,2900,1500,2500,1050]),'P90−原始零与δ为同一检验；固定零模型的区间不包含约束选择不确定性。']
 top=calls[(calls['sample']=='CFPS')&(calls.data_tag=='TOP99')];tr=[]
 for _,r in top.iterrows():tr.append([r.spec,r.status,str(int(r.N))+' / '+str(int(r.households)),fmt(r.get('dc'))+' ('+fmt(r.get('dc_SE'))+')',fmt(r.LL)])
 if not tr:tr=[['—','未执行：SD数值准入失败' if S.get('decision')=='C' else '未执行，具体理由见台账','3274 / 2410','—','—']]
 append+=['附表A25 Z₀顶端P99诊断',table('附表A25',['规格','状态','人数 / 户数','δ (SE)','打印LL'],tr,[900,3350,1500,1600,1650]),
     '事前P99=3.76636049455，准备数据改变32个值，其他列不变。数据准备不等于实际拟合；未执行时无统计结果，不能写成稳健性通过。该诊断只用MI01。']
 cr=[]
 for _,r in calls.iterrows():cr.append([r.id.replace('SYNTHETIC_SD_','合成 ').replace('CFPS_SD_','CFPS '),r.status,fmt(r.wall_seconds,2),fmt(r.cpu_seconds,2),fmt(r.sy,6),str(int(r.points)) if pd.notna(r.points) and r.spec!='E0' else '—'])
 append+=['附表A26 Round2F全部实际调用',table('附表A26',['调用','状态','墙钟秒','CPU秒','SY残差','积分点'],cr,[2750,2100,1050,1050,1300,750]),
    f"实际{summary['timing']['calls']}次调用；引擎墙钟累计{summary['timing']['engine_wall_seconds']:.2f}秒，从批次开始到队列终态约{summary['timing']['batch_wall_seconds']:.0f}秒。末次引擎账本快照为{summary['timing']['budget_snapshot_wall_seconds']:.2f}秒，未包含其后读回与收尾；终态时间戳只精确到秒。合成调用与CFPS调用分别列出，合成接口不作为研究发现。EXTRACTION_FAILED保留原程序回执，完整控制E0的根本输出问题是标准误无法计算（附表A13）；参数原始输出、回执、起点映射及未执行理由见公开包。"]
 return new,append,hyp

def main():
 out=ROOT/'manuscript/delivery';out.mkdir(parents=True,exist_ok=True)
 edits=read(ROOT/'manuscript/edits_static.json');dyn,append,hyp=dynamic()
 for kind in edits:edits[kind].update(dyn[kind])
 dump(ROOT/'manuscript/edits_applied.json',edits)
 files=[('main','PP_LGCM_review_v50_round2E.docx','PP_LGCM_review_v51_round2F.docx'),('appendix','PP_LGCM_appendix_review_v42_round2E.docx','PP_LGCM_appendix_review_v43_round2F.docx')]
 expected=[];receipts=[]
 for kind,old,new in files:
  with zipfile.ZipFile(BASE/old) as src:
   original=E.fromstring(src.read('word/document.xml'));tree=deepcopy(original);body=tree.find('w:body',NS)
   original_nodes=list(original.find('w:body',NS));changes=[]
   for i in range(len(original_nodes)-1,-1,-1):
    n=original_nodes[i];current=body[i]
    if kind=='main' and i==24:
     replacement=E.parse(str(ROOT/'manuscript/working/main/paragraph_024.xml')).getroot()
     assert replacement.xpath('.//w:instrText/text()',namespaces=NS)==n.xpath('.//w:instrText/text()',namespaces=NS)
     body.replace(current,replacement);changes.append(dict(index=i,edit='manually reviewed XML fragment'));continue
    if str(i) not in edits[kind]:continue
    replacements=[]
    for item in edits[kind][str(i)]:
     if isinstance(item,dict):replacements.append(ds.table(item['title'],item['headers'],item['rows'],kind,widths=item.get('widths'))[-1])
     elif E.QName(n).localname=='p':replacements.append(paragraph_like(n,item))
     else:replacements.append(ds.paragraph(item,keep=item.startswith('表')))
    body.remove(current)
    for offset,node in enumerate(replacements):body.insert(i+offset,node)
    changes.append(dict(index=i,edit='result-bound table or reviewed paragraph',before=ds.text(n),after=[ds.text(x) for x in replacements]))
   if kind=='appendix':
    at=len(body)-1
    for item in append:
     node=ds.table(item['title'],item['headers'],item['rows'],kind,widths=item.get('widths'))[-1] if isinstance(item,dict) else ds.paragraph(item,keep=item.startswith('附表'))
     body.insert(at,node);at+=1
   assert tree.xpath('.//w:instrText/text()',namespaces=NS)==original.xpath('.//w:instrText/text()',namespaces=NS),'Word field code changed'
   assert tree.xpath('.//w:footnoteReference/@w:id',namespaces=NS)==original.xpath('.//w:footnoteReference/@w:id',namespaces=NS)
   xml=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
   dst=out/new
   with zipfile.ZipFile(dst,'w') as z:
    for info in src.infolist():z.writestr(copy(info),xml if info.filename=='word/document.xml' else src.read(info.filename))
   with zipfile.ZipFile(dst) as z:
    assert z.testzip() is None and z.namelist()==src.namelist()
    preserved=[name for name in z.namelist() if name!='word/document.xml']
    assert all(z.read(name)==src.read(name) for name in preserved)
   title='';readable=[]
   for node in body:
    if node.tag==W+'p':
     s=ds.text(node);readable.append(s)
     if re.match(r'^(表\d+|附表A\d+)',s):title=s
    elif node.tag==W+'tbl':
     rr=rows(node);expected.append(dict(document=kind,title=title,headers=rr[0],rows=rr[1:]))
     readable.append('\n'.join(['| '+' | '.join(str(c).replace('|','\\|').replace('\n','<br>') for c in rr[0])+' |',
       '| '+' | '.join(['---']*len(rr[0]))+' |']+['| '+' | '.join(str(c).replace('|','\\|').replace('\n','<br>') for c in r)+' |' for r in rr[1:]]))
   if 'word/footnotes.xml' in src.namelist():
    used=set(tree.xpath('.//w:footnoteReference/@w:id',namespaces=NS))
    notes=E.fromstring(src.read('word/footnotes.xml'))
    footnotes=[n for n in notes if n.get(W+'id') in used]
    if footnotes:
     readable.append('文档脚注（原Word编号）：')
     readable.extend(n.get(W+'id')+'：'+ds.text(n) for n in footnotes)
   (out/(kind+'_readable.md')).write_text('\n\n'.join(readable),encoding='utf-8')
   receipts.append(dict(document=new,source=old,source_sha256=ds.sha(BASE/old),docx_sha256=ds.sha(dst),
      preserved_parts=len(preserved),field_codes_preserved=True,footnote_ids_preserved=True,changes=list(reversed(changes))))
  print('BUILT',new,flush=True)
 dump(out/'expected_tables.json',expected);dump(out/'revision_receipts.json',receipts)
 dump(out/'build_status.json',dict(preview=False,status='BUILT_PENDING_NATIVE_WORD_AND_PDF_VERIFICATION',versions=['v51','v43']))
 pd.DataFrame(hyp,columns=['hypothesis','prediction','current_evidence']).to_csv(out/'hypothesis_status.csv',index=False,encoding='utf-8-sig')

if __name__=='__main__':main()
