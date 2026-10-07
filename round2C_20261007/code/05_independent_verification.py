"""独立复算已保存参数的几何与Rubin汇总；不运行R或Mplus。"""
from pathlib import Path
import csv,json,hashlib,sys
import numpy as np
from scipy.stats import t
ROOT=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007')
F=['IX','SX','IY','SY']; V=[f'{v}{i}' for v in ['X','Y'] for i in range(1,6)]
KEY=[('IY','IX'),('SY','IX'),('SY','SX'),('SY','IY')]
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def matrix(p):
    with p.open(encoding='utf-8-sig',newline='') as f:a=list(csv.reader(f))
    return np.array([[float(v) for v in r[1:]] for r in a[1:]])
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_model(d):
    r=json.loads((d/'receipt_round2C.json').read_text());spec=r['spec'];tau=r.get('tau')
    assert digest(d/'model.inp')==r['input_sha256']
    assert digest(d/'model.out')==r['output_sha256']
    assert int(rows(d/'fit.csv')[0]['Observations'])==3274
    p=rows(d/'parameters_high_precision.csv')
    assert [int(x['parameter']) for x in p]==list(range(1,len(p)+1))
    raw=d/'estimates.dat'
    if not raw.exists():raw=d/'estimates.dat.txt'
    values=np.array([float(s.replace('D','E')) for s in raw.read_text().split()]);n=len(p)
    assert len(values)>=2*n+1 and values[2*n]==n
    assert np.allclose(values[:n],[float(x['estimate']) for x in p],rtol=1e-12,atol=1e-14)
    assert np.allclose(values[n:2*n],[float(x['se']) for x in p],rtol=1e-12,atol=1e-14)
    binding=json.loads((d/'parameter_binding.json').read_text())
    assert digest(raw)==binding['results_sha256']
    with (d/'parameter_covariance.csv').open(encoding='utf-8-sig',newline='') as stream:cov_rows=list(csv.reader(stream))
    assert cov_rows[0][1:]==[str(i) for i in range(1,len(p)+1)]
    assert [x[0] for x in cov_rows[1:]]==[str(i) for i in range(1,len(p)+1)]
    def get(m,a,b):
        z=[x for x in p if x['matrix']==m and (x['row'],x['column'])==(a,b)]
        if not z and m in ('psi','theta'):z=[x for x in p if x['matrix']==m and (x['column'],x['row'])==(a,b)]
        assert len(z)==1,(d,m,a,b)
        return float(z[0]['estimate'])
    B=np.zeros((4,4));P=B.copy();L=np.zeros((10,4));T=np.zeros((10,10))
    for a,b in KEY:B[F.index(a),F.index(b)]=get('beta',a,b)
    for i,a in enumerate(F):P[i,i]=tau if a=='SY' and tau is not None else get('psi',a,a)
    for a,b in [('IX','SX'),('SX','IY')]:P[F.index(a),F.index(b)]=P[F.index(b),F.index(a)]=get('psi',a,b)
    L[:5,0]=1;L[5:,2]=1;L[:5,1]=[0,.4,.6,.8,1];L[5:,3]=[0,.4,.6,.8,1]
    if spec!='XLIN':
        for i in range(1,4):L[i,1]=get('lambda',V[i],'SX')
    for i,v in enumerate(V):T[i,i]=get('theta',v,v)
    if spec=='SW':
        for i in range(5):T[i,i+5]=T[i+5,i]=get('theta',V[i],V[i+5])
    A=np.linalg.inv(np.eye(4)-B);G=A@P@A.T;S=L@G@L.T+T
    idx=[0,2];sl=[1,3]
    H=G[np.ix_(sl,sl)]-G[np.ix_(sl,idx)]@np.linalg.solve(G[np.ix_(idx,idx)],G[np.ix_(idx,sl)])
    diffs={k:float(np.max(np.abs(m-matrix(d/f'matrix_{k}.csv')))) for k,m in [('B',B),('PSI',P),('LAMBDA',L),('THETA',T),('G',G),('SIGMA',S),('partial',H)]}
    assert max(diffs.values())<1e-9,(d,diffs)
    checks=[]
    for name,m,rank in [('PSI',P,3 if tau==0 else 4),('G',G,3 if tau==0 else 4),('THETA',T,10),('SIGMA',S,10)]:
        sd=np.sqrt(np.abs(np.diag(m)));sd[sd<1e-10]=1
        e=np.linalg.eigvalsh(m/np.outer(sd,sd))
        checks.append(e.min()>=-1e-7 and sum(e>1e-7)==rank)
    negative=any(float(x['estimate'])<0 for x in p if x['matrix'] in ('psi','theta') and x['row']==x['column'])
    geom=not negative and all(checks)
    assert geom==r['geometry_passed'],d
    u=matrix(d/'parameter_covariance.csv');se=np.array([float(x['se']) for x in p])
    err=float(max(abs(np.diag(u)-se**2)))
    if r['usable']:assert err<max(1e-5,max(se**2)*1e-4)
    return {'id':r['id'],'attempt':r['attempt'],'geometry_agrees':True,'geometry_passed':geom,'max_matrix_difference':max(diffs.values()),'vcov_diagonal_difference':err,'output_sha256':r['output_sha256']}
