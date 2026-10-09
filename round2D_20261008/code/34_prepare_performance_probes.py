"""准备六份短迭代性能探针；仅在private中新建文件，不提交Mplus。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil

ROOT=Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008')
SOURCE=ROOT/'models/SONGAP/D1_Z0_MI01/repair_start'
DEST=ROOT/'private/performance_calibration_20261009'
OUT=ROOT/'audit/performance_review_20261009'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(text):
    # 仅允许三个预先登记的计算诊断选项不同；模型／数据语句逐字保持。
    text=re.sub(r'PROCESSORS\s*=\s*\d+\s*;', 'PROCESSORS=<BENCHMARK>;',text,flags=re.I)
    text=re.sub(r'MITERATIONS\s*=\s*\d+\s*;', 'MITERATIONS=<BENCHMARK>;',text,flags=re.I)
    text=re.sub(r'\s*STARTS\s*=\s*0\s*;', '',text,flags=re.I)
    return text

def main():
    raw=(SOURCE/'model.inp').read_bytes()
    text=raw.decode('utf-8')
    assert not re.search(r'(?<!M)STARTS\s*=',text,re.I)
    records=[]
    for number,processors in enumerate([1,4,2,2,4,1],1):
        candidate,n=re.subn(r'PROCESSORS\s*=\s*1\s*;',f'PROCESSORS={processors};',text,flags=re.I)
        assert n==1
        candidate,n=re.subn(r'MITERATIONS\s*=\s*4000\s*;','MITERATIONS=1; STARTS=0;',candidate,flags=re.I)
        assert n==1
        assert canonical(candidate)==canonical(text)
        folder=DEST/f'probe_{number:02d}_cpu{processors}'
        folder.mkdir(exist_ok=True,parents=True)
        inp=folder/'model.inp'
        data=folder/'data.dat'
        if inp.exists():
            assert inp.read_bytes()==candidate.encode('utf-8')
        else:
            inp.write_bytes(candidate.encode('utf-8'))
        if not data.exists():
            shutil.copy2(SOURCE/'data.dat',data)
        assert sha(data)==sha(SOURCE/'data.dat')
        assert not (folder/'model.out').exists(),'Probe already has output; do not relabel as unsubmitted'
        records.append(dict(probe=number,processors=processors,path=folder.relative_to(ROOT).as_posix(),
            input_sha256=sha(inp),data_sha256=sha(data),status='PREPARED_NOT_SUBMITTED',
            allowed_input_differences=['PROCESSORS','MITERATIONS=1','STARTS=0'],
            scientific_model_unchanged=True,full_estimation=False))
    binding=json.loads((ROOT/'runtime/postqueue_launch_contract.json').read_text(encoding='utf-8-sig'))
    unchanged=all(sha(ROOT/r['path'])==r['sha256'] for r in binding['sources'])
    assert unchanged and (SOURCE/'model.inp').read_bytes()==raw
    result=dict(status='PREPARED_NOT_SUBMITTED',created_at=datetime.now(timezone.utc).isoformat(),
        purpose='Timing diagnostic only; no parameters, SEs, p values, or MI pooled results to be reported',
        source=SOURCE.relative_to(ROOT).as_posix(),source_input_sha256=sha(SOURCE/'model.inp'),
        source_data_sha256=sha(SOURCE/'data.dat'),cases=json.loads((SOURCE/'input_contract.json').read_text(encoding='utf-8-sig'))['N'],
        controls_seeds_and_integration_preserved=True,sequence=records,
        maximum_seconds_per_probe=120,maximum_probe_engine_seconds=720,
        start_gate='Original model at an identity-verified idle boundary; no overlapping Mplus; record a separate computational variant and all calls before launch',
        adoption_gate='Timing probes alone cannot authorize changed production settings; complete equivalent valid-model comparison is required',
        bound_source_files_unchanged=unchanged,new_mplus_calls=0,
        private_data_publication=False)
    p=OUT/'calibration_preparation.json'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],prepared=len(records),new_mplus_calls=0,
        source_unchanged=unchanged,receipt=str(p)),ensure_ascii=False))

if __name__=='__main__':
    main()
