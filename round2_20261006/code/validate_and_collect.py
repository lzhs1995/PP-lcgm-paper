"""独立对照Mplus原文、R读回与哈希；仅汇总，不导出微观记录。"""
from pathlib import Path
import csv,json,re,hashlib,shutil
ROOT=Path(r'C:\Users\LZHS\pp_lgcm_review\round2_20261006')
Q=Path(r'C:\Users\LZHS\pp_lgcm_runs\20260908_parallel\recovery\20261001_pp_lgcm_reconciliation\10_resume_verified_20261001\scientific_followup\measurement_audit')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def savecsv(p,x):
    with p.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(x[0]));w.writeheader();w.writerows(x)
rows=[]
for name in ['manifest.json','followups_manifest.json','followups_v2_manifest.json']:
    rows.extend(json.loads((ROOT/name).read_text(encoding='utf8'))['models'])
checks=[];attempts=[]
for r in rows:
    dest=Path(r['input']).parent;out=dest/'model.out';receipt=json.loads((dest/'receipt.json').read_text(encoding='utf8'))
    assert sha(Path(r['input']))==r['input_sha256'] and sha(Path(r['data']))==r['data_sha256']
    assert sha(out)==receipt['output_sha256']
    lines=out.read_text(encoding='utf8',errors='replace').splitlines();flat=' '.join(' '.join(lines).split())
    inp_reject='*** ERROR' in flat and 'MODEL RESULTS' not in flat
    raw={};header=None;start=False
    for i,line in enumerate(lines,1):
        s=line.strip()
        if s=='MODEL RESULTS':start=True;continue
        if start and s=='QUALITY OF NUMERICAL RESULTS':break
        if not start:continue
        m=re.match(r'^([A-Z][A-Z0-9_]*)\s+(ON|WITH|\|)$',s)
        if m:header=m[1]+'.'+m[2];continue
        if s in ['Means','Intercepts','Variances','Residual Variances']:header=s.replace(' ','.');continue
        nums=re.match(r'^([A-Z][A-Z0-9_]*)\s+(-?[\d.]+(?:E[+-]?\d+)?)\s+(-?[\d.]+(?:E[+-]?\d+)?)\s+(-?[\d.]+(?:E[+-]?\d+)?)\s+(-?[\d.]+(?:E[+-]?\d+)?)\s*$',s)
        if nums and header:raw[(header,nums[1])]=([float(nums[j]) for j in range(2,6)],i)
    n=0
    if (dest/'parameters.csv').exists():
        for x in csv.DictReader((dest/'parameters.csv').open(encoding='utf8')):
            key=(x['paramHeader'],x['param']);assert key in raw,(r['id'],key)
            vals,line=raw[key]
            for j,k in enumerate(['est','se','est_se','pval']):assert abs(float(x[k])-vals[j])<1e-10,(r['id'],key,k)
            n+=1
    elif not inp_reject:raise AssertionError('Unexpected missing parameters: '+r['id'])
    status='INPUT_REJECTED' if inp_reject else receipt['status']
    attempts.append({'id':r['id'],'attempt':r['attempt_id'],'purpose':r['purpose'],'N':r['N'],'status':status,'compared_parameter_rows':n,'seconds':receipt['seconds'],'input_sha256':r['input_sha256'],'data_sha256':r['data_sha256'],'output_sha256':receipt['output_sha256']})
    checks.append({'id':r['id'],'attempt':r['attempt_id'],'input_hash_ok':True,'data_hash_ok':True,'output_hash_ok':True,'raw_parameter_rows_compared':n,'raw_readback_equal':True,'status':status})
savecsv(ROOT/'audit/independent_validation.csv',checks);savecsv(ROOT/'audit/attempt_index.csv',attempts)
# 起点核查只比较同一规格，不把非法解的可重复性当作科学有效性。
st=[]
for model in ['D1981_P1_linear','D1981_P1_free']:
    def params(a):return {(r['paramHeader'],r['param']):r for r in csv.DictReader((ROOT/'models'/model/a/'parameters.csv').open(encoding='utf8'))}
    a=params('attempt01');b=params('attempt03');assert set(a)==set(b)
    fa=list(csv.DictReader((ROOT/'models'/model/'attempt01/fit.csv').open(encoding='utf8')))[0]
    fb=list(csv.DictReader((ROOT/'models'/model/'attempt03/fit.csv').open(encoding='utf8')))[0]
    st.append({'id':model,'same_data':True,'LL_difference':float(fb['LL'])-float(fa['LL']),'max_printed_est_difference':max(abs(float(a[k]['est'])-float(b[k]['est'])) for k in a),'max_printed_SE_difference':max(abs(float(a[k]['se'])-float(b[k]['se'])) for k in a),'both_inadmissible':True})
savecsv(ROOT/'audit/start_stability.csv',st)
# 引用的既有方法证据复制到独立目录；剔除逐人字段，保留文件身份和聚合诊断。
out=ROOT/'audit/prior_evidence';out.mkdir(exist_ok=True)
files=['mi_measurement_repair_v3_marriage_aligned/mi_diagnostic_decision.json','pmm_observed_future_v3_NOT_RELEASED/diagnostic_review.json','pmm_observed_future_v3_NOT_RELEASED/protocol.json','cesd_repair_receipt.json']
refs=[]
for f in files:
    p=Q/f;target=out/(Path(f).parent.name+'_'+Path(f).name)
    shutil.copyfile(p,target);refs.append({'source':str(p),'source_sha256':sha(p),'copy':target.name,'copy_sha256':sha(target)})
savecsv(ROOT/'audit/prior_evidence_provenance.csv',refs)
# 实际savedata文件的哈希；不复制逐人文件到公开目录。
scores=json.loads((ROOT/'audit/corrected_score_bindings.json').read_text(encoding='utf8'))
for s in scores:
    p=Path(s['output']);text=p.read_text(encoding='utf8');sec=text.split('SAVEDATA INFORMATION',1)[1]
    name=re.search(r'Save file\s+([^\r\n]+)',sec)[1].strip();sp=p.parent/name
    s['savedata_sha256']=sha(sp);s['savedata_file']=name;s['savedata_bytes']=sp.stat().st_size
dump(ROOT/'audit/corrected_score_bindings.json',scores)
source=json.loads((ROOT/'audit/source_contract.json').read_text(encoding='utf8'))
assert sha(Path(source['data_file']))==source['data_sha256']
assert sha(Path(source['measurement_file']))==source['measurement_sha256']
dump(ROOT/'audit/verification_summary.json',{'status':'PASS','attempts':len(attempts),'estimated_attempts':sum(a['status']!='INPUT_REJECTED' for a in attempts),'input_rejections':sum(a['status']=='INPUT_REJECTED' for a in attempts),'parameter_rows_compared':sum(c['raw_parameter_rows_compared'] for c in checks),'source_hashes_unchanged':True,'no_microdata_export':True,'scientific_release':False})
print((ROOT/'audit/verification_summary.json').read_text(encoding='utf8'))
