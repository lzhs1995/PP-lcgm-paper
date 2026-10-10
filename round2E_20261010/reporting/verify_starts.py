"""独立从原始参数及实际INP验证语义起点，不导入R实现。"""
import re
import numpy as np
import pandas as pd
from raw_mplus import RawModel,canonical_measurement,close,sha

FACTORS=['IX','SX','IY','SY']
OBS=[p+str(i) for p in ['X','Y'] for i in range(1,6)]
NUM=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?'


def semantic(raw,op,lhs,rhs):
    th,lam,_=canonical_measurement(raw,FACTORS,OBS)
    if op=='BY':return lam[OBS.index(rhs),FACTORS.index(lhs)]
    if op=='VAR' and lhs in OBS:return th[OBS.index(lhs),OBS.index(lhs)]
    if op=='WITH' and lhs in OBS and rhs in OBS:return th[OBS.index(lhs),OBS.index(rhs)]
    matrix='ALPHA' if op=='MEAN' else 'PSI' if op in ['VAR','WITH'] else 'BETA'
    row,col=('1',lhs) if op=='MEAN' else (lhs,lhs if op=='VAR' else rhs)
    number=raw.lookup(matrix,row,col,number=True)
    if not number and op=='ON':matrix='GAMMA';number=raw.lookup(matrix,row,col,number=True)
    return raw.lookup(matrix,row,col) if number else None


def verify_starts(root,index):
    records=[];cache={}
    for d in sorted((root/'models').iterdir()):
        if not (d/'receipt.json').exists():continue
        slots=pd.read_csv(d/'start_mapping.csv').fillna('')
        assert not slots.key.duplicated().any()
        text=(d/'model.inp').read_text(encoding='latin1').upper()
        assert 'ON SXZ' in text if '_E1' in d.name else 'XWITH' not in text
        source=None
        hs=set(slots.source_sha256)-{''}
        if hs:
            assert len(hs)==1
            h=next(iter(hs));entry=index[h];source_dir=root/entry['path']
            assert sha(source_dir/'model.out')==h
            assert sha(source_dir/'estimates.dat')==entry['estimates_sha256']
            assert sha(source_dir/'tech3.dat')==entry['tech3_sha256']
            if h not in cache:cache[h]=RawModel(source_dir)
            source=cache[h]
            assert 'THE MODEL ESTIMATION TERMINATED NORMALLY' in '\n'.join(source.lines)
            vv=source.parameters
            assert not ((vv.matrix.isin(['psi','theta']))&(vv.row==vv.column)&(vv.estimate<0)).any()
        perturb_index=0;mapped=0
        for _,s in slots.iterrows():
            op,lhs,rhs=s['op'],s['lhs'],s['rhs']
            value=float(s['value'])
            expected=float(s['init'])
            if str(s['action']).startswith('mapped_high_precision'):
                v=semantic(source,op,lhs,rhs);assert v is not None,(d.name,s['key'])
                close([s['source_value']],[v],'source semantic value',atol=1e-10)
                expected=v;mapped+=1
            else:assert s['source_value']==''
            if op in ['ON','MEAN','BY']:
                perturb_index+=1
                if 'deterministic_perturbation' in s['action']:expected+=(.02 if perturb_index%2 else -.02)
            close([value],[expected],'start transform',atol=1e-10)
            if op=='MEAN':pat=r'(?m)^\s*\[\s*'+lhs+r'\s*\*\s*('+NUM+r')\s*\]\s*;'
            elif op=='VAR':pat=r'(?m)^\s*'+lhs+r'\s*\*\s*('+NUM+r')\s*;'
            else:pat=r'(?m)^\s*'+lhs+r'\s+'+op+r'\s+'+rhs+r'\s*\*\s*('+NUM+r')\s*;'
            values=re.findall(pat,text)
            assert len(values)==1,(d.name,s['key'],values)
            close([float(values[0])],[value],'actual INP free start',atol=2e-10)
        records.append(dict(id=d.name,start_slots=len(slots),mapped_source_slots=mapped,passed=True))
    return records
