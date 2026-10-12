"""独立复核公开原始结果，不读取微观数据、不重新拟合。"""
from pathlib import Path
import argparse,json,csv,os,re
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
import pandas as pd
from raw_mplus import RawModel,rubin,close,sha
from verify_model import verify_model
from verify_starts import verify_starts

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def verify_baseline(root,out):
 B=root/'baseline';mf=read(B/'SOURCE_MANIFEST.json')
 for r in mf['files']:assert sha(B/r['path'])==r['sha256'],r['path']
 Q=[];U=[]
 for k in range(1,11):
  d=B/'models'/f'CFPS_SD_E0_{k:02d}_base';raw=RawModel(d)
  key=pd.read_csv(d/'key_paths.csv');ids=key.parameter.to_numpy(int)-1;labels=key.label.tolist()
  Q.append(raw.q[ids]);U.append(raw.v[np.ix_(ids,ids)])
 result,*_=rubin(Q,U)
 actual=pd.read_csv(B/'results/POOLED_KEY_PATHS.csv')
 actual=actual[(actual.z=='SD') & (actual.spec=='E0')].set_index('label').loc[labels]
 close(actual[result.columns],result,'baseline SD E0 ten')
 result.insert(0,'label',labels);result.to_csv(out/'baseline_SD_E0_recomputed.csv',index=False)
 return dict(families=1,members=10,files=len(mf['files']))
def numeric(root,a,b,mode,diagnostic=False):
 allowed={'USABLE','INADMISSIBLE_SY_ONLY'} if diagnostic else {'USABLE'}
 if a.get('status') not in allowed or b.get('status') not in allowed:return False
 if a['structural_signature']!=b['structural_signature']:return False
 x=pd.read_csv(root/'models'/a['id']/'key_paths.csv').set_index('label');y=pd.read_csv(root/'models'/b['id']/'key_paths.csv').set_index('label').loc[x.index]
 d=np.abs(x.estimate-y.estimate);lim=.05*y.se if mode=='integration' else np.maximum(.001,.01*y.se)
 return bool((d<=lim).all() and (abs(x.se-y.se)/y.se<=.05).all() and (mode=='integration' or abs(a['LL']-b['LL'])<=.01))

