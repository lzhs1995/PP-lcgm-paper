"""依据真实原生回执和落盘终态完成工作台验收；不重新启动R/Mplus。"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=Path('C:/Users/LZHS/.clauder_workbench/evidence')
TASK='pp-lgcm-round2f-20261011'
FORMAL_TASK='pp-lgcm-round2f-formal-20261011'
JOB='796384d5'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def harness(args,stem):
 run=subprocess.run([sys.executable,'-X','utf8','-m','clauder_workbench',*args],capture_output=True,text=True,encoding='utf-8')
 (ROOT/'audit'/f'{stem}_console.txt').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
 assert run.returncode==0,run.stdout+'\n'+run.stderr
 obj=json.loads(run.stdout);assert obj['decision']=='PASS'
 path=next(EVIDENCE.glob('*'+obj['evidence_id']+'.json'));shutil.copy2(path,ROOT/'audit'/f'{stem}.json')
 return path,obj
def main():
 S=read(ROOT/'runtime/selection_2f.json');assert S['terminal']['status'] in ['FINISHED','STOPPED_WITH_REASON']
 assert read(ROOT/'runtime/progress.json')['stage']=='results_2f_written'
 assert read(ROOT/'audit/independent/independent_verification.json')['status']=='PASS'
 assert read(ROOT/'manuscript/delivery/manuscript_validation.json')['status']=='PASS'
 assert read(ROOT/'manuscript/delivery/visual_review.json')['status']=='PASS'
 receipts=list((ROOT/'models').glob('*/engine_receipt.json'))
 assert len(receipts)==read(ROOT/'runtime/budget_status.json')['calls']
 assert all(read(p)['status'] in ['EXITED','TIMEOUT','INTERRUPTED'] for p in receipts)
 for name,digest in read(ROOT/'contracts/FROZEN_CODE_2F.json').items():assert sha(ROOT/'code'/name)==digest
 assert sha(ROOT/'contracts/RUN_CONTRACT_2F.json')==(ROOT/'contracts/FROZEN_CONTRACT_SHA256.txt').read_text().strip()
 native=read(ROOT/'runtime/native_formal_terminal.json')
 raw=json.dumps(native,ensure_ascii=False)
 # 原始工具响应与派生完成状态明确区分；不得用文件名冒称原生完成。
 native_done='ROUND2F_PIPELINE_ENDED FINISHED' in raw and 'No job found' not in raw and not native.get('isError')
 assert native_done,'Native terminal marker absent; inspect saved results and actual tool response'
 assert 'Job '+JOB+' started' in json.dumps(read(ROOT/'runtime/native_formal_submit.json'))
 # 初版误用连接测试任务标识查正式作业；失败记录保留，不改写历史task_key。
 initial=ROOT/'audit/workbench_initial'
 if not initial.exists():
  initial.mkdir()
  for name in ['workbench_completion_console.txt','completion_state.json']:
   if (ROOT/'audit'/name).exists():shutil.copy2(ROOT/'audit'/name,initial/name)
  failed=next(EVIDENCE.glob('*d18f4450-f5fb-46ce-93f7-47c4f7fbe29f.json'));shutil.copy2(failed,initial/failed.name)
  (initial/'README.md').write_text('# 首次工作台验收记录\n\n首次验收以连接测试任务pp-lgcm-round2f-20261011查正式作业完成记录而失败。正式作业实际登记在pp-lgcm-round2f-formal-20261011，job_id为796384d5。修复仅在报告层分别验收原生接口与正式作业并关联原始证据；未重跑估计、修改冻结代码或放宽数值门槛。最终回执为上级workbench_completion.json。\n',encoding='utf-8')
 from clauder_workbench.inflight import load_inflight
 inflight=load_inflight(FORMAL_TASK)
 if inflight:
  assert inflight['job_id']==JOB and inflight['task_key']==FORMAL_TASK
  archive_path,archive=harness(['async-guard','complete','--task-key',FORMAL_TASK,'--job-id',JOB,
   '--reason','Actual native terminal and all durable engine receipts verified; no new model calls'],'formal_async_complete')
 else:
  archive=read(ROOT/'audit/formal_async_complete.json');archive_path=next(EVIDENCE.glob('*'+archive['evidence_id']+'.json'))
 archived=archive['extra'].get('archived_path')
 assert archived and archive['job_id']==JOB and archive['task_key']==FORMAL_TASK
 assert read(Path(archived))['job_id']==JOB
 shutil.copy2(archived,ROOT/'audit/formal_async_inflight_archived.json')
 source_files=['runtime/native_formal_submit.json','runtime/native_formal_terminal.json','runtime/selection_2f.json',
  'runtime/progress.json','results/DECISION_2F.json','audit/independent/independent_verification.json',
  'audit/formal_async_complete.json','audit/formal_async_inflight_archived.json']
 state=dict(status='completed',scientific_project_complete=False,new_model_calls=0,
  queue_terminal=S['terminal'],completed_attempts=len(receipts),native_job_id=JOB,
  task_binding=dict(native_smoke=TASK,formal_async=FORMAL_TASK),
  evidence_type='derived completion check linked to original native tool response and persistent files',
  sources=[dict(path=f,sha256=sha(ROOT/f)) for f in source_files],created_utc=datetime.now(timezone.utc).isoformat())
 (ROOT/'audit/completion_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 parent=read(ROOT/'runtime/native_gate_complete.json')['evidence_id']
 parent_path=next(EVIDENCE.glob('*'+parent+'.json'))
 # 两个原任务键分别通过各自门槛，再把两条真实证据链关联；不冒用task_key。
 common=['completion-check','--mode','formal','--io-mode','durable_files',
  '--require-transport-class','NATIVE_MCP_OK','--state-file',str(ROOT/'audit/completion_state.json')]
 native_check_path,native_check=harness(common+['--task-key',TASK,'--parent-evidence',str(parent_path),
  '--require-native-smoke','--native-smoke-max-age-min','600','--require-file',
  'file::'+str(ROOT/'runtime/native_formal_terminal.json')+',min_bytes=100,max_age_h=24'],'workbench_native_completion')
 args=common+['--task-key',FORMAL_TASK,'--require-job-complete',
  '--parent-evidence',str(parent_path),str(native_check_path),str(archive_path)]
 for name,minimum in [('audit/independent/verified_calls.csv',len(receipts)),('reports/CALLS.csv',len(receipts)),('reports/SEVEN_ISSUES.csv',7)]:
  args+=['--require-file','validation::'+str(ROOT/name)+f',min_rows={minimum},min_bytes=100,max_age_h=24']
 for name in ['results/DECISION_2F.json','manuscript/delivery/manuscript_validation.json','manuscript/delivery/visual_review.json']:
  args+=['--require-file','file::'+str(ROOT/name)+',min_bytes=100,max_age_h=24']
 path,obj=harness(args,'workbench_completion')
 dest=ROOT/'audit/workbench';dest.mkdir(exist_ok=True);todo=[obj['evidence_id'],parent];seen=set()
 for p in EVIDENCE.glob('20261011*async_guard*.json'):
  record=read(p)
  if record.get('task_key')==FORMAL_TASK:todo.append(record['evidence_id'])
 while todo:
  key=todo.pop()
  if key in seen:continue
  seen.add(key);p=next(EVIDENCE.glob('*'+key+'.json'));o=read(p);shutil.copy2(p,dest/p.name);todo+=o.get('parent_evidence_ids',[])
 print('WORKBENCH_COMPLETION_PASS',obj['evidence_id'],flush=True)
if __name__=='__main__':main()
