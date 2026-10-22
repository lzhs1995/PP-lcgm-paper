"""独立复核有限社区数敏感性；不调用R合并函数、不重新估计模型。"""
import os
for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']: os.environ[n]='1'
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from scipy.stats import t
R=Path(__file__).resolve().parent
FIELDS=['estimate','se','df','lower','upper','p','lambda','MCSE_over_SE']
def keys(p):
    return [':'.join([x.matrix.lower()]+(sorted([x.row.upper(),x.column.upper()]) if x.matrix.lower() in ('psi','theta') else [x.row.upper(),x.column.upper()])) for x in p.itertuples()]
def pool(Q,U,nu):
    m=len(Q); W=np.mean(U,axis=0); B=np.atleast_2d(np.cov(Q,rowvar=False,ddof=1)); T=W+(1+1/m)*B
    q=Q.mean(axis=0); se=np.sqrt(T.diagonal()); lam=(1+1/m)*B.diagonal()/T.diagonal()
    ratio=(1+1/m)*B.diagonal()/W.diagonal(); old=np.where(ratio>0,(m-1)*(1+1/ratio)**2,np.inf)
    obs=(nu+1)/(nu+3)*nu*(1-lam); df=1/(1/old+1/obs); crit=t.ppf(.975,df)
    return np.column_stack([q,se,df,q-crit*se,q+crit*se,2*t.sf(abs(q/se),df),lam,np.sqrt(B.diagonal()/m)/se])
verified=[]
for z,communities in [('gender',432),('oldest',433),('son',433)]:
    src=R.parent/f'charls_latent_h42_{z}_edu_full_20261022';dst=R/z
    c=json.loads((src/'contracts/RUN_CONTRACT.json').read_text()); rec=json.loads((dst/'CORRECTION.json').read_text())
    assert rec['communities']==c['communities']==communities and rec['corrected_dfcom']==communities-1
    Q=[];U=[]
    for ident in c['primary_sequence']:
        d=src/'models'/ident;p=pd.read_csv(d/'parameters_high_precision.csv');ks=keys(p)
        if not Q: orderkeys=ks
        ix=[ks.index(k) for k in orderkeys];Q.append(p.estimate.to_numpy()[ix]);U.append(np.loadtxt(d/'parameter_covariance.csv',delimiter=',')[np.ix_(ix,ix)])
    Q=np.array(Q);U=np.array(U);expected=pool(Q,U,communities-1)
    got=pd.read_csv(dst/'POOLED_CLUSTER_DF_CORRECTED.csv');assert list(got.key)==orderkeys
    np.testing.assert_allclose(got[FIELDS].to_numpy(),expected,rtol=1e-7,atol=1e-9)
    tab=pd.read_csv(dst/'CONTRASTS_CLUSTER_DF_CORRECTED.csv');assert len(tab)==21
    for row in tab.to_dict('records'):
        a=np.zeros(134)
        if row['contrast']!='difference':a[orderkeys.index('beta:'+row['path'])]=1
        if row['contrast']!='group0':a[orderkeys.index('beta:'+row['path']+'G')]=1
        expected=pool((Q@a)[:,None],np.array([[[a@v@a]] for v in U]),communities-1)[0]
        np.testing.assert_allclose([row[n] for n in FIELDS],expected,rtol=1e-7,atol=1e-9)
    assert hashlib.sha256((src/'results/PRIMARY_H42.csv').read_bytes()).hexdigest()==rec['original_primary_sha256']
    verified.append({'indicator':z,'communities':communities,'dfcom':communities-1,'parameters':134,'contrasts':21,'primary_unchanged':True})
out={'status':'PASS_INDEPENDENT_FINITE_CLUSTER_CORRECTION','families':verified,'Mplus_calls':0,'MI_calls':0,'full_H4_complete':False}
(R/'VERIFICATION.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