def verify(root,out,terminal=False):
 out.mkdir(parents=True,exist_ok=True);rec=[];models={}
 baseline=verify_baseline(root,out)
 for d in sorted((root/'models').iterdir()):
  if not (d/'receipt.json').exists():continue
  a,m=verify_model(d);rec.append(a);models[d.name]=m
  j=read(d/'input_contract.json');r=read(d/'receipt.json');e=read(d/'engine_receipt.json')
  close([e['seconds']],[e['wall_seconds']],'gross time');assert e.get('test_hook') is None
  if r['status']=='USABLE' and j['spec']!='E0':
   assert r['criteria_as_requested'] and r['integration_dimensions']==1
   assert j['conv']=='tight' and j['processors']==1 and j['points'] in [20,30]
   assert abs(r['exact_LL_difference'])<=.01 and r['exact_LL_n_match']
  if j['spec']=='E1B':assert 'sy@0;' in (d/'model.inp').read_text().lower()
  if j['spec'].startswith('E1F'):
   val=int(j['spec'][3:])/1000
   if m:close([m.lookup('PSI','SY','SY')],[val],'fixed positive variance')
 for f,h in read(root/'contracts/FROZEN_CODE_2F.json').items():assert sha(root/'code'/f)==h,f
 assert sha(root/'contracts/RUN_CONTRACT_2F.json')==(root/'contracts/FROZEN_CONTRACT_SHA256.txt').read_text().strip()
 C=read(root/'contracts/RUN_CONTRACT_2F.json');bs=read(root/'runtime/budget_status.json')
 assert bs['calls']<=C['budget']['max_calls']
 for cat,n in C['budget']['categories'].items():assert sum(x['category']==cat for x in bs['rows'])<=n
 close([bs['engine_seconds']],[sum(read(root/'models'/x['id']/'engine_receipt.json')['seconds'] for x in bs['rows'])],'budget')
 starts=verify_starts(root,read(root/'upstream/START_SOURCES.json'))
 pd.DataFrame(starts).to_csv(out/'verified_full_starts.csv',index=False)
 nf=0
 if terminal:
  S=read(root/'runtime/selection_2f.json');assert S['terminal']['status'] in ['FINISHED','STOPPED_WITH_REASON']
  for step in ['F1','F2']:
   P=S.get(step)
   if not P:continue
   runs=P['runs'];sc=numeric(root,runs['q30a'],runs['q30b'],'start')
   ia=numeric(root,runs['q20a'],runs['q30a'],'integration',True);ib=numeric(root,runs['q20b'],runs['q30b'],'integration',True)
   assert sc==P['start_check']['passed'];assert ia==P['integration_a']['passed'];assert ib==P['integration_b']['passed']
   passed=sc and ia and ib and all(x['status']=='USABLE' and abs(x.get('exact_LL_difference',float('inf')))<=.01 and x.get('exact_LL_n_match') for x in [runs['q30a'],runs['q30b']])
   assert bool(passed)==P['passed']
   if passed:assert P['selected']['points']==30
  if all(k in S for k in ['F1','F2']):
   expected='A' if S['F1']['passed'] and S['F2']['passed'] else 'A1' if S['F2']['passed'] else 'B' if S['F1']['passed'] else 'C'
   assert expected==S['decision']
  pooled=pd.read_csv(root/'results/POOLED_KEY_PATHS_2F.csv');sl=pd.read_csv(root/'results/CONDITIONAL_SLOPES_2F.csv')
  for name,F in (S.get('families') or {}).items():
   members=F['members'];complete=set(members)==set(map(str,range(1,11))) and all(v['status']=='USABLE' for v in members.values())
   if F['status']!='COMPLETE_10_USABLE':assert not complete;continue
   assert complete and S['F2' if name=='E1' else 'F1']['passed']
   Q=[];U=[]
   for k in range(1,11):
    m=members[str(k)];assert m['sample']=='CFPS' and m['data_tag']=='Z0' and m['spec']==name and m['points']==30 and m['conv']=='tight' and m['member']==k
    actual=read(root/'models'/m['id']/'receipt.json');assert actual==m
    raw=models[m['id']];keys=pd.read_csv(root/'models'/m['id']/'key_paths.csv');ids=keys.parameter.to_numpy(int)-1;labels=keys.label.tolist()
    Q.append(raw.q[ids]);U.append(raw.v[np.ix_(ids,ids)])
   table,W,B,T=rubin(Q,U);actual=pooled[pooled.family==name].set_index('label').loc[labels]
   close(actual[table.columns],table,'Rubin ten',atol=1e-8)
   rv=1.1*np.diag(B)/np.diag(W);fmi=(rv+2/(table['df'].to_numpy()+3))/(1+rv)
   close(actual.FMI,fmi,'FMI',atol=1e-8)
   for _,row in sl[sl.family==name].iterrows():
    a=np.zeros(len(labels));a[labels.index('dc')]=row.z
    if 'minus' not in row.point:a[labels.index('bss')]=1
    ct,_,_,_=rubin(np.asarray(Q)@a,np.einsum('i,mij,j->m',a,np.asarray(U),a).reshape(10,1,1))
    close(row[ct.columns].astype(float),ct.iloc[0],'slope/contrast',atol=1e-8)
   nf+=1
  multi=pd.read_csv(root/'results/MULTIPLICITY_2F.csv');assert len(multi)==4 and (multi.family_size==4).all()
  p=multi['p'].dropna().to_numpy();o=np.argsort(p);adj=np.empty_like(p);adj[o]=np.minimum(1,np.maximum.accumulate((4-np.arange(len(p)))*p[o]))
  close(multi.loc[multi.p.notna(),'holm'],adj,'Holm four')
  assert bs['calls']==len(rec)
 pd.DataFrame(rec).to_csv(out/'verified_calls.csv',index=False)
 result=dict(status='PASS' if terminal else 'IN_PROGRESS_VERIFIED_SNAPSHOT',calls=len(rec),free_parameters=sum(x['free_parameters'] for x in rec),printed_rows=sum(x['printed_rows'] for x in rec),matrices=sum(x['matrices'] for x in rec),full_start_slots_verified=sum(x['start_slots'] for x in starts),complete_families_recomputed=nf,baseline=baseline,microdata_read=False,engine_wall_seconds=bs['engine_seconds'])
 (out/'independent_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--terminal',action='store_true');a=p.parse_args();verify(a.root,a.output,a.terminal)
