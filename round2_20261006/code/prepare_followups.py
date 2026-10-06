"""预先约定的局部诊断：两项结构敏感性及两次起点核查。"""
from pathlib import Path
import json,hashlib,re,shutil
ROOT=Path(r'C:\Users\LZHS\pp_lgcm_review\round2_20261006')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
m=json.loads((ROOT/'manifest.json').read_text(encoding='utf8'))
rows={r['id']:r for r in m['models']}
out=[]
cases=[('D1981_P1_linear','D1981_P1_linear_xcov','attempt01','ix sx WITH c1-c26;','X_growth_covariate_covariance_sensitivity'),
       ('D1981_P1_linear','D1981_P1_linear_boundary','attempt02','sy@0;\nsy WITH iy@0 ix@0 sx@0;','conditional_SY_zero_boundary_sensitivity'),
       ('D1981_P1_linear','D1981_P1_linear','attempt03','iy*.3; sy*.001; ix*.3; sx*.001;','starting_values_only'),
       ('D1981_P1_free','D1981_P1_free','attempt03','iy*.3; sy*.001; ix*.3; sx*.001;\niy sy | y1@0 y2*3 y3*6 y4*9 y5@10;\nix sx | x1@0 x2*3 x3*6 x4*9 x5@10;','starting_values_only')]
for src_id,ident,attempt,extra,purpose in cases:
    src=rows[src_id];dest=ROOT/'models'/ident/attempt;dest.mkdir(parents=True,exist_ok=False)
    text=Path(src['input']).read_text(encoding='utf8')
    if purpose=='starting_values_only' and src_id.endswith('_free'):
        extra='iy*.3; sy*.001; ix*.3; sx*.001;'
        text=text.replace('y2*4 y3*6 y4*8','y2*3 y3*6 y4*9').replace('x2*4 x3*6 x4*8','x2*3 x3*6 x4*9')
    text=text.replace('OUTPUT:',extra+'\nOUTPUT:')
    # MplusAutomation可生成无分号TITLE；仅替换至DATA段前，不能吞掉FILE语句。
    text=re.sub(r'TITLE:.*?(?=^DATA:)',f'TITLE: Round2 {ident} {attempt};\n',text,count=1,flags=re.S|re.M)
    assert re.search(r'DATA:\s*FILE\s*=\s*"data.dat";',text)
    assert max(map(len,text.splitlines()))<=90
    (dest/'model.inp').write_text(text,encoding='utf8')
    shutil.copyfile(src['data'],dest/'data.dat')
    assert sha(dest/'data.dat')==src['data_sha256']
    r={**src,'id':ident,'attempt_id':attempt,'input':str(dest/'model.inp'),'data':str(dest/'data.dat'),'input_sha256':sha(dest/'model.inp'),'parent':src_id,'purpose':purpose}
    out.append(r)
(ROOT/'followups_v2_manifest.json').write_text(json.dumps({**m,'models':out},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'prepared':len(out),'new_scientific_specs':2,'new_starts':2,'data_unchanged':True}))