def verify_pool():
    gates=rows(ROOT/'audit/family_gates.csv');target=ROOT/'results/conditional_MI_paths.csv'
    eligible=[g['spec'] for g in gates if g['eligible_for_conditional_pooling']=='TRUE']
    if not eligible:return []
    saved=rows(target);out=[];receipts=json.loads((ROOT/'audit/current_receipts.json').read_text())
    for spec in eligible:
        Q=[];U=[]
        for i in range(1,11):
            r=receipts[f'{spec}_MI{i:02}'];assert r['usable']
            d=ROOT/'models'/r['id']/r['attempt'];p=rows(d/'parameters_high_precision.csv');idx=[]
            for a,b in KEY:
                z=[j for j,x in enumerate(p) if x['matrix']=='beta' and (x['row'],x['column'])==(a,b)];assert len(z)==1;idx+=z
            Q.append([float(p[j]['estimate']) for j in idx]);U.append(matrix(d/'parameter_covariance.csv')[np.ix_(idx,idx)])
        Q=np.array(Q);W=np.mean(U,axis=0);B=np.cov(Q,rowvar=False,ddof=1);T=W+1.1*B
        q=Q.mean(axis=0);se=np.sqrt(np.diag(T));r=1.1*np.diag(B)/np.diag(W)
        df=np.full(4,np.inf);np.divide(1,r,out=df,where=r>0);df=9*(1+df)**2
        lo=q-t.ppf(.975,df)*se;hi=q+t.ppf(.975,df)*se;pv=2*t.sf(abs(q/se),df)
        calc={'estimate':q,'se':se,'df':df,'lower':lo,'upper':hi,'p':pv,
              'relative_increase':r,'lambda':1.1*np.diag(B)/np.diag(T),
              'FMI':(r+2/(df+3))/(r+1),'MCSE_mean':np.sqrt(np.diag(B)/10),
              'MCSE_over_SE':np.sqrt(np.diag(B)/10)/se}
        z=[x for x in saved if x['spec']==spec];assert len(z)==4
        for k,v in calc.items():assert np.allclose(v,[float(x[k]) for x in z],rtol=1e-8,atol=1e-10),(spec,k)
        for k,m in [('within',W),('between',B),('total',T)]:assert np.allclose(m,matrix(ROOT/'results'/f'{spec}_{k}_covariance.csv'),rtol=1e-9,atol=1e-12)
        out.append({'spec':spec,'members':10,'four_paths_and_covariances':'PASS'})
    return out
def verify_starts():
    out=[]
    for r in rows(ROOT/'audit/start_checks.csv'):
        if r['executed']!='TRUE':
            out.append({'spec':r['spec'],'executed':False});continue
        base=ROOT/'models'/f'{r["spec"]}_MI01'
        original=json.loads((ROOT/'audit/current_receipts.json').read_text())[f'{r["spec"]}_MI01']['attempt']
        a=base/original;b=base/'start_check01'
        if not all((d/name).exists() for d in [a,b] for name in ['fit.csv','parameters_high_precision.csv']):
            assert r['stable']=='FALSE'
            out.append({'spec':r['spec'],'executed':True,'recalculation':'UNAVAILABLE_FAILED_START_CHECK','stable':False});continue
        dl=abs(float(rows(a/'fit.csv')[0]['LL'])-float(rows(b/'fit.csv')[0]['LL']))
        def keys(d):
            p=rows(d/'parameters_high_precision.csv')
            return np.array([float(next(x for x in p if x['matrix']=='beta' and (x['row'],x['column'])==key)['estimate']) for key in KEY])
        dp=float(max(abs(keys(a)-keys(b))))
        assert abs(dl-float(r['dLL']))<1e-8 and abs(dp-float(r['max_path_difference']))<1e-10
        out.append({'spec':r['spec'],'executed':True,'dLL':dl,'max_path_difference':dp,'recalculation':'PASS'})
    return out
if __name__=='__main__':
    partial='--partial' in sys.argv
    if not partial:assert (ROOT/'results/SUMMARY_CONTRACT.json').exists()
    checked=[];skipped=[]
    for f in sorted((ROOT/'models').glob('*/*/receipt_round2C.json')):
        if (f.parent/'matrix_G.csv').exists():checked.append(verify_model(f.parent))
        else:skipped.append({'path':str(f.relative_to(ROOT)),'reason':'No complete geometry saved; retained as failed or unparsed run'})
    out={'status':'PARTIAL_READBACK_PASS' if partial else 'PASS','models_checked':len(checked),'models':checked,'unverified_geometry':skipped,'pooling':[] if partial else verify_pool(),'starts':[] if partial else verify_starts(),'method':'Python independently rebuilds matrices and Rubin summaries from R-exported high precision parameters; no independent CFPS estimation'}
    dest=ROOT/'evidence'/('independent_verification_partial.json' if partial else 'independent_verification.json')
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('models',)},ensure_ascii=False))
