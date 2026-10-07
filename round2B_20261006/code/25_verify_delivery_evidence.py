"""只读核对最终父模型回执、原始输出、打印精度和公开入口；不重新估计。"""
from pathlib import Path
import csv, json, hashlib, ast

root = Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
receipts = json.loads((root/'audit/target_parent_receipts.json').read_text(encoding='utf8'))
assert len(receipts) == 10
rows = []
for rec in receipts:
    folder = root/'models'/rec['id']/'attempt01'
    for name, field in [('model.inp','input_sha256'),('model.out','output_sha256')]:
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == rec[field]
    raw = (folder/'model.out').read_text(encoding='utf8', errors='replace')
    assert ('THE MODEL ESTIMATION TERMINATED NORMALLY' in raw) == rec['normal']
    assert 'NEGATIVE VARIANCE/RESIDUAL VARIANCE' in raw
    with (folder/'parameters_high_precision.csv').open(encoding='utf-8-sig') as f:
        hp = list(csv.DictReader(f))
    sy = [p for p in hp if p['matrix']=='psi' and p['row']==p['column']=='SY']
    assert len(sy)==1 and float(sy[0]['estimate'])<0
    with (folder/'parameters.csv').open(encoding='utf-8-sig') as f:
        printed = list(csv.DictReader(f))
    sy_printed = [p for p in printed if p['param']=='SY' and p['paramHeader']=='Residual.Variances']
    assert len(sy_printed)==1
    for exact, rounded in [('estimate','est'),('se','se')]:
        assert abs(float(sy[0][exact])-float(sy_printed[0][rounded])) <= 0.0005001
    rows.append({'model':rec['id'], 'input_output_hashes':'PASS',
                 'raw_negative_variance_warning':True,
                 'SY_residual':float(sy[0]['estimate']), 'SY_SE':float(sy[0]['se']),
                 'printed_rounding':'PASS', 'status':rec['status']})
scope=json.loads((root/'DELIVERY_SCOPE.json').read_text(encoding='utf8'))
assert not scope['formal_MI_pooling_performed'] and not scope['core_moderation_performed']
assert not scope['seven_issues_all_resolved']
for p in (root/'code').glob('*.py'):
    ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
result={'status':'PASS','models':rows,'scope_consistent':True,
        'limits':'Checks saved outputs and file provenance; no independent model refit.'}
(root/'audit/final_evidence_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':'PASS','parents':len(rows),'SY_range':[min(r['SY_residual'] for r in rows),max(r['SY_residual'] for r in rows)]}))
