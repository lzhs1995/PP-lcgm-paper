"""从原始TECH1/RESULTS/TECH3复算本批；不拟合Mplus、不读取微观数据。"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import csv
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from raw_mplus import RawModel, canonical_measurement, matrix_check, printed_rows, rubin, close, sha
from verify_starts import verify_starts

FACTORS=['IX','SX','IY','SY']
OBS=[f'{p}{i}' for p in ['X','Y'] for i in range(1,6)]

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def aslist(x):
    return x if isinstance(x,list) else [x]

def selected(root, obj):
    return root/'models'/obj['id']

def verify_model(d):
    r,job=read(d/'receipt.json'),read(d/'input_contract.json')
    assert sha(d/'model.inp')==job['input_sha256']
    text=(d/'model.out').read_text(encoding='latin1') if (d/'model.out').exists() else ''
    assert bool('THE MODEL ESTIMATION TERMINATED NORMALLY' in text)==r['normal']
    if text: assert sha(d/'model.out')==r['output_sha256']
    engine=read(d/'engine_receipt.json');close([r['seconds']],[engine['seconds']],'engine seconds')
    rec=dict(id=r['id'],status=r['status'],free_parameters=0,printed_rows=0,matrices=0,passed=True)
    if not (d/'parameters_high_precision.csv').exists():
        assert r['status']!='USABLE';return rec,None
    raw=RawModel(d);hp=pd.read_csv(d/'parameters_high_precision.csv')
    assert hp[['parameter','matrix','row','column']].equals(raw.parameters[['parameter','matrix','row','column']])
    close(hp[['estimate','se']],raw.parameters[['estimate','se']],'raw parameters')
    close(pd.read_csv(d/'parameter_covariance.csv',header=None),raw.v,'TECH3 export')
    close(raw.se**2,np.diag(raw.v),'SE squared',atol=1e-6,rtol=1e-5)
    assert raw.p==job['expected_free']
    # R回执使用OUT三位打印LL；独立高精度LL应落在其舍入区间。
    close([r['LL']],[raw.extra['H0 Loglikelihood']],'LL',atol=.00051,rtol=0)
    keys=pd.read_csv(d/'key_paths.csv')
    pr=printed_rows(raw.lines)
    for _,k in keys.iterrows():
        pid=raw.lookup('BETA',k['row'],k['column'],number=True)
        assert pid==int(k['parameter']) and pid>0
        close([k['estimate'],k['se']],[raw.q[pid-1],raw.se[pid-1]],'key parameter')
        pt=pr[(pr.paramHeader==k['row']+'.ON')&(pr.param==k['column'])]
        assert len(pt)==1
        close([float(pt.iloc[0].est),float(pt.iloc[0].se)],[k['estimate'],k['se']],'printed key',atol=.00051,rtol=0)
    # 自由参数与打印结果逐项对应，允许同一参数出现在多个输出表述中。
    for _,p in hp.iterrows():
        row,col=p['row'],p['column'];mat=p['matrix']
        if mat in ('beta','gamma'): h,field=row+'.ON',col
        elif mat=='lambda': h,field=col+'.BY',row
        elif mat in ('theta','psi') and row==col:
            candidates=pr[(pr.param==row)&pr.paramHeader.isin(['Variances','Residual.Variances'])]
            h,field=None,None
        elif mat in ('theta','psi'):
            candidates=pr[((pr.paramHeader==row+'.WITH')&(pr.param==col))|((pr.paramHeader==col+'.WITH')&(pr.param==row))]
            h,field=None,None
        elif mat in ('alpha','nu'):
            candidates=pr[(pr.param==col)&pr.paramHeader.isin(['Means','Intercepts'])];h,field=None,None
        else: continue
        if h: candidates=pr[(pr.paramHeader==h)&(pr.param==field)]
        if candidates.empty and mat=='lambda':
            candidates=pr[(pr.paramHeader==col+'.|')&(pr.param==row)]
        # 提升的基期指标载荷在BETA中，在MODEL RESULTS仍按BY打印。
        if candidates.empty and mat=='beta' and row in OBS and col in FACTORS:
            candidates=pr[pr.paramHeader.isin([col+'.BY',col+'.|'])&(pr.param==row)]
        assert len(candidates)==1,(r['id'],mat,row,col,len(candidates))
        close(candidates[['est','se']].iloc[0],[p['estimate'],p['se']],'printed parameter',atol=.00051,rtol=0)
    psi=raw.block('PSI',FACTORS,FACTORS);beta=raw.block('BETA',FACTORS,FACTORS)
    th,lam,_=canonical_measurement(raw,FACTORS,OBS)
    er=3 if r['spec'].endswith('B') else 4
    checks={'PSI':matrix_check(psi,er),'THETA':matrix_check(th)}
    matrices={'PSI':psi,'THETA':th,'LAMBDA':lam,'B':beta}
    if r['spec'] in ('E0','E0B'):
        a=np.linalg.inv(np.eye(4)-beta);g=a@psi@a.T;s=lam@g@lam.T+th
        checks['G']=matrix_check(g,er);checks['SIGMA']=matrix_check(s);matrices.update(G=g,SIGMA=s)
    else:
        for z in aslist(job['support_points']):
            b=beta.copy();b[3,1]+=raw.lookup('BETA','SY','SXZ')*z
            a=np.linalg.inv(np.eye(4)-b);s=lam@a@psi@a.T@lam.T+th
            name=f'COND_Z{z:+.3f}_G0';checks[name]=matrix_check(s);matrices[name]=s
    gate=read(d/'gate.json')
    for name,c in checks.items():
        other=gate['geometry']['checks'][name]
        for field in ('rank','expected_rank','psd','rank_ok','positive_definite'): assert c[field]==other[field],(name,field)
        close([c['min_eigen']],[other['min_eigen']],name+' eigenvalue',atol=2e-8)
        close(matrices[name],gate['geometry']['matrices'][name],name+' matrix',atol=1e-8)
    geo_ok=all(c['psd'] for c in checks.values()) and checks['PSI']['rank_ok'] and checks['THETA']['positive_definite']
    geo_ok &= all(c['positive_definite'] for k,c in checks.items() if 'SIGMA' in k or k.startswith('COND_'))
    if 'G' in checks:geo_ok &= checks['G']['rank_ok']
    vc_eig=np.linalg.eigvalsh(raw.v/np.outer(np.sqrt(np.diag(raw.v)),np.sqrt(np.diag(raw.v))))
    vc_ok=np.all(np.isfinite(raw.se)) and np.all(raw.se>0) and vc_eig.min()>1e-10
    neg=hp[(hp.matrix.isin(['psi','theta']))&(hp.row==hp.column)&(hp.estimate<0)]
    flat=re.sub(r'\s+',' ',text)
    fatal=bool(re.search(r'SADDLE POINT|STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED|NON-POSITIVE DEFINITE FIRST-ORDER DERIVATIVE|NOT TRUSTWORTHY|DID NOT CONVERGE|NO CONVERGENCE',flat))
    theta_warning='RESIDUAL COVARIANCE MATRIX (THETA) IS NOT POSITIVE' in flat
    psi_warning='LATENT VARIABLE COVARIANCE MATRIX (PSI) IS NOT POSITIVE' in flat
    ok=bool(r['normal'] and not fatal and not theta_warning and (not psi_warning or er==3) and vc_ok and len(neg)==0 and geo_ok)
    assert ok==(r['status']=='USABLE'),(r['id'],'admissibility disagreement')
    rec.update(free_parameters=raw.p,printed_rows=len(pr),matrices=len(checks))
    return rec,raw

def verify(root, output, terminal=False):
    output.mkdir(parents=True,exist_ok=True);records=[];models={}
    for d in sorted((root/'models').iterdir()):
        if not (d/'receipt.json').exists():continue
        row,raw=verify_model(d);records.append(row);models[d.name]=raw
    S=read(root/'runtime/selection.json') if (root/'runtime/selection.json').exists() else None
    if terminal:assert S and S.get('terminal'), 'queue has not ended'
    family_count=0;start_records=[]
    if terminal:
        start_records=verify_starts(root,read(root/'upstream/START_SOURCES.json'))
        pd.DataFrame(start_records).to_csv(output/'verified_full_starts.csv',index=False)
        fam=pd.read_csv(root/'results/FAMILY_STATUS.csv');pool=pd.read_csv(root/'results/POOLED_KEY_PATHS.csv')
        for _,f in fam.iterrows():
            b=S['branches'][f.z];members=b[f.spec] or {}
            states=[members.get(str(i),{}).get('status','NOT_RUN') for i in range(1,11)]
            if f.spec=='E1' and b['status']=='PILOT_NOT_USABLE':states[0]=b['low']['status']
            assert ';'.join(states)==f.member_statuses
            assert states.count('USABLE')==f.n_usable
            for m in members.values():
                assert m['status']==read(root/'models'/m['id']/'receipt.json')['status']
        for _,f in fam[fam.status=='ADOPT'].iterrows():
            selecteds=S['branches'][f.z][f.spec];assert set(selecteds)==set(map(str,range(1,11)))
            Q=[];U=[];labels=None
            for i in range(1,11):
                m=selecteds[str(i)];assert m['status']=='USABLE' and m['sample']=='CFPS'
                raw=models[m['id']];k=pd.read_csv(selected(root,m)/'key_paths.csv');ids=k.parameter.to_numpy(int)-1
                Q.append(raw.q[ids]);U.append(raw.v[np.ix_(ids,ids)]);labels=k.label.tolist()
            table,W,B,T=rubin(Q,U)
            actual=pool[(pool.z==f.z)&(pool.spec==f.spec)].set_index('label').loc[labels]
            close(actual[table.columns],table,'Rubin ten members',atol=1e-8)
            rel=1.1*np.diag(B)/np.diag(W)
            fmi=(rel+2/(table['df'].to_numpy()+3))/(rel+1)
            close(actual['FMI'],fmi,'FMI',atol=1e-8)
            if f.spec=='E1':
                assert S['branches'][f.z]['numeric']['integration']['passed'] and S['branches'][f.z]['numeric']['start']['passed']
                slopes=pd.read_csv(root/'results/CONDITIONAL_SLOPES.csv')
                for _,row in slopes[slopes.z==f.z].iterrows():
                    a=np.zeros(len(labels));a[labels.index('bss')]=1;a[labels.index('dc')]=row.zvalue
                    ct,_,_,_=rubin(np.asarray(Q)@a,np.einsum('i,mij,j->m',a,np.asarray(U),a).reshape(10,1,1))
                    close(row[ct.columns].astype(float),ct.iloc[0],'conditional slope',atol=1e-8)
            family_count+=1
        mult=pd.read_csv(root/'results/MULTIPLICITY.csv')
        for label in ['dc','gi0','gs0']:
            sub=mult[mult.label==label];assert len(sub)==4 and (sub.family_size==4).all()
            good=sub['p'].notna();p=sub.loc[good,'p'].to_numpy();order=np.argsort(p)
            expected=np.empty_like(p);expected[order]=np.minimum(1,np.maximum.accumulate((4-np.arange(len(p)))*p[order]))
            close(sub.loc[good,'holm'],expected,'fixed-family Holm')
            assert sub.loc[~good,'holm'].isna().all()
        deferred=pd.read_csv(root/'results/DEFERRED.csv');assert len(deferred[deferred.task.str.startswith('H4')])==3
    for name,h in read(root/'contracts/FROZEN_CODE.json').items(): assert sha(root/'code'/name)==h,name
    b=read(root/'runtime/budget_status.json');assert b['calls']==len(records) if terminal else b['calls']>=len(records)
    close([b['engine_seconds']],[sum(read(root/'models'/r['id']/'engine_receipt.json')['seconds'] for r in b['rows'])],'budget reconciliation')
    assert b['calls']<=101 and b['engine_seconds']<=28805
    contract=read(root/'contracts/RUN_CONTRACT.json')
    for category,cap in contract['budget']['categories'].items():
        assert sum(x['category']==category for x in b['rows'])<=cap
    pd.DataFrame(records).to_csv(output/'verified_calls.csv',index=False)
    result={'status':'PASS' if terminal else 'IN_PROGRESS_VERIFIED_SNAPSHOT','calls':len(records),
      'free_parameters':sum(r['free_parameters'] for r in records),'printed_rows':sum(r['printed_rows'] for r in records),
      'matrices':sum(r['matrices'] for r in records),'complete_families_recomputed':family_count,'microdata_read':False}
    result['full_start_models_verified']=len(start_records)
    result['full_start_slots_verified']=sum(x['start_slots'] for x in start_records)
    result['fixed_family_holm_verified']=bool(terminal)
    (output/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--terminal',action='store_true')
    a=p.parse_args();verify(a.root,a.output,a.terminal)
