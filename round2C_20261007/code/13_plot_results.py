"""科学图：固定残差剖面与独立通过门槛的条件MI路径；不绘制显著性星号。"""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');D=R/'figures';D.mkdir(exist_ok=True)
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
labels={'bii':'Closeness intercept -> depression intercept','bis':'Closeness intercept -> depression change','bss':'Closeness change -> depression change','bsyiy':'Depression intercept -> depression change'}
assert json.loads((R/'evidence/independent_verification.json').read_text())['status']=='PASS'
p=rows(R/'results/profile_MI01.csv');fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
for ax,(key,title) in zip(axes.flat,labels.items()):
 z=[x for x in p if x['label']==key]
 for x in z:
  tau=float(x['tau']);q=float(x['estimate']);legal=x['usable']=='TRUE'
  if legal:ax.errorbar(tau,q,yerr=[[q-float(x['lower'])],[float(x['upper'])-q]],fmt='o',color='#24547a',capsize=4)
  else:ax.plot(tau,q,'x',color='#a74242',markersize=8)
 ax.axhline(0,color='.6',lw=.8);ax.set_title(title,fontsize=10);ax.set_xlabel('Fixed conditional SY residual variance');ax.set_ylabel('Path estimate');ax.grid(axis='y',alpha=.2)
fig.suptitle('MI01 fixed-residual profile: conditional estimates, not a confidence region',fontsize=13)
fig.text(.5,-.025,'Blue: admissible, conditional 95% Wald interval. Red cross: inadmissible point (diagnostic only).\nC1 structure without same-wave residual covariances; fixed baseline scale; 10-year endpoint loading.',ha='center',fontsize=9)
fig.savefig(D/'profile_MI01.pdf',bbox_inches='tight');fig.savefig(D/'profile_MI01.png',dpi=160,bbox_inches='tight');plt.close(fig)
source=R/'results/conditional_MI_paths.csv'
if source.exists():
 p=rows(source);families=list(dict.fromkeys(x['spec'] for x in p));fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
 for ax,(key,title) in zip(axes.flat,labels.items()):
  for i,spec in enumerate(families):
   x=next(x for x in p if x['spec']==spec and x['label']==key);q=float(x['estimate']);ax.errorbar(q,i,xerr=[[q-float(x['lower'])],[float(x['upper'])-q]],fmt='o',capsize=4)
  ax.set_yticks(range(len(families)),families);ax.set_ylim(-.6,len(families)-.4);ax.axvline(0,color='.6',lw=.8);ax.set_title(title,fontsize=10);ax.set_xlabel('Estimate and conditional MI 95% interval');ax.grid(axis='x',alpha=.2)
 fig.suptitle('Each eligible family pooled separately across all 10 imputations',fontsize=13)
 fig.text(.5,-.025,'C1: fixed SY residual=0. SW: same-wave residual covariances. XLIN: calendar-linear X and Y.\nGrowth-factor meaning differs across structures; intervals exclude model-selection uncertainty.',ha='center',fontsize=9)
 fig.savefig(D/'conditional_MI_paths.pdf',bbox_inches='tight');fig.savefig(D/'conditional_MI_paths.png',dpi=160,bbox_inches='tight');plt.close(fig)
out=[{'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(D.glob('*.pdf'))]
(D/'figure_manifest.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
