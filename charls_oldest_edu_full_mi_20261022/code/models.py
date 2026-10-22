"""编译隔离的 CHARLS oldest×education 20-MI 潜变量家族；不执行引擎。"""
from pathlib import Path
import csv,hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]; PILOT=ROOT.parent/'charls_latent_h42_oldest_edu_pilot_20261022'; MI=ROOT.parent/'charls_latent_h42_oldest_edu_mi_20261022'
SOURCE_A=PILOT/'models/H42_GH15_A'; SOURCE_B=PILOT/'models/H42_GH15_B'
SOURCE=SOURCE_A
FAC=['IX','SX','IY','SY','IZ','SZ']
OBS=[f'{p}{i}' for p in ['X','Y','Z'] for i in range(1,6)]
TARGETS=[('IY','IX'),('SY','IX'),('SY','SX'),('IY','IZ'),('SY','IZ'),('SY','SZ'),('SY','SXIZ')]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False)
def compile_model(ident):
    c=read(ROOT/'contracts/RUN_CONTRACT.json'); assert ident in c['sequence']
    assert read(MI/'audit/INDEPENDENT_MI.json')['status']=='PASS_INDEPENDENT_WORKING_MI'
    for n,h in c['source_hashes'].items(): assert sha(SOURCE_A/n)==h
    is_b=ident.endswith('_B'); member=int(ident.split('MI')[1].split('_')[0]); assert 1<=member<=20
    source=SOURCE_B if is_b else SOURCE_A
    for n,h in c['source_B_hashes' if is_b else 'source_hashes'].items(): assert sha(source/n)==h
    d=ROOT/'models'/ident; d.mkdir(exist_ok=False)
    data=MI/'private'/f'MI{member:02d}.dat'; members=list(csv.DictReader((MI/'audit/MI_MEMBERS.csv').open(newline='')))
    assert sha(data)==members[member-1]['sha256']; shutil.copy2(data,d/'data.dat')
    text=(source/'model.inp').read_text(encoding='ascii').replace('TITLE: '+source.name+';','TITLE: '+ident+';')
    assert 'sxiz | sx XWITH iz;' in text and 'KNOWNCLASS=cg(c3=0 c3=1);' in text
    (d/'model.inp').write_text(text,encoding='ascii'); shutil.copy2(source/'normalized_slots.json',d/'normalized_slots.json')
    j={'id':ident,'indicator':'oldest','group':'EDU','g':'C3','parent':False,'refinement':True,'member':member,'start':'B' if is_b else 'A','sensitivity_B':is_b,'points':15,'N':2397,'communities':433,'expected_free':134,'cap_seconds':240,'source_pilot':str(source),'hashes':{'model.inp':sha(d/'model.inp'),'data.dat':sha(d/'data.dat'),'normalized_slots.json':sha(d/'normalized_slots.json')}}
    save(d/'job.json',j); print(json.dumps({'id':ident,'member':member,'start':j['start'],'data_sha256':j['hashes']['data.dat']}),flush=True)
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='compile': compile_model(sys.argv[2])
    else: raise SystemExit('Use compile MODEL_ID')
