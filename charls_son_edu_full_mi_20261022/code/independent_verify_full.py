"""独立重建当前 son×education 家族的 134 参数变换、MI 合并和 B 起点核对。"""
import os
for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']: os.environ[n]='1'
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
import pandas as pd
from scipy.stats import t
from calibrated_reader import matrices,pid
from models import FAC,OBS,TARGETS,read,sha
R=Path(__file__).resolve().parents[1]
FIELDS=['estimate','se','df','lower','upper','p','lambda','MCSE_over_SE']
def semkey(m,a,b):
    m=m.lower()
    if m in ('psi','theta'): a,b=sorted((a,b))
    return ':'.join((m,a,b))
def slot_meta(slots,mp,j):
    n=len(slots); J=np.zeros((n,n)); meta=[]
    for i,r in enumerate(slots):
        op,a,b=r['op'],r['lhs'],r['rhs']; row=a; col=b
        if op=='ON' and b=='C3':
            J[i,pid(mp[2],'ALPHA','1',a)]=1;J[i,pid(mp[1],'ALPHA','1',a)]=-1;mat='BETA'
        elif op=='DIFF':
            J[i,pid(mp[2],'BETA',a,b)]=1;J[i,pid(mp[1],'BETA',a,b)]=-1;mat='BETA';col=b+'G'
        else:
            if op=='MEAN':mat='ALPHA';row='1';col=a
            elif op=='BY':mat='LAMBDA';row=b;col=a
            elif op in ('VAR','WITH'):mat='PSI' if a in FAC else 'THETA';col=a if op=='VAR' else b
            elif op=='ON':mat='BETA'
            else: raise ValueError(op)
            k=pid(mp[1],mat,row,col);J[i,k]=1
            if op!='MEAN' and (not j.get('parent',False)) and op=='ON' and (a,b) in TARGETS:
                k1=pid(mp[2],mat,row,col); assert k1!=k
            elif op!='MEAN': assert k==pid(mp[2],mat,row,col)
        meta.append(dict(parameter=i+1,matrix=mat.lower(),row=row,column=col))
    assert np.linalg.matrix_rank(J)==n
    return J,pd.DataFrame(meta)
def verify_one(ident):
    c=read(R/'contracts/RUN_CONTRACT.json'); d=R/'models'/ident; j=read(d/'job.json'); e=read(d/'engine_receipt.json'); a=read(d/'receipt.json')
    assert a['status']=='USABLE' and e['exitcode']==0 and e['process_exited'] and e['actual_engine_calls']==1
    for n,h in j['hashes'].items(): assert sha(d/n)==h,(ident,n)
    assert sha(d/'model.out')==a['output_sha256']
    assert e['input_sha256']==j['hashes']['model.inp'] and e['data_sha256']==j['hashes']['data.dat']
    for n in ['stdout','stderr']: assert sha(d/'execution'/f'{n}.log')==e[n+'_sha256'],(ident,n)
    text,mp,q,se,V,ll=matrices(d); assert len(q)==134 and len(mp)==2
    p=pd.read_csv(d/'parameters_high_precision.csv'); assert len(p)==134
    assert 'THE MODEL ESTIMATION TERMINATED NORMALLY' in text and not re.search(r'[1-9]\d* ERROR\(S\) FOUND|\*\*\* ERROR|MAY NOT BE TRUSTWORTHY|SADDLE POINT|STANDARD ERRORS.{0,100}COULD NOT BE COMPUTED|FIXED TO AVOID SINGULARITY|NOT POSITIVE DEFINITE',text)
    slots=read(d/'normalized_slots.json');J,meta=slot_meta(slots,mp,j); nV=J@V@J.T; nq=J@q; nse=np.sqrt(nV.diagonal())
    assert np.array_equal(J,np.loadtxt(d/'parameter_transform.csv',delimiter=','))
    assert np.allclose(nq,p.estimate.to_numpy(),rtol=1e-10,atol=1e-11)
    assert np.allclose(nse,p.se.to_numpy(),rtol=1e-9,atol=1e-11)
    assert np.allclose(nV,np.loadtxt(d/'parameter_covariance.csv',delimiter=','),rtol=1e-9,atol=1e-11)
    assert np.isfinite(nq).all() and np.isfinite(nV).all() and (nse>0).all()
    assert np.linalg.eigvalsh(nV/np.outer(nse,nse)).min()>1e-10
    geometry={}
    for mat,names in [('psi',FAC),('theta',OBS)]:
        g=np.zeros((len(names),len(names)))
        for row,v in zip(p.itertuples(),nq):
            if row.matrix.lower()==mat:
                ii,jj=names.index(row.row),names.index(row.column);g[ii,jj]=g[jj,ii]=v
        diag=g.diagonal(); assert (diag>0).all(); geometry[mat.upper()]=float(np.linalg.eigvalsh(g/np.sqrt(np.outer(diag,diag))).min())
        assert geometry[mat.upper()]>1e-7 and abs(geometry[mat.upper()]-a['geometry'][mat.upper()])<1e-10
    obs=int(re.search(r'Number of observations\s+(\d+)',text).group(1)); assert obs==j['N']==2263
    assert abs(ll+j['N']*np.log(2)-a['LL'])<1e-7
    keys=[semkey(x.matrix,x.row,x.column) for x in p.itertuples()];assert len(set(keys))==134
    return dict(id=ident,q=nq,se=nse,V=nV,LL=a['LL'],keys=keys,geometry=geometry,active_seconds=e['active_seconds'])
