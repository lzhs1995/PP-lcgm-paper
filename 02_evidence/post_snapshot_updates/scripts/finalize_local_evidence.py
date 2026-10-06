"""冻结本地科学处置与资源测量；不把编校完成提升为科学放行。"""
from review_workspace import OUT, PROJECT, readj, writej, csvout, sha
from pathlib import Path
import csv,json,re,shutil,statistics
from datetime import datetime,timezone
root=OUT/'audit_stage1';rows=[]
for p in sorted((root/'mplus').glob('*/*.out')):
 raw=p.read_text(encoding='utf-8-sig',errors='replace');flat=' '.join(raw.split())
 mi=re.search(r'Number of replications\s+Requested\s+(\d+)\s+Completed\s+(\d+)',raw)
 normal='THE MODEL ESTIMATION TERMINATED NORMALLY' in flat
 matrix=bool(re.search(r'NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT',flat))
 nonconv=bool(re.search(r'NO CONVERGENCE|DID NOT CONVERGE|DID NOT TERMINATE NORMALLY',flat))
 error_lines=[s.strip() for s in raw.splitlines() if '*** ERROR' in s]
 aux=bool(error_lines) and all('SAVEDATA' in s for s in error_lines)
 complete=normal or bool(mi and mi[1]==mi[2])
 state='INPUT_OR_RUNTIME_ERROR' if error_lines and not aux else 'NONCONVERGED' if nonconv else 'MI_INCOMPLETE' if mi and mi[1]!=mi[2] else 'MATRIX_DIAGNOSTIC_REVIEW' if matrix else 'TERMINAL_PARAMETER_REVIEW' if complete else 'TERMINATION_UNVERIFIED'
 rows.append({'model_id':p.parent.name,'file':str(p.relative_to(root)),'sha256':sha(p),'normal_marker':normal,'MI_requested':mi[1] if mi else '', 'MI_completed':mi[2] if mi else '', 'matrix_warning_wrapped_text':matrix,'auxiliary_savedata_error':aux,'status':state,'scientific_release':False})
csvout(root/'convergence_inventory_final.csv',rows)
watch=OUT/'native/sensitivity_resource_watch.jsonl'
samples=[];models=[]
for line in watch.read_text(encoding='utf-8').splitlines():
 try:r=json.loads(line)
 except json.JSONDecodeError:continue
 if r.get('event')=='sample':
  samples.append(r)
  models.extend(m for m in r['models'] if m.get('owned'))
cpus=[m['cpu_core_percent'] for m in models if m['cpu_core_percent'] is not None]
receipt=readj(OUT/'analysis/sensitivity_input_repair/execution_receipt.json')
performance={'monitor_samples':len(samples),'owned_model_samples':len(models),'rss_peak_mib':max((m['rss_mib'] for m in models),default=None),'private_peak_mib':max((m['private_mib'] for m in models),default=None),'observed_cpu_core_percent':cpus,'free_physical_min_gib':min((r['memory']['available']/2**30 for r in samples),default=None),'direct_fit_seconds':[{'model':r['id'],'seconds':r['seconds']} for r in receipt],'limitation':'Sampled peaks only. Short univariate models were not necessarily sampled. Not a matched upgrade benchmark; no claim that raising priority caused faster estimates.'}
writej(OUT/'native/sensitivity_performance_summary.json',performance)
stamp=datetime.now(timezone.utc).isoformat()
state=readj(OUT/'state.json');state.update(stage='MANUSCRIPT_CANDIDATE_AND_TARGETED_SENSITIVITY_COMPLETE_NLM_PENDING',updated_at=stamp,new_mplus=12,distinct_new_specifications=8,failed_input_attempts=4,current_sensitivity={'reviewable':3,'inadmissible':3,'nonconverged':2},new_interactions=0,manuscript_release=False,reason='CESD8 five-wave baseline inadmissible; MI/VCOV scientific boundaries remain.')
writej(OUT/'state.json',state)
baseline=readj(OUT/'baseline_manifest.json');assert all(sha(r['path'])==r['sha256'] for r in baseline['files'])
writej(OUT/'baseline_recheck.json',{'checked_at':stamp,'files':len(baseline['files']),'all_original_hashes_unchanged':True})
print(json.dumps(performance,ensure_ascii=False))
