"""只读核对模型入口与冻结聚合描述的尺度；不输出任何逐人值或标识。"""
from pathlib import Path
import numpy as np
import csv,json,hashlib
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007')
data=R/'models/C1_MI01/attempt01/data.dat'
source=R.parent/'round2B_20261006/audit/observed_longitudinal_descriptives.csv'
with source.open(encoding='utf-8-sig',newline='') as f:desc=list(csv.DictReader(f))
a=np.genfromtxt(data,missing_values='.',filling_values=np.nan);assert a.shape==(3274,35)
out=[];reference={}
for typ,prefix,offset in [('X','wfd_m',1),('Y','ces8',6)]:
 base=next(d for d in desc if d['year']=='2012' and d['variable'].startswith(prefix))
 mu=float(base['mean']);sd=float(base['sd']);reference[typ]={'mean':mu,'sd':sd}
 for i,year in enumerate([2012,2016,2018,2020,2022]):
  d=next(d for d in desc if d['year']==str(year) and d['variable'].startswith(prefix));x=a[:,offset+i]
  mean=float(np.nanmean(x));expected=(float(d['mean'])-mu)/sd;n=int(np.isfinite(x).sum())
  assert abs(mean-expected)<1e-6 and n==int(d['N'])
  out.append({'process':typ,'year':year,'N':n,'input_mean':mean,'expected_frozen_baseline_mean':expected,'difference':mean-expected})
report={'status':'PASS','data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'aggregate_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'baseline_reference':reference,'checks':out,'scope':'Aggregate count and mean checks supplement prior row/hash binding; do not independently reconstruct raw item scoring'}
(R/'audit/input_scale_reproducible_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':report['status'],'process_wave_checks':len(out),'reference':reference},ensure_ascii=False))
