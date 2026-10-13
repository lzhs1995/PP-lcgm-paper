"""仅复算保存聚合结果和核对稿件来源；绝不调用Mplus或读取个体数据。"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,re,zipfile,math
import numpy as np
from scipy.stats import t as student_t
from lxml import etree as E
import document_support as ds
import pdf_checks as pc

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'manuscript/delivery';EV=ROOT/'evidence'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def writecsv(p,data):
 keys=list(dict.fromkeys(k for row in data for k in row))
 with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)
def tree(path):
 with zipfile.ZipFile(path) as z:return E.fromstring(z.read('word/document.xml'))
NUM=r'[−-]?(?:\d+\.\d+(?:[eE][+-]?\d+)?|\.\d+|\d+)'
def nums(s):return re.findall(NUM,s)
def fl(s):return float(s.replace('−','-'))

def recompute():
 sd=read(EV/'SD_E0_parameter_matrices.json')['SD_E0'];Q=np.array(sd['Q']);U=np.array(sd['U'])
 assert Q.shape==(10,6) and U.shape==(10,6,6)
 W=U.mean(axis=0);B=np.cov(Q,rowvar=False,ddof=1);T=W+1.1*B;est=Q.mean(axis=0);se=np.sqrt(np.diag(T))
 lam=1.1*np.diag(B)/np.diag(T);df=9/lam**2;crit=student_t.ppf(.975,df)
 saved=rows(EV/'SD_E0_paths.csv');out=[]
 for j,r in enumerate(saved):
  got=dict(estimate=est[j],se=se[j],lower=est[j]-crit[j]*se[j],upper=est[j]+crit[j]*se[j],p=2*student_t.sf(abs(est[j]/se[j]),df[j]))
  for k,v in got.items():assert abs(v-float(r[k]))<1e-10,(r['label'],k,v,r[k])
  out.append(dict(model='SD E0',label=r['label'],**{k:float(v) for k,v in got.items()}))
 sw=rows(EV/'SW_members.csv');labs=['bii','bis','bss','bsyiy'];sq=np.array([[float(r[l]) for l in labs] for r in sw])
 wr=list(csv.reader((EV/'SW_within_covariance.csv').open(encoding='utf-8-sig')));ww=np.array([[float(v) for v in r[1:]] for r in wr[1:]])
 sb=np.cov(sq,rowvar=False,ddof=1);st=ww+1.1*sb;sest=sq.mean(axis=0);sse=np.sqrt(np.diag(st));slam=1.1*np.diag(sb)/np.diag(st);sdf=9/slam**2
 for j,r in enumerate([r for r in rows(EV/'SW_paths.csv') if r['spec']=='SW']):
  got=dict(estimate=sest[j],se=sse[j],lower=sest[j]-student_t.ppf(.975,sdf[j])*sse[j],upper=sest[j]+student_t.ppf(.975,sdf[j])*sse[j],p=2*student_t.sf(abs(sest[j]/sse[j]),sdf[j]))
  for k,v in got.items():assert abs(v-float(r[k]))<1e-10,(r['label'],k,v,r[k])
  out.append(dict(model='SW',label=r['label'],**{k:float(v) for k,v in got.items()}))
 return out

def trace():
 out=[]
 for d in sorted((EV/'models').iterdir()):
  raw=(d/'model.out').read_text(encoding='utf-8',errors='replace')
  if 'TECHNICAL 8 OUTPUT' not in raw:continue
  tail=raw.split('TECHNICAL 8 OUTPUT')[-1]
  matches=re.findall(r'^\s*(\d+)\s+(-?[\d.]+D[+-]\d+)\s+([\d.]+)\s+([\d.]+)\s+(EM|QN|FS)\s*$',tail,re.M)
  if not matches:continue
  criterion=re.search(r'Derivative\s+([\d.]+D[+-]\d+)',raw)
  receipt=read(d/'receipt.json');last=matches[-1]
  out.append(dict(id=d.name,terminal_iteration=int(last[0]),last_printed_abs_change=last[2],last_algorithm=last[4],QN_steps=';'.join(x[0] for x in matches if x[4]=='QN'),FS_steps=';'.join(x[0] for x in matches if x[4]=='FS'),printed_derivative_criterion=criterion.group(1) if criterion else '',exact_LL=receipt.get('exact_LL',''),source=str((d/'model.out').relative_to(ROOT)),sha256=ds.sha(d/'model.out')))
 f={r['id']:r for r in out};a=f['CFPS_SD_E1B_01_F1_q30a'];b=f['CFPS_SD_E1B_01_F1_q30b']
 assert a['terminal_iteration']==54 and a['FS_steps']=='34'
 assert b['terminal_iteration']==83 and b['QN_steps']=='65;81'
 assert abs((b['exact_LL']-a['exact_LL'])-.000412)<1e-9
 arows=rows(EV/'models/CFPS_SD_E1B_01_F1_q30a/parameters_high_precision.csv');brows=rows(EV/'models/CFPS_SD_E1B_01_F1_q30b/parameters_high_precision.csv')
 assert len(arows)==len(brows)==134
 diffs=[]
 for ar,br in zip(arows,brows):
  assert [ar[k] for k in ['parameter','matrix','row','column']]==[br[k] for k in ['parameter','matrix','row','column']]
  diffs.append(dict(parameter=ar['parameter'],matrix=ar['matrix'],row=ar['row'],column=ar['column'],difference_over_reference_SE=abs(float(ar['estimate'])-float(br['estimate']))/float(br['se'])))
 return out,max(diffs,key=lambda r:r['difference_over_reference_SE'])

def evidence_map():
 claims=read(OUT/'result_claims.json');mt=tree(OUT/'PP_LGCM_scoped_final_candidate.docx');text=pc.text(mt)
 for r in claims:
  path=ROOT/r['source'];assert ds.sha(path)==r['source_sha256']
  selector=json.loads(r['selector']);selected=[x for x in rows(path) if all(x[k]==v for k,v in selector.items())];assert len(selected)==1
  q=selected[0];f=r['field'];value=ds.interval(q) if f=='interval' else ds.pvalue(q[f]) if f=='p' else ds.number(q[f])
  assert value==r['display'] and value in text
  r['check']='EXACT_SELECTED_SOURCE_AND_FORMAT';r['type']='empirical_result'
 # 正文其他数字逐个列出：设计常数/年份/引文/编号与实证估计分开。
 bt=tree(ROOT/'baseline/manuscripts/PP_LGCM_review_v51_round2F.docx');bn=list(bt.find('w:body',ds.NS))
 numeric=[]
 for pr in read(OUT/'main_paragraph_sources.json'):
  value=pr['text'];original=value
  for r in claims:
   if r['location']==f"正文内容段{pr['content_index']}":value=value.replace(r['display'],'〔结果已绑定〕')
  # 引文域显示的年份和模型/表格/假设编号只列一致性清单。
  nd=list(mt.find('w:body',ds.NS))[pr['body_index']]
  for visible in re.findall(r'（[^）]*(?:19|20)\d{2}[^）]*）',value):
   for token in nums(visible):numeric.append(dict(location=f"正文段{pr['body_index']}",display=token,type='citation_year_or_citation_metadata',source='baseline/manuscripts/PP_LGCM_review_v51_round2F.docx',check='PRESERVED_CITATION_OR_REFERENCES'))
   value=value.replace(visible,'〔引文〕')
  value=re.sub(r'(?:H\d+(?:\.\d+)?[ab]?|E[01]B?|Z₀|[XY][01]|[gsbi]+0|MI\d+|A\d+|表\d+)',lambda m:'〔编号〕',value)
  sources=['evidence/'+s for s in pr['sources']]
  if pr['baseline_nodes']:sources.append('baseline/manuscripts/PP_LGCM_review_v51_round2F.docx')
  for token in nums(value):
   typ='design_or_method_constant';check='SOURCE_BOUND_METHOD_OR_DESIGN';src=sources
   if token in ['2012','2016','2018','2020','2022']:
    typ='study_year';src=['evidence/observed_longitudinal_descriptives.csv'];check='YEAR_IN_OBSERVED_WAVES'
   elif token in ['3274','2410','24']:
    typ='sample_or_adjustment';src=['evidence/Z_CONTRACT.json'];check='EXACT_SAMPLE_CONTRACT'
   elif token in ['1.41','1.84']:
    typ='single_MI_diagnostic';src=['evidence/NUMERIC_PATH_COMPARISONS.csv'];check='ROUND_100_TIMES_SE_RATIO'
   elif '.' in token and len(token.split('.')[-1])>=8 and fl(token)>.1:
    typ='baseline_standardization';src=['evidence/Z_CONTRACT.json','evidence/observed_longitudinal_descriptives.csv'];check='ROUNDED_BASELINE_MOMENT'
   elif token=='3871':typ='citation_page';src=['evidence/LITERATURE_VERIFICATION.csv'];check='LOCAL_SOURCE_RECORD'
   elif token=='95':src=['baseline/manuscripts/PP_LGCM_review_v51_round2F.docx'];check='CONFIDENCE_LEVEL_PROTOCOL'
   if not src:src=['reporting/main_content.json'];check='IDENTIFIER_OR_SCOPE_NOT_EMPIRICAL_RESULT'
   numeric.append(dict(location=f"正文段{pr['body_index']}",label='',field='',display=token,estimate='',se='',lower='',upper='',model='SW / SD E0' if typ not in ['single_MI_diagnostic'] else 'E1B MI01',N=3274,households=2410,MI=1 if typ=='single_MI_diagnostic' else 10,source=';'.join(src),source_sha256=';'.join(ds.sha(ROOT/x) for x in src),selector=json.dumps({'baseline_nodes':pr['baseline_nodes'],'context':original},ensure_ascii=False),adoption='单份诊断' if typ=='single_MI_diagnostic' else '方法或设计事实',check=check,type=typ))
 # 表2拟合范围直接核对逐成员CSV；保留原采用/起点结论的独立来源。
 fit=rows(EV/'SW_fit.csv');tables=read(OUT/'expected_tables.json');ft=[t for t in tables if t['title'].startswith('表2 ')][0]
 for row in ft['rows']:
  subset=[r for r in fit if r['id'].startswith(row[0]+'_MI')];assert len(subset)==10
  for j,k in [(2,'CFI'),(3,'TLI'),(4,'RMSEA_Estimate')]:
   v=[float(r[k]) for r in subset];display=f'{min(v):.3f}–{max(v):.3f}';assert display==row[j]
   claims.append(dict(location='表2 '+row[0]+' '+k,label=k,display=display,model=row[0],N=3274,households=2410,MI=10,source='evidence/SW_fit.csv',source_sha256=ds.sha(EV/'SW_fit.csv'),selector=json.dumps({'id_prefix':row[0]+'_MI'}),adoption='可报告模型的描述性拟合' if row[0]!='XLIN' else '不合法模型诊断',check='EXACT_MIN_MAX_OF_TEN_MEMBERS',type='empirical_fit'))
 # 表内其他数值及表注，逐格绑定母版/结果；标识符不充当统计证据。
 for tb in tables:
  if tb['document']!='main':continue
  for ri,row in enumerate([tb['headers']]+tb['rows']):
   for ci,cell in enumerate(row):
    if not nums(cell):continue
    if tb['title'].startswith(('表3 ','表4 ')) and ci in [1,2,3,4] and ri>0:continue
    if tb['title'].startswith('表2 ') and ci in [2,3,4] and ri>0:continue
    claims.append(dict(location=f"{tb['title'].split()[0]}行{ri}列{ci}",display=cell,source='baseline/manuscripts/expected_tables.json;reporting/main_content.json',source_sha256=ds.sha(ROOT/'baseline/manuscripts/expected_tables.json')+';'+ds.sha(ROOT/'reporting/main_content.json'),adoption='定义、家族状态或编号',type='table_definition_or_status',check='TABLE_PROVENANCE_AND_NUMBERING'))
 # 表注的样本和调整量每次出现分别登记。
 mapped={r['body_index'] for r in read(OUT/'main_paragraph_sources.json')}
 for i,node in enumerate(mt.find('w:body',ds.NS)):
  val=pc.text(node)
  if node.tag==ds.W+'p' and i not in mapped and val.startswith('注：'):
   claims.append(dict(location=f'正文表注段{i}',display=val,source='evidence/Z_CONTRACT.json;evidence/SD_E0_multiplicity.csv',source_sha256=ds.sha(EV/'Z_CONTRACT.json')+';'+ds.sha(EV/'SD_E0_multiplicity.csv'),type='table_note',adoption='方法与多重性说明',check='SAMPLE_AND_ORIGINAL_HOLM_FAMILY'))
 # 检验明确的非结果数值，不用输出出现即代表估计可靠。
 z=read(EV/'Z_CONTRACT.json');assert z['samples']['SD_Z0']['N']==3274 and z['samples']['SD_Z0']['households']==2410 and len(z['samples']['SD_Z0']['ctrl_index'])==24
 nr=rows(EV/'NUMERIC_PATH_COMPARISONS.csv')
 for lab,want in [('dc','1.41'),('bss','1.84')]:
  r=[r for r in nr if r['step']=='F1' and r['mode']=='start' and r['label']==lab][0]
  assert f"{100*float(r['change_over_high_precision_SE']):.2f}"==want
 mo=rows(EV/'observed_longitudinal_descriptives.csv');assert {int(r['year']) for r in mo}=={2012,2016,2018,2020,2022}
 for var,mean,sd in [('wfd_m','4.1089078464','0.7092542690'),('ces8','13.5754428833','4.2592386459')]:
  rr=[r for r in mo if r['year']=='2012' and r['variable']==var][0];assert f"{float(rr['mean']):.10f}"==mean and f"{float(rr['sd']):.10f}"==sd
 for k,expected in [('ref_mean','4.8578066046'),('ref_sd','10.2070583983')]:assert f"{z['z']['SD'][k]:.10f}"==expected
 multi=[r for r in rows(EV/'SD_E0_multiplicity.csv') if r['z']=='SD' and r['spec']=='E0'];assert len(multi)==2 and all(float(r['holm'])==1 and int(r['family_size'])==4 for r in multi)
 protocol=read(EV/'MI_protocol.json');assert (protocol['m'],protocol['maxit'],protocol['donors'])==(10,30,5)
 lit=(EV/'LITERATURE_VERIFICATION.csv').read_text(encoding='utf-8-sig');assert '3871' in lit and '02654075241283974' in lit
 return claims+numeric

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
 for r in read(ROOT/'reports/EVIDENCE_SOURCES.json')+read(ROOT/'reports/FROZEN_INPUTS.json'):
  assert ds.sha(ROOT/r['snapshot'])==r['sha256']
  if args.prepare and Path(r['source']).exists():assert ds.sha(Path(r['source']))==r['sha256']
 pooled=recompute();tr,largest=trace();emap=evidence_map()
 c=Counter(r['sample'] for r in rows(EV/'CALLS_2E.csv'));assert c=={'CFPS':28,'SYNTHETIC':6},c
 if args.prepare:
  writecsv(ROOT/'FINAL_EVIDENCE_MAP.csv',emap)
  writecsv(ROOT/'reports/RECOMPUTED_MAIN_RESULTS.csv',pooled)
  writecsv(ROOT/'reports/CONVERGENCE_TRACE_LOCAL.csv',tr)
 else:
  delivered=rows(ROOT/'FINAL_EVIDENCE_MAP.csv');assert len(delivered)==len(emap)
  for a,b in zip(delivered,emap):
   for k,v in b.items():assert a[k]==str(v),(k,a[k],v)
 result=dict(status='PASS',new_mplus_calls=0,main_numeric_evidence_rows=len(emap),recomputed_paths=len(pooled),trace_calls=len(tr),A19_counts=dict(c),largest_all_parameter_start_difference=largest,scope='Saved aggregates only; no microdata refit; design facts source-bound; Word/PDF cells checked separately')
 dump(ROOT/'reports/EVIDENCE_VERIFICATION.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
