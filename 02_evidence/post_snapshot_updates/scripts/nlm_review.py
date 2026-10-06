"""对已冻结的本轮PDF执行独立三审；原始响应与来源ID逐次落盘。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import sys, subprocess, time
sys.path.insert(0,r'C:\Users\LZHS\.agents\skills\mplusautomation-guide\scripts')
from nlm_reliability import compact_json, run_query
NLM=r'C:\Users\LZHS\.local\bin\nlm.exe';ROOT=OUT/'reviews';ROOT.mkdir(exist_ok=True)
def call(name,args):
 result=subprocess.run([NLM,*args,'--profile','default'],capture_output=True,timeout=420)
 stdout=result.stdout.decode('utf-8','replace');stderr=result.stderr.decode('utf-8','replace')
 writej(ROOT/(name+'.json'),{'returncode':result.returncode,'stdout':stdout,'stderr':stderr})
 if result.returncode:raise RuntimeError(name+' failed; inspect receipt')
 value=compact_json(stdout)
 if not isinstance(value,(dict,list)):raise RuntimeError(name+' missing JSON')
 return value
def upload():
 assert readj(OUT/'native/nlm_network_rule.json')['status']=='PASS'
 assert readj(OUT/'native/nlm_preflight.json')['notebook_list']['status']=='AUTH_VALID'
 receipt=readj(OUT/'manuscript/pdf_receipt.json')
 nbfile=ROOT/'notebook.json'
 if nbfile.exists(): nb=readj(nbfile)
 else:
  obj=call('notebook_create_raw',['notebook','create','PP-LGCM CFPS 七项审阅 20261005 v43-v37','--json'])
  nb={'id':obj.get('id') or obj.get('notebook_id')};assert nb['id'];writej(nbfile,nb)
 sources=[]
 for row in receipt['records']:
  pdf=Path(row['pdf']);assert sha(pdf)==row['pdf_sha256']
  record=ROOT/(pdf.stem+'_source.json')
  if record.exists(): s=readj(record)
  else:
   obj=call(pdf.stem+'_upload_raw',['source','add',nb['id'],'--file',str(pdf),'--wait','--wait-timeout','360','--json'])
   sid=obj.get('id') or obj.get('source_id');assert sid
   s={'id':sid,'filename':pdf.name,'path':str(pdf),'sha256':sha(pdf)};writej(record,s)
  sources.append(s)
 writej(ROOT/'source_manifest.json',{'notebook_id':nb['id'],'pdf_only':True,'sources':sources})
 print('PDF-only sources prepared',nb['id'],flush=True)
def query(passno,scoped=False,full=False):
 man=readj(ROOT/'source_manifest.json');sources=man['sources'];ids=[s['id'] for s in sources]
 for s in sources:assert sha(Path(s['path']))==s['sha256']
 common='仅检查本轮两个PDF：'+ '与'.join('['+s['filename']+']' for s in sources)+'。这是有明确历史结果和科学开放项的修订候选，不是正式放行稿。不要把已明确标注不可推断或历史结果的数字要求改成显著，也不要发明结果。'
 scope={1:'第一审：结构与数值绑定。核查正文与附录补充审计的测量范围、2016长短版、时间载荷、样本2225/1981/3274、八项敏感性终态、关键路径、原有表号图号和交叉引用。只列新增真实矛盾，区分PDF抽取伪影。',2:'第二审：方法与解释。核查量表20—80减20的转换、自由形状因子的时间单位、非官方问卷标记、死亡与缺失、因子得分不确定性、MI不能平均P值、正常终止与不可接受解、因果机制以及H4.2b的一致支持边界。',3:'第三审：格式与最终一致性。检查正文五处新修订和附录补充审计（补表R1—R3）是否有错字、断裂句、表格截断、编号或符号错误、旧稿叙述与当前结论混淆、未经证据支持的新增断言。'}[passno]
 prompt=common+scope+'每个问题给出文件名、PDF页码、原文短引、具体修改建议；引用两个来源。无新增问题则明确说明。末尾输出NEW_ISSUES_COUNT: N和A5_NO_NEW_ISSUES: YES或NO。'
 if scoped:
  scope={1:'核对3274、2225、1981的样本含义与8个敏感性模型终态是否一致。',2:'核对CESD8主分析、CESD20sc减20、2016非官方长短版标记、自由载荷时间单位及H4.2b的解释是否有矛盾。',3:'只核对新修订段落及附录补表R1—R3的格式、编号、符号及旧结果/新结果边界。'}[passno]
  prompt='同时依据'+ '与'.join('['+s['filename']+']' for s in sources)+'，'+scope+'引用两个来源，回答不超过500字；有问题给PDF页码和短引，无问题明确说无新增问题。末尾输出NEW_ISSUES_COUNT: N；A5_NO_NEW_ISSUES: YES或NO。'
 suffix='_scoped' if scoped else ''
 if full:
  scope={1:'全文第一审：逐页核查表图编号、正文交叉引用、样本数、系数符号、脚注与正文/附录一致性。',2:'全文第二审：核查方法、统计解释、引文用途、量尺与时间单位、缺失/插补、调节与因果语言。',3:'全文第三审：核查排版、符号、标题、表格跨页、正文引用附录、残留草稿说明及无来源断言。'}[passno]
  prompt='审查完整的'+ '与'.join('['+s['filename']+']' for s in sources)+'，不限于新补表。'+scope+'此稿明确区分历史估计、不可接受解和未放行结论；请指出真实内部矛盾或未充分标示的推断问题，不把已充分说明的科学局限当作必须变成显著结果的要求。每个真实问题给文件名、PDF页码、原文短引和修正建议；无问题明确说明。引用两个来源。末尾输出NEW_ISSUES_COUNT: N和A5_NO_NEW_ISSUES: YES或NO。'
  suffix='_full'
 result=run_query(NLM,man['notebook_id'],prompt,ids,ROOT/f'pass{passno}{suffix}',filename=sources[0]['filename'],profile='default',timeout=120 if scoped else 180,attempts=1)
 print('pass',passno,result['status'],flush=True)
 if result['status']!='PASS':raise RuntimeError('NLM response validation failed')
 if any(x['exit_code']!=0 for x in result['attempts']):raise RuntimeError('Nonzero exit cannot count as successful review')
if __name__=='__main__':
 if sys.argv[1]=='upload':upload()
 else:query(int(sys.argv[1]),'--scoped' in sys.argv,'--full' in sys.argv)
