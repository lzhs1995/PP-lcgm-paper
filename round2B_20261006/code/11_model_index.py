"""从实际回执/高精度参数建立可公开的逐次执行索引。"""
from pathlib import Path
import csv,json,hashlib
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');rows=[]
for receipt in sorted((root/'models').glob('*/*/receipt.json')):
 r=json.loads(receipt.read_text(encoding='utf8'));folder=receipt.parent
 row={k:r.get(k) for k in ['id','N','status','normal','negative_variance','matrix_warning','finite_parameters','seconds','input_sha256','data_sha256','output_sha256']}
 row['attempt']=folder.name;row['path']=folder.relative_to(root).as_posix()
 if (folder/'fit.csv').exists():
  fit=next(csv.DictReader((folder/'fit.csv').open(encoding='utf-8-sig')))
  for k in ['CFI','TLI','RMSEA_Estimate','SRMR','AIC','BIC','Parameters']:row[k]=fit.get(k)
 p=folder/'parameters_high_precision.csv'
 if p.exists():
  ps=list(csv.DictReader(p.open(encoding='utf-8-sig')))
  for label,matrix,a,b in [('SY_residual','psi','SY','SY'),('SX_residual','psi','SX','SX'),('SY_ON_SX','beta','SY','SX')]:
   q=[x for x in ps if x['matrix']==matrix and x['row']==a and x['column']==b]
   if q:
    row[label]=q[0]['estimate'];row[label+'_SE']=q[0]['se']
 row['parameter_covariance_bound']=(folder/'parameter_binding.json').exists()
 rows.append(row)
keys=list(dict.fromkeys(k for row in rows for k in row))
with (root/'audit/model_execution_index.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
lines=['# 本轮模型执行索引','', '输入被拒绝、正常结束但不可接受、可继续审阅分别登记。受约束模型须结合规格说明，不能单凭REVIEWABLE作为主分析。','', '| 模型 | 尝试 | N | 状态 | 完整输入与输出 |','|---|---|---:|---|---|']
for r in rows:lines.append(f"| {r['id']} | {r['attempt']} | {r['N']} | {r['status']} | [INP]({r['path']}/model.inp.txt) / [OUT]({r['path']}/model.out.txt) |")
(root/'MODEL_INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps({'executions':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}},ensure_ascii=False))
