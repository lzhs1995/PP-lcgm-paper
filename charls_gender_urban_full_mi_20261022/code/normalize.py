"""潜在交互已知组：原始矩阵读回和可逆全参数变换，不使用高斯边际似然。"""
import os
for name in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import json,re,sys
import numpy as np
import pandas as pd
from models import ROOT,SOURCE,FAC,OBS,TARGETS,read,sha,save
from calibrated_reader import matrices,pid

def semkey(m,a,b):
    m=m.lower()
    if m=='gamma':m='beta'
    if m in ['psi','theta']:a,b=sorted((a,b))
    return ':'.join((m,a,b))

def normalize(ident):
    d=ROOT/'models'/ident;j=read(d/'job.json');e=read(d/'engine_receipt.json')
    result=dict(id=ident,actual_engine_calls=e.get('actual_engine_calls',0),status='READBACK_PENDING')
    if e.get('state')!='EXITED' or e.get('exitcode')!=0 or not e.get('process_exited'):
        result['status']='ENGINE_'+e.get('state',e.get('status','UNKNOWN'));save(d/'receipt.json',result);return result
    try:
        for n,h in j['hashes'].items():assert sha(d/n)==h
        text,mp,q,se,V,ll=matrices(d);n=j['expected_free'];assert len(mp)==2 and len(q)==n
        assert np.isfinite(q).all() and np.isfinite(V).all() and (se>0).all()
        slots=read(d/'normalized_slots.json');assert len(slots)==n
        J=np.zeros((n,n));meta=[];labels={}
        for i,r in enumerate(slots):
            op=r['op'];a=r['lhs'];b=r['rhs'];row=a;col=b
            if op=='ON' and b=='C4':
                J[i,pid(mp[2],'ALPHA','1',a)]=1;J[i,pid(mp[1],'ALPHA','1',a)]=-1;mat='BETA'
            elif op=='DIFF':
                J[i,pid(mp[2],'BETA',a,b)]=1;J[i,pid(mp[1],'BETA',a,b)]=-1;mat='BETA';col=b+'G'
            else:
                if op=='MEAN':mat='ALPHA';row='1';col=a
                elif op=='BY':mat='LAMBDA';row=b;col=a
                elif op in ['VAR','WITH']:mat='PSI' if a in FAC else 'THETA';col=a if op=='VAR' else b
                elif op=='ON':mat='BETA'
                else:raise ValueError(op)
                k=pid(mp[1],mat,row,col);J[i,k]=1
                if op!='MEAN':
                    varied=not j['parent'] and op=='ON' and (a,b) in TARGETS
                    if varied:
                        k1=pid(mp[2],mat,row,col);assert k1!=k
                        labels[r['label']+'0']=float(q[k]);labels[r['label']+'1']=float(q[k1])
                    else:
                        assert k==pid(mp[2],mat,row,col);labels[r['label']]=float(q[k])
                else:
                    for group in [0,1]:labels[a.lower()+str(group)]=float(q[pid(mp[group+1],'ALPHA','1',a)])
            meta.append(dict(parameter=i+1,matrix=mat.lower(),row=row,column=col))
        assert np.linalg.matrix_rank(J)==n
        nq=J@q;NV=J@V@J.T;nse=np.sqrt(NV.diagonal())
        vcmin=float(np.linalg.eigvalsh(NV/np.outer(nse,nse)).min())
        # 创新协方差与测量残差分别核验；不把含乘积的边际分布当作高斯。
        geometry={};negative=[]
        for mat,names in [('PSI',FAC),('THETA',OBS)]:
            cov=np.zeros((len(names),len(names)))
            for r,v in zip(slots,nq):
                if r['op'] in ['VAR','WITH'] and r['lhs'] in names:
                    a=names.index(r['lhs']);b=a if r['op']=='VAR' else names.index(r['rhs']);cov[a,b]=cov[b,a]=v
                    if a==b and v<0:negative.append(mat+':'+r['lhs'])
            diag=cov.diagonal();assert (diag>0).all()
            geometry[mat]=float(np.linalg.eigvalsh(cov/np.sqrt(np.outer(diag,diag))).min())
        flat=' '.join(text.split())
        normal='THE MODEL ESTIMATION TERMINATED NORMALLY' in flat
        fatal=bool(re.search(r'[1-9]\d* ERROR\(S\) FOUND|\*\*\* ERROR|MAY NOT BE TRUSTWORTHY|SADDLE POINT|STANDARD ERRORS.{0,100}COULD NOT BE COMPUTED|FIXED TO AVOID SINGULARITY|NOT POSITIVE DEFINITE',flat))
        observations=int(re.search(r'Number of observations\s+(\d+)',text).group(1))
        data=np.loadtxt(d/'data.dat');assert data.shape==(j['N'],27)
        names=['CLUSTER']+[f'{v}{i}' for v in ['X','Y'] for i in range(1,6)]+[f'C{i}' for i in range(1,12)]+[f'Z{i}' for i in range(1,6)]
        group=data[:,names.index(j['g'])];assert set(group)=={0.,1.}
        grouped=pd.DataFrame(dict(cluster=data[:,0],group=group)).groupby('cluster').group.nunique()
        mixed=int((grouped>1).sum())  # 城乡可在社区内恒定，零是数据诊断而非估计失败。
        par=pd.DataFrame(meta);par['estimate']=nq;par['se']=nse
        par.to_csv(d/'parameters_high_precision.csv',index=False)
        np.savetxt(d/'parameter_covariance.csv',NV,delimiter=',');np.savetxt(d/'parameter_transform.csv',J,delimiter=',')
        save(d/'final_labeled_values.json',labels)
        usable=normal and not fatal and not negative and observations==j['N'] and vcmin>1e-10 and min(geometry.values())>1e-7
        result.update(status='USABLE' if usable else 'INADMISSIBLE',normal=normal,fatal=fatal,negative=negative,geometry=geometry,
            full_vcov_min=vcmin,N=observations,parameters=n,LL=float(ll+j['N']*np.log(2)),saved_class_LL=float(ll),
            class_constant_removed=float(j['N']*np.log(2)),mixed_group_communities=mixed,
            output_sha256=sha(d/'model.out'),gaussian_analytic_LL_used=False,original_CFPS_four_complete=False,full_H4_complete=False)
    except Exception as exc:
        import traceback
        result.update(status='READBACK_FAILED',error=repr(exc),traceback=traceback.format_exc())
    save(d/'receipt.json',result)
    print(json.dumps(result),flush=True)
    return result