def rubin(Q,U,dfcom=np.inf):
    m=Q.shape[0]; W=sum(U)/m; B=np.atleast_2d(np.cov(Q,rowvar=False,ddof=1)); T=W+(1+1/m)*B;est=Q.mean(0);se=np.sqrt(np.diag(T));r=(1+1/m)*np.diag(B)/np.diag(W);lam=(1+1/m)*np.diag(B)/np.diag(T);df_old=np.where(r>0,(m-1)*(1+1/r)**2,np.inf)
    if np.isfinite(dfcom): df_obs=(dfcom+1)/(dfcom+3)*dfcom*(1-lam); df=1/(1/df_old+1/df_obs)
    else: df=df_old
    crit=t.ppf(.975,df);out=np.column_stack([est,se,df,est-crit*se,est+crit*se,2*t.sf(np.abs(est/se),df),lam,np.sqrt(np.diag(B)/m)/se]);return out,W,B,T
def verify():
    c=read(R/'contracts/RUN_CONTRACT.json'); term=read(R/'results/TERMINAL.json'); assert term['status']=='COMPLETE_20_MI_WORKING_H42_SON_EDU' and term['attempted']==21
    ids=c['primary_sequence']; assert len(ids)==20 and len(c['sequence'])==21
    recs=[verify_one(i) for i in ids]; b=verify_one(c['sequence'][-1]); keys=recs[0]['keys'];Q=np.array([x['q'][np.array([x['keys'].index(k) for k in keys])] for x in recs]);U=[x['V'][np.ix_([x['keys'].index(k) for k in keys],[x['keys'].index(k) for k in keys])] for x in recs]
    pooled,W,B,T=rubin(Q,U); pooled437,_,_,_=rubin(Q,U,437)
    for fn,arr in [('POOLED_ALL',pooled),('POOLED_CLUSTER_DF',pooled437)]:
        saved=pd.read_csv(R/'results'/f'{fn}.csv');assert list(saved.key)==keys;assert np.allclose(saved[FIELDS].to_numpy(),arr,rtol=1e-7,atol=1e-9)
    for n,v in [('W',W),('B',B),('T',T)]: assert np.allclose(v,np.loadtxt(R/'results'/f'POOLED_{n}.csv',delimiter=','),rtol=1e-9,atol=1e-11)
    contrast=pd.read_csv(R/'results/POOLED_RESEARCH_CONTRASTS.csv').set_index(['path','contrast'])
    def scalar(a,dfcom=np.inf):
        q=Q@a;u=[np.array([[a@v@a]]) for v in U];arr,_,_,_=rubin(q[:,None],u,dfcom);return arr[0]
    for path in ['IY:IX','SY:IX','SY:SX','IY:IZ','SY:IZ','SY:SZ','SY:SXIZ']:
        base=keys.index('beta:'+path);diff=keys.index('beta:'+path+'G')
        for g in ['group0','group1','difference']:
            a=np.zeros(134); 
            if g!='difference':a[base]=1
            if g!='group0':a[diff]=1
            arr=scalar(a); row=contrast.loc[(path,g)]; assert np.allclose(arr,FIELDS and row[FIELDS].to_numpy(dtype=float),rtol=1e-7,atol=1e-9)
            arr437=scalar(a,437); assert np.allclose(arr437[[2,3,4,5]],row[['cluster_df','cluster_lower','cluster_upper','cluster_p']].to_numpy(dtype=float),rtol=1e-7,atol=1e-9)
    primary=pd.read_csv(R/'results/PRIMARY_H42.csv').iloc[0]; assert primary.path=='SY:SXIZ' and primary.contrast=='difference'; assert abs(primary.bonferroni_p_planned12-min(1,12*primary.p))<1e-10
    # MI01 A/B 起点敏感性：仅比较同一 MI01 数据的两套起点，不把它当作 MI 合并。
    aq=recs[0]['q']; bq=b['q'][np.array([b['keys'].index(k) for k in keys])]; ase=recs[0]['se']; bse=b['se'][np.array([b['keys'].index(k) for k in keys])]; av=recs[0]['V']; bv=b['V'][np.ix_([b['keys'].index(k) for k in keys],[b['keys'].index(k) for k in keys])]
    checks={'LL_absolute':abs(recs[0]['LL']-b['LL']),'parameter_difference_in_reference_SE':float(np.max(abs(aq-bq)/ase)),'SE_relative':float(np.max(abs(ase-bse)/ase)),'normalized_vcov_difference':float(np.max(abs(av-bv)/np.outer(ase,ase)))}
    limits=c['tolerances']; sens={'passed':all(checks[k]<=limits[k] for k in checks),'checks':checks,'tolerances':limits,'same_MI_member':True,'interpretation':'start sensitivity only; not an independent MI member'}
    (R/'results/MI01_B_STARTS_INDEPENDENT.json').write_text(json.dumps(sens,indent=2),encoding='utf-8')
    ledger=pd.DataFrame([dict(id=x['id'],active_seconds=x['active_seconds'],parameters=134) for x in recs+[b]]);ledger.to_csv(R/'results/INDEPENDENT_PARAMETER_LEDGER.csv',index=False)
    out={'status':'PASS_FULL_TRANSFORM_AND_RUBIN_SON_EDU','m':20,'models':21,'N':2263,'communities':433,'parameters_checked':2814,'contrasts':21,'primary':{'estimate':float(primary.estimate),'lower':float(primary.lower),'upper':float(primary.upper),'p':float(primary.p),'bonferroni_planned12':float(primary.bonferroni_p_planned12),'MCSE_over_SE':float(primary.MCSE_over_SE)},'raw_matrix_parser_reused':True,'linear_transformation_and_pooling_independently_recomputed':True,'total_engine_active_seconds':float(sum(x['active_seconds'] for x in recs+[b])),'conditional_working_MI':True,'exact_congeniality_proven':False,'original_CFPS_four_complete':False,'full_H4_complete':False,'B_start_sensitivity_passed':sens['passed']}
    (R/'results/INDEPENDENT_VERIFICATION.json').write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out),flush=True)
if __name__=='__main__': verify()
