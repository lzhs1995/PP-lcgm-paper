"""从终态与原始参数整理审阅表；不执行新的估计。"""
from pathlib import Path
from datetime import datetime,timezone
import json,os,re
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
import pandas as pd
from scipy.stats import norm
from raw_mplus import RawModel,sha,rubin

ROOT=Path(__file__).resolve().parents[1]
LABELS={'bii':'IX→IY','bis':'IX→SY','bss':'SX→SY（Z₀=0）','bsyiy':'IY→SY',
        'gi0':'Z₀→IY','gs0':'Z₀→SY（SX=0）','dc':'SX×Z₀→SY'}
STATUS={'USABLE':'单次合法','INADMISSIBLE_SY_ONLY':'SY负残差','INADMISSIBLE':'不合法',
        'ESTIMATION_FAILED':'估计失败','TIMEOUT':'超时'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def csv(p,rows,columns=None):pd.DataFrame(rows,columns=columns).to_csv(p,index=False,encoding='utf-8-sig')

def quantities(d):
 raw=RawModel(d);key=pd.read_csv(d/'key_paths.csv');labels=key.label.tolist()
 idx=key.parameter.to_numpy(int)-1;Q=raw.q[idx];V=raw.v[np.ix_(idx,idx)]
 result={l:(float(Q[j]),float(np.sqrt(V[j,j]))) for j,l in enumerate(labels)}
 C=read(ROOT/'contracts/RUN_CONTRACT_2F.json')
 if 'dc' in labels:
  for point in ['raw_zero','positive_median','P90']:
   a=np.zeros(len(labels));a[labels.index('bss')]=1;a[labels.index('dc')]=C['support_points_SD'][point]
   result[point]=(float(a@Q),float(np.sqrt(a@V@a)))
  a=np.zeros(len(labels));a[labels.index('dc')]=C['support_points_SD']['P90']-C['support_points_SD']['raw_zero']
  result['P90_minus_raw_zero']=(float(a@Q),float(np.sqrt(a@V@a)))
 return raw,result

def main():
 S=read(ROOT/'runtime/selection_2f.json');assert S.get('terminal',{}).get('status') in ['FINISHED','STOPPED_WITH_REASON']
 R=ROOT/'reports';R.mkdir(exist_ok=True)
 receipts=[read(p) for p in sorted((ROOT/'models').glob('*/receipt.json'))]
 rows=[];diag=[];neg=[];lookup={};output_diagnostics=[]
 for r in receipts:
  mid=r['id'];d=ROOT/'models'/mid;e=read(d/'engine_receipt.json')
  row={k:r.get(k) for k in ['id','sample','spec','member','attempt','category','data_tag','status','N','households','points','processors','LL','sy']}
  row.update(wall_seconds=e['wall_seconds'],cpu_seconds=e.get('cpu_seconds'),keep_awake=e.get('keep_awake'),
             cap=e['limit_seconds'],overrun=max(0,e['seconds']-e['limit_seconds']),
             last_abs_change=r.get('convergence',{}).get('last_abs_change'),
             iterations=r.get('convergence',{}).get('iterations'),exact_LL_difference=r.get('exact_LL_difference'))
  lines=(d/'model.out').read_text(encoding='latin1').splitlines()
  flat=re.sub(r'\s+',' ',' '.join(lines))
  no_se='STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE COMPUTED' in flat
  row['output_diagnosis']='STANDARD_ERRORS_UNAVAILABLE' if no_se else r['status']
  if no_se:
   begin=next(i for i,l in enumerate(lines) if 'THE STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES' in l)
   end=next(i for i in range(begin,len(lines)) if lines[i].strip()=='MODEL RESULTS')
   diagnostic=dict(id=mid,receipt_status=r['status'],output_diagnosis=row['output_diagnosis'],
      normal_termination_text=r['normal'],source=f'models/{mid}/model.out',sha256=sha(d/'model.out'),
      first_line=begin+1,last_line=end,excerpt='\n'.join(lines[begin:end]).strip(),
      estimates_saved=(d/'estimates.dat').exists(),tech3_bytes=(d/'tech3.dat').stat().st_size,
      parameter_covariance_available=False,
      scope='Raw Mplus warning; no valid SE/CI. Frozen receipt and queue decision are preserved.')
   output_diagnostics.append(diagnostic)
  if (d/'parameters_high_precision.csv').exists():
   raw,q=quantities(d);lookup[mid]=(raw,q)
   row['saved_LL']=float(raw.extra['H0 Loglikelihood'])
   psi_id=raw.lookup('PSI','SY','SY',number=True)
   row['SY_SE']=float(raw.se[psi_id-1]) if psi_id else None
   for v in raw.parameters.to_dict('records'):
    if v['matrix'] in ['psi','theta'] and v['row']==v['column'] and v['estimate']<0:
     neg.append(dict(id=mid,**v))
   if 'dc' in q:row.update(dc=q['dc'][0],dc_SE=q['dc'][1])
   if r['sample']=='CFPS':
    for label,(est,se) in q.items():
     diag.append(dict(id=mid,spec=r['spec'],status=r['status'],data_tag=r['data_tag'],label=label,
        estimate=est,se=se,lower=est-norm.ppf(.975)*se,upper=est+norm.ppf(.975)*se,
        p=2*norm.sf(abs(est/se)),inference='single model only; inadmissible rows diagnostic'))
  rows.append(row)
 csv(R/'CALLS.csv',rows);csv(R/'DIAGNOSTIC_PARAMETERS.csv',diag)
 write(R/'OUTPUT_DIAGNOSTICS.json',output_diagnostics)
 (R/'OUTPUT_DIAGNOSTICS.md').write_text('# 原始输出严重诊断与程序回执\n\n'
   '本表保留原程序状态，另列原始Mplus诊断。没有重新估计、修改冻结代码或回写原始回执。\n\n'+
   '\n\n'.join(f"## {d['id']}\n\n程序状态：`{d['receipt_status']}`；原始输出诊断：`{d['output_diagnosis']}`。"
     f"原始OUT第{d['first_line']}—{d['last_line']}行：\n\n```text\n{d['excerpt']}\n```\n\n"
     '输出未产生estimates.dat，TECH3为零字节；并非上传损坏。没有可报告的标准误或区间，不能视为完整控制敏感性通过。'
     for d in output_diagnostics),encoding='utf-8')
 csv(R/'NEGATIVE_VARIANCES.csv',neg,['id','parameter','matrix','row','column','estimate','se'])
 comps=[]
 for step in ['F1','F2']:
  P=S.get(step,{})
  for a,b,mode in [('q30a','q30b','start'),('q20a','q30a','integration'),('q20b','q30b','integration')]:
   if not all(k in P.get('runs',{}) and P['runs'][k]['id'] in lookup for k in [a,b]):continue
   ra,rb=P['runs'][a],P['runs'][b];ma,qa=lookup[ra['id']];mb,qb=lookup[rb['id']]
   for label in qa:
    ea,sa=qa[label];eb,sb=qb[label];lim=max(.001,.01*sb) if mode=='start' else .05*sb
    comps.append(dict(step=step,mode=mode,a=ra['id'],b=rb['id'],label=label,estimate_a=ea,estimate_b=eb,
        se_a=sa,se_b=sb,absolute_change=abs(ea-eb),change_over_high_precision_SE=abs(ea-eb)/sb,
        SE_relative=abs(sa-sb)/sb,path_tolerance=lim,
        coefficient_precision_pass=bool(abs(ea-eb)<=lim and abs(sa-sb)/sb<=.05),
        LL_difference_printed=ra['LL']-rb['LL'],LL_difference_saved=float(ma.extra['H0 Loglikelihood']-mb.extra['H0 Loglikelihood']),
        a_status=ra['status'],b_status=rb['status'],
        scope='prespecified key path' if label in LABELS else 'supplementary derived slope; no new test'))
 csv(R/'NUMERIC_PATH_COMPARISONS.csv',comps)
 # 区分同积分的收敛/起点变化与跨积分比较，不把冻结汇总的跨设置行当纯EM效应。
 prior=read(ROOT/'baseline/models/CFPS_SD_E1B_01_diagnostic/receipt.json')
 conv=[]
 for r in rows:
  if r['sample']=='CFPS' and r['spec']=='E1B' and r['category']=='NUMERIC':
   conv.append(dict(id=r['id'],old_id=prior['id'],old_points=20,new_points=r['points'],
      old_LL=prior['LL'],new_LL=r['LL'],delta_LL=r['LL']-prior['LL'],
      comparison='same integration; tighter stopping and different full start source' if r['points']==20 else 'integration and stopping/start settings both differ'))
 csv(R/'CONVERGENCE_COMPARISON.csv',conv)
 (ROOT/'results/README_2F.md').write_text(
  '# 冻结程序汇总的解释边界\n\n'
  'TIGHT_VS_DEFAULT_2F.csv是不同轮次所选结果的描述，F1比较新30点与旧20点，F2比较新30点与旧15点，'
  '不能把差异全部归于EM收敛。同20点E1B对照另见根目录CONVERGENCE_COMPARISON.csv；起点来源仍不同。\n\n'
  'SE_DECOMPOSITION_2F.csv的N2 not run表示本轮没有该诊断；没有家族时MI文件只有明确的无结果说明。'
  '进度中的active及合同per_call_active_seconds沿用接口命名；本轮实际记账为gross engine wall，'
  '秒数与finished_epoch−started_epoch逐调用相等，未扣除轮询间隙或待机。\n',encoding='utf-8')
 # 旧无/有交互模型的缩放差仅做复核；非法模型不作为检验参照。
 lr=[]
 for a,b in [('CFPS_SD_E0_01_base','CFPS_SD_E1_01_q15'),
              ('CFPS_SD_E0_01_base','CFPS_SD_E1_01_q15_repair'),
              ('CFPS_SD_E0B_01_diagnostic','CFPS_SD_E1B_01_diagnostic')]:
  x=RawModel(ROOT/'baseline/models'/a);y=RawModel(ROOT/'baseline/models'/b)
  cx=x.extra['H0 Scaling Correction Factor for MLR'];cy=y.extra['H0 Scaling Correction Factor for MLR']
  cd=(x.p*cx-y.p*cy)/(x.p-y.p)
  lr.append(dict(model0=a,model1=b,cd=float(cd),naive_LR=float(2*(y.extra['H0 Loglikelihood']-x.extra['H0 Loglikelihood'])),
     scaled_LR_status='not computable with nonpositive cd' if cd<=0 else 'descriptive only; admissibility/boundary limitations remain'))
 csv(R/'BASELINE_LR_DIAGNOSTIC.csv',lr)
 budget=read(ROOT/'runtime/budget_status.json')
 batch=read(ROOT/'runtime/batch_window.json')
 terminal_time=datetime.strptime(S['terminal']['utc'],'%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc)
 timing=dict(calls=len(receipts),sample_counts=pd.Series([r['sample'] for r in receipts]).value_counts().to_dict(),
     status_counts=pd.Series([r['status'] for r in receipts]).value_counts().to_dict(),
     engine_wall_seconds=sum(r['wall_seconds'] for r in rows),cpu_seconds=sum(r['cpu_seconds'] or 0 for r in rows),
     batch_wall_seconds=round(terminal_time.timestamp()-batch['start_epoch']),
     batch_wall_precision='approximately one second; queue terminal timestamp is printed to seconds',
     budget_snapshot_wall_seconds=budget['wall_seconds'],budget_snapshot_updated_utc=budget['updated_utc'],
     queue_terminal_utc=S['terminal']['utc'],budget=read(ROOT/'contracts/RUN_CONTRACT_2F.json')['budget'],
     overrun_calls=[r['id'] for r in rows if r['overrun']>0],
     all_actual_calls_keep_awake=all(r['keep_awake']=='ON' for r in rows))
 families={name:{'status':F['status'],'n_usable':sum(m['status']=='USABLE' for m in F['members'].values()),
     'repairs':len(F['repairs'])} for name,F in (S.get('families') or {}).items()}
 write(R/'SUMMARY.json',dict(round='Round2F',decision=S.get('decision'),terminal=S['terminal'],timing=timing,
     F1_pass=S.get('F1',{}).get('passed'),F2_pass=S.get('F2',{}).get('passed'),families=families,
     no_new_microdata=True,project_complete=False,created_utc=datetime.now(timezone.utc).isoformat()))
 print(json.dumps(dict(decision=S.get('decision'),families=families,timing=timing),ensure_ascii=False))

if __name__=='__main__':main()