def compare(a,b):
    a=Path(a);b=Path(b);ra=read(a/'receipt.json');rb=read(b/'receipt.json');assert ra['status']==rb['status']=='USABLE'
    pa=pd.read_csv(a/'parameters_high_precision.csv');pb=pd.read_csv(b/'parameters_high_precision.csv')
    keys=lambda p:[semkey(x.matrix,x.row,x.column) for x in p.itertuples()]
    ka=keys(pa);kb=keys(pb);assert len(set(ka))==len(ka) and len(set(kb))==len(kb) and set(ka)==set(kb)
    order=[kb.index(k) for k in ka];aq=pa.estimate.to_numpy();ase=pa.se.to_numpy();bq=pb.estimate.to_numpy()[order];bse=pb.se.to_numpy()[order]
    av=np.loadtxt(a/'parameter_covariance.csv',delimiter=',');bv=np.loadtxt(b/'parameter_covariance.csv',delimiter=',')[np.ix_(order,order)]
    checks=dict(LL_absolute=abs(ra['LL']-rb['LL']),parameter_difference_in_reference_SE=float(np.max(abs(aq-bq)/ase)),
        SE_relative=float(np.max(abs(ase-bse)/ase)),normalized_vcov_difference=float(np.max(abs(av-bv)/np.outer(ase,ase))))
    limits=read(ROOT/'contracts/RUN_CONTRACT.json')['tolerances']
    return dict(passed=all(checks[k]<=limits[k] for k in checks),checks=checks,tolerances=limits,parameters=len(ka))

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='normalize':normalize(sys.argv[2])
    elif len(sys.argv)==5 and sys.argv[1]=='compare':
        result=compare(sys.argv[2],sys.argv[3]);save(Path(sys.argv[4]),result);print(json.dumps(result),flush=True)
    else:raise SystemExit('Use normalize ID or compare DIR_A DIR_B OUTPUT_JSON')
