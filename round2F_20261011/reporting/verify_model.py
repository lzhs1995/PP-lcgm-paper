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
    # 读取Mplus实际摘要，不能只核对来自同一调用合同的重复元数据。
    def printed_int(label):
        m=re.search(r'^\s*'+re.escape(label)+r'\s+(\d+)\s*$',text,re.M)
        return int(m.group(1)) if m else None
    n=printed_int('Number of observations')
    if n is not None:assert n==job['N'],(r['id'],'actual N')
    clusters=printed_int('Number of clusters')
    if clusters is not None:assert clusters==job['households'],(r['id'],'actual clusters')
    inp=(d/'model.inp').read_text(encoding='utf-8-sig')
    assert re.search(r'PROCESSORS\s*=\s*1\s*;',inp,re.I)
    if r['normal'] and job['spec']!='E0':
        assert printed_int('Number of integration points')==job['points']
        assert printed_int('Dimensions of numerical integration')==1
        for label,want in [('Loglikelihood change',1e-5),('Relative loglikelihood change',1e-9)]:
            m=re.search(r'^\s*'+re.escape(label)+r'\s+([.\dDEe+-]+)\s*$',text,re.M)
            assert m and float(m.group(1).replace('D','E'))==want,(r['id'],label)
    close([engine['seconds']],[engine['finished_epoch']-engine['started_epoch']],'actual engine wall',atol=1e-6)
    assert engine['test_hook'] is None
    flat=re.sub(r'\s+',' ',text)
    no_se='STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE COMPUTED' in flat
    rec=dict(id=r['id'],status=r['status'],free_parameters=0,printed_rows=0,matrices=0,
             standard_errors_unavailable=no_se,passed=True)
    if not (d/'parameters_high_precision.csv').exists():
        assert r['status']!='USABLE'
        if r['status']=='EXTRACTION_FAILED':
            # 正常终止文字不能覆盖严重标准误警告；原始回执不改写。
            assert no_se and 'MODEL MAY NOT BE IDENTIFIED' in flat
            assert not (d/'estimates.dat').exists()
            assert (d/'tech3.dat').exists() and (d/'tech3.dat').stat().st_size==0
            rec['output_diagnosis']='STANDARD_ERRORS_UNAVAILABLE'
        return rec,None
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
    ok=bool(r.get('criteria_as_requested',True) and r['normal'] and not fatal and not theta_warning and (not psi_warning or er==3) and vc_ok and len(neg)==0 and geo_ok)
    assert ok==(r['status']=='USABLE'),(r['id'],'admissibility disagreement')
    rec.update(free_parameters=raw.p,printed_rows=len(pr),matrices=len(checks))
    return rec,raw
