"""仅从本轮原始回执和高精度参数汇总采用状态，不启动模型。"""
from pathlib import Path
import csv,json,hashlib,re
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
rows=[]
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
for dest in sorted((root/'models').glob('*/*')):
    if not (dest/'receipt.json').exists():continue
    rec=json.loads((dest/'receipt.json').read_text(encoding='utf8'))
    row={'model':dest.parent.name,'attempt':dest.name,'N':rec['N'],'status':rec['status'],
         'inference':'DIAGNOSTIC_ONLY','input_sha256':rec['input_sha256'],
         'output_sha256':rec['output_sha256']}
    inp=(dest/'model.inp').read_text(encoding='utf8')
    constrained=bool(re.search(r'\bsy\s*@\s*0\s*;',inp,re.I))
    row['SY_residual_fixed_zero']=constrained
    pars=csvrows(dest/'parameters_high_precision.csv') if (dest/'parameters_high_precision.csv').exists() else []
    row['high_precision_parameter_sha256']=hashlib.sha256((dest/'parameters_high_precision.csv').read_bytes()).hexdigest() if pars else ''
    variances=[float(p['estimate']) for p in pars if p['matrix'] in {'psi','theta'} and p['row']==p['column']]
    if any(v<0 for v in variances):row['status']='INADMISSIBLE'
    for factor in ['IX','SX','IY','SY']:
        selected=[p for p in pars if p['matrix']=='psi' and p['row']==p['column']==factor]
        assert len(selected)<=1
        row[f'{factor}_residual']=float(selected[0]['estimate']) if selected else (0 if factor=='SY' and constrained and pars else '')
    for target,predictor in [('IY','IX'),('SY','SX')]:
        selected=[p for p in pars if p['matrix']=='beta' and p['row']==target and p['column']==predictor]
        assert len(selected)<=1
        for col in ['estimate','se']:
            row[f'{target}_ON_{predictor}_{col}']=float(selected[0][col]) if selected else ''
    if row['status']=='REVIEWABLE':
        row['inference']='CONSTRAINED_SENSITIVITY_ONLY' if constrained else 'MEMBER_REVIEWABLE_NOT_POOLED_INFERENCE'
    fit=csvrows(dest/'fit.csv') if (dest/'fit.csv').exists() else []
    for key in ['CFI','TLI','RMSEA_Estimate','SRMR','Parameters','LL']:
        row[key]=fit[0].get(key,'') if fit else ''
    rows.append(row)
fields=list(dict.fromkeys(k for row in rows for k in row))
with (root/'audit/model_adoption_summary.csv').open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
(root/'audit/model_adoption_summary_notes.md').write_text(
    '# 模型采用汇总的边界\n\n每行绑定本次INP、OUT和高精度参数哈希。非法模型的路径仅为诊断，未提供正式显著性判定。SY固定零是预定约束，不是估计值。参数协方差可逆不消除增长因子负残差。REVIEWABLE仅表示可以继续审阅，不自动通过拟合、缺失机制或MI合并验收。K1的1981人与K2—K4的1976人并非严格同样本比较。\n',encoding='utf8')
print(json.dumps({'rows':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in sorted(set(r['status'] for r in rows))}}))
