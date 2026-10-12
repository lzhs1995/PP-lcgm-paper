"""Windows假引擎测试；Python替身，不调用Mplus，不接触CFPS数据。"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
R=Path('C:/Users/LZHS/pp_lgcm_review/round2F_20261011');W=R/'development'/('engine_test_'+str(time.time_ns()));W.mkdir()
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def make(name,caps=4,engine=1000):
 r=W/name
 for d in ['code','contracts','runtime','models']:(r/d).mkdir(parents=True)
 shutil.copy2(R/'code/r2f_engine.py',r/'code/r2f_engine.py')
 c=json.loads((R/'contracts/RUN_CONTRACT_2F.json').read_text());c['budget']['categories']={'SMOKE':caps};c['budget']['engine_seconds']=engine
 (r/'contracts/RUN_CONTRACT_2F.json').write_text(json.dumps(c));(r/'contracts/FROZEN_CONTRACT_SHA256.txt').write_text(H(r/'contracts/RUN_CONTRACT_2F.json'))
 (r/'contracts/FROZEN_CODE_2F.json').write_text(json.dumps({'r2f_engine.py':H(r/'code/r2f_engine.py')}))
 (r/'runtime/batch_window.json').write_text(json.dumps({'start_epoch':time.time()}));return r
def run(r,name,sleep=0.2,cap=10,hook=None,alter=False):
 d=r/'models'/name;d.mkdir()
 (d/'model.inp').write_text('import time\ntime.sleep('+str(sleep)+')\nopen("model.out","w").write("FAKE ENGINE ONLY")\n')
 (d/'data.dat').write_text('1 2 3\n')
 j=dict(root=str(r),dest=str(d),id=name,category='SMOKE',cap_seconds=cap,input_sha256=H(d/'model.inp'),data_sha256=H(d/'data.dat'),mplus=sys.executable)
 (d/'input_contract.json').write_text(json.dumps(j))
 if alter:(d/'model.inp').write_text('changed')
 e=os.environ.copy()
 if hook:e['R2F_ENGINE_TEST_CLOCK_JUMP']=hook
 p=subprocess.run([sys.executable,str(r/'code/r2f_engine.py'),str(d/'input_contract.json')],env=e,capture_output=True,text=True,encoding='utf-8',timeout=60)
 (d/'test_console.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
 return d,p,json.loads((d/'engine_receipt.json').read_text()) if (d/'engine_receipt.json').exists() else None
tests=[]
def ck(n,x):tests.append({'test':n,'passed':bool(x)});assert x,n
r=make('normal');d,p,a=run(r,'A');ck('normal_and_full_wall',a['status']=='EXITED' and a['seconds']==a['wall_seconds'])
ck('awake_released',json.loads((d/'keep_awake_release.json').read_text())['state']=='RELEASED')
p=subprocess.run([sys.executable,str(r/'code/r2f_engine.py'),str(d/'input_contract.json')],capture_output=True)
ck('receipt_idempotent',json.loads((r/'runtime/budget_status.json').read_text())['calls']==1)
d,p,a=run(r,'B',sleep=30,cap=2);ck('ordinary_timeout',a['status']=='TIMEOUT' and a['seconds']>=2)
d,p,a=run(r,'C',sleep=30,cap=3,hook='1.5:100');ck('polling_gap_not_deducted',a['status']=='TIMEOUT' and a['seconds']>=100 and a['seconds']==a['wall_seconds'] and a['gap_seconds']>90)
r=make('cap',caps=1);run(r,'A');d,p,a=run(r,'B');ck('category_cap',a is None and 'CALL_CAP' in p.stderr)
r=make('budget',engine=1);d,p,a=run(r,'A');ck('engine_budget',a is None and 'BUDGET_EXHAUSTED' in p.stderr)
r=make('input');d,p,a=run(r,'A',alter=True);ck('input_hash',a is None and 'AssertionError' in p.stderr)
r=make('contract');f=r/'contracts/RUN_CONTRACT_2F.json';f.write_text(f.read_text()+' ');d,p,a=run(r,'A');ck('contract_hash',a is None and 'Frozen execution contract changed' in p.stderr)
(R/'audit/CONSENSUS_ENGINE_TESTS.json').write_text(json.dumps({'fake_engine':True,'tests':tests,'passed':all(x['passed'] for x in tests),'work':str(W)},indent=2))
print('CONSENSUS_ENGINE_TESTS',len(tests),'PASS')
