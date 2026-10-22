"""按类读TECH1，线性变换全部128参数及TECH3，复算条件高斯似然。"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import json,re
import numpy as np
import pandas as pd
from scipy.linalg import cho_factor,cho_solve
R=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def parse_matrix(block):
 ls=block.splitlines();out=[];i=0
 mats={'NU','LAMBDA','THETA','ALPHA','BETA','PSI','GAMMA','TAU','KAPPA'}
 while i<len(ls)-2:
  mat=ls[i].strip()
  if mat not in mats or not re.fullmatch(r'[_ ]+',ls[i+2]) or not ls[i+2].strip():i+=1;continue
  cols=ls[i+1].split();i+=3
  while i<len(ls) and ls[i].strip() and ls[i].strip() not in mats:
   t=ls[i].split()
   if mat in {'NU','ALPHA','TAU','KAPPA'} and re.match(r'^[-+\d]',t[0]):row='1';vals=t
   else:row=t[0];vals=t[1:]
   for col,v in zip(cols,vals):out.append((mat,row,col,int(v)))
   i+=1
 return out
def matrices(d):
 txt=(d/'model.out').read_text(encoding='latin1');spec=txt.split('TECHNICAL 1 OUTPUT',1)[1].split('STARTING VALUES',1)[0]
 blocks=re.split(r'PARAMETER SPECIFICATION FOR LATENT CLASS (\d+) \([^)]*\)',spec)
 if len(blocks)>1:
  mp={int(blocks[i]):parse_matrix(blocks[i+1].split('PARAMETER SPECIFICATION FOR LATENT CLASS REGRESSION',1)[0]) for i in range(1,len(blocks),2)}
 else:mp={1:parse_matrix(spec)}
 P=max(x[3] for b in mp.values() for x in b);a=np.fromstring((d/'estimates.dat').read_text(),sep=' ')
 v0=np.fromstring((d/'tech3.dat').read_text(),sep=' ');assert len(v0)==P*(P+1)//2
 V=np.zeros((P,P));V[np.tril_indices(P)]=v0;V=V+V.T-np.diag(V.diagonal())
 assert int(a[2*P])==P and np.allclose(V.diagonal(),a[P:2*P]**2,rtol=1e-6,atol=1e-8)
 assert {x[3] for b in mp.values() for x in b if x[3]}==set(range(1,P+1))
 return txt,mp,a[:P],a[P:2*P],V,a[2*P+1]
def pid(mp,mat,r,c):
 hits={n for m,a,b,n in mp if m==mat and a==r and b==c}
 if not hits and mat in ('BETA','GAMMA'):hits={n for m,a,b,n in mp if m in ('BETA','GAMMA') and a==r and b==c}
 if not hits and mat in ('PSI','THETA'):hits={n for m,a,b,n in mp if m==mat and a==c and b==r}
 assert len(hits)==1,(mat,r,c,hits)
 n=next(iter(hits));assert n>0,(mat,r,c,n);return n-1
def gaussian_ll(q,refpar,data):
 fac=['IX','SX','IY','SY'];obs=[f'{p}{i}' for p in ['X','Y'] for i in range(1,6)]
 L=np.zeros((10,4));L[:5,0]=1;L[5:,2]=1;L[:5,1]=[0,.4,.6,.8,1];L[5:,3]=[0,.4,.6,.8,1]
 TH=np.zeros((10,10));P=np.zeros((4,4));B=np.zeros((4,4));G=np.zeros((4,24));a=np.zeros(4)
 for row,value in zip(refpar.itertuples(),q):
  mat=row.matrix.upper();r=row.row;c=row.column
  if mat=='LAMBDA':L[obs.index(r),fac.index(c)]=value
  elif mat=='THETA':i=obs.index(r);j=obs.index(c);TH[i,j]=TH[j,i]=value
  elif mat=='PSI':i=fac.index(r);j=fac.index(c);P[i,j]=P[j,i]=value
  elif mat=='ALPHA':a[fac.index(c)]=value
  elif mat in ('BETA','GAMMA'):
   if c in fac:B[fac.index(r),fac.index(c)]=value
   else:G[fac.index(r),int(c[1:])-1]=value
  else:raise ValueError(mat)
 A=np.linalg.inv(np.eye(4)-B);S=L@A@P@A.T@L.T+TH
 mu=(a[None,:]+data[:,11:35]@G.T)@A.T@L.T;y=data[:,1:11];mask=np.isfinite(y);ll=0.
 for pattern in np.unique(mask,axis=0):
  ids=np.all(mask==pattern,axis=1);j=np.flatnonzero(pattern)
  if not len(j):continue
  cov=S[np.ix_(j,j)];chol=cho_factor(cov,lower=True);e=y[ids][:,j]-mu[ids][:,j]
  ll-=.5*(len(e)*(len(j)*np.log(2*np.pi)+2*np.log(np.diag(chol[0])).sum())+np.sum(e*cho_solve(chol,e.T).T))
 return ll
def main():
 d=R/'models/CFPS_EDU_KNOWN_H0_MI01_A';src=R/'references/SW_MI01'
 txt,mp,q,se,V,ll=matrices(d);_,oldmp,oq,ose,OV,oll=matrices(src)
 assert len(q)==len(oq)==128 and len(mp)==2
 ref=pd.read_csv(src/'parameters_high_precision.csv').sort_values('parameter');J=np.zeros((128,128))
 for k,row in enumerate(ref.itertuples()):
  mat=row.matrix.upper();r=row.row;c=row.column
  if mat in ('BETA','GAMMA') and c=='C2':
   J[k,pid(mp[2],'ALPHA','1',r)]=1;J[k,pid(mp[1],'ALPHA','1',r)]=-1
  else:
   j=pid(mp[1],mat,r,c);J[k,j]=1
   if mat!='ALPHA':assert j==pid(mp[2],mat,r,c),(mat,r,c)
 assert np.linalg.matrix_rank(J)==128
 cq=J@q;CV=J@V@J.T;cse=np.sqrt(CV.diagonal())
 diff=np.abs(cq-oq);reld=np.abs(cse-ose)/ose;lim=np.maximum(.001,.05*ose)
 data=np.genfromtxt(d/'data.dat',missing_values='.',filling_values=np.nan);assert data.shape==(3274,36)
 oldll=gaussian_ll(oq,ref,data);newll=gaussian_ll(cq,ref,data)
 constant=ll-newll
 households=pd.DataFrame({'fid':data[:,0],'g':data[:,12]}).groupby('fid').g.nunique()
 covariance_scaled=float(np.max(np.abs(CV-OV)/np.outer(ose,ose)))
 checks=dict(normal='THE MODEL ESTIMATION TERMINATED NORMALLY' in txt,
  all_parameters=bool(np.all(diff<=lim)),all_SE=bool(np.all(reld<=.05)),full_vcov=covariance_scaled<.05,
  reference_likelihood=abs(oldll-oll)<.02,conditional_likelihood=abs(newll-oldll)<.02,
  fixed_class_constant=abs(constant+len(data)*np.log(2))<.02,
  robust_cross_group_clusters=int((households>1).sum())>0,
  no_autofix='FIXED TO AVOID SINGULARITY' not in txt,
  positive_vcov=bool(np.linalg.eigvalsh(V/np.outer(se,se)).min()>1e-10))
 tab=ref.copy();tab['knownclass_transformed_estimate']=cq;tab['knownclass_transformed_se']=cse;tab['difference_over_reference_SE']=diff/ose
 tab.to_csv(R/'results/H0_ALL_PARAMETER_COMPARISON.csv',index=False)
 pd.DataFrame(J).to_csv(R/'results/H0_PARAMETER_TRANSFORMATION.csv',index=False,header=False)
 checks={k:bool(v) for k,v in checks.items()}
 res=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,free_parameters=128,
  max_parameter_difference_over_SE=float(np.max(diff/ose)),max_SE_relative_difference=float(reld.max()),
  max_vcov_difference_over_SE_product=covariance_scaled,reference_LL=oll,reference_analytic_LL=oldll,
  knownclass_printed_saved_LL=ll,knownclass_conditional_analytic_LL=newll,class_constant=constant,
  expected_constant=-len(data)*np.log(2),mixed_resource_households=int((households>1).sum()),
  engine_seconds=read(d/'engine_receipt.json')['seconds'],scope='H0 equivalence only; not interaction calibration or H4 inference')
 (R/'audit/H0_EQUIVALENCE.json').write_text(json.dumps(res,indent=2),encoding='utf-8');print(json.dumps(res))
if __name__=='__main__':main()
