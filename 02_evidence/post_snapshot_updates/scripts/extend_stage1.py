"""补齐审计优先级来源，仅复制inp/out和汇总，禁止带入个体数据。"""
from review_workspace import OUT, PROJECT, PRIOR, Q, readj, writej, csvout, sha
from pathlib import Path
import csv,re,shutil
ROOT=OUT/'audit_stage1';sources={}
def add(p,role):
 p=Path(p)
 if p.exists() and p.suffix.lower()=='.out':sources[str(p)]=role
indexed=list(csv.DictReader((ROOT/'model_index.csv').open(encoding='utf-8-sig')))
for r in indexed:
 n=r['model'].lower()
 if re.match(r'pp_lgca_type(12|13|14|14_4)_r_step2_(cat_)?[is]_mod_[is]_mi_tics.out$',n):add(r['source'],'core_two_stage_interaction')
 if re.match(r'pp_lgca_type(12|13|14|14_4)_(edu12|urban12|pinc412)_r_step2_cat_[is]_mod_[is]_mi_tics.out$',n):add(r['source'],'three_way_exploratory')
 if re.match(r'c_pp_lgca_type[1-4].*mi_tics.out$',n) and not re.search('edu|sex|urban|pinc',n):add(r['source'],'direct_association')
known=Path(r'C:\Users\LZHS\Desktop\interge_rela\result_pp_lgca_continu.panel_best_clo_ces8sd_covar_time12_22')
for pattern in ['c_pp_lgca_type1_mi_tics.out','c_pp_lgca_type2_mi_tics.out','c_pp_lgca_type3_mi_tics.out','lgca_process[12345]_*.out','lgca_process44_*.out','pp_lgca_type1[234]*step2*base*.out']:
 for p in known.glob(pattern):add(p,'historical_basis_or_score')
for p in Path(r'C:\Users\LZHS\pp_lgcm_sensitivity\20261002_direct11_contract\candidate_inputs').glob('*/model.out'):add(p,'corrected_direct11_MI_candidate')
for batch in ['sensitivity','sensitivity_input_repair']:
 for p in (OUT/'analysis'/batch).glob('*/model.out'):add(p,batch)
for p in (PROJECT/'work/cfps_moderation_tech3_repair_20261004/output').glob('*_base/*.out'):add(p,'existing_TECH3_nonMI_calibration')
rows=[]
for source,role in sorted(sources.items()):
 p=Path(source);key=sha(p)[:12];folder=ROOT/'mplus'/key;folder.mkdir(exist_ok=True,parents=True)
 text=p.read_text(encoding='utf-8-sig',errors='replace');flat=' '.join(text.split())
 for f in [p,p.with_suffix('.inp')]:
  if f.exists():
   target=folder/f.name
   if target.exists():assert sha(target)==sha(f)
   else:shutil.copy2(f,target)
 n=re.search(r'Number of observations\s+(\d+)',text)
 clusters=re.search(r'Number of clusters\s+(\d+)',text)
 mi=re.search(r'Number of replications\s+Requested\s+(\d+)\s+Completed\s+(\d+)',text)
 data=re.search(r'\bFILE\s*(?:IS|=)\s*([^;]+)',text,re.I)
 inp=p.with_suffix('.inp');syntax=inp.read_text(encoding='utf-8-sig',errors='replace') if inp.exists() else ''
 rows.append({'model_id':key,'role':role,'source':source,'packaged_output':str((folder/p.name).relative_to(ROOT)),'input_present':inp.exists(),'data_reference_only':data[1].strip() if data else 'NA','N':n[1] if n else 'MI: see member output','households':clusters[1] if clusters else 'NA','requested_MI':mi[1] if mi else '', 'completed_MI':mi[2] if mi else '', 'normal_marker':'THE MODEL ESTIMATION TERMINATED NORMALLY' in flat,'matrix_warning':bool(re.search('NOT POSITIVE DEFINITE|NON-POSITIVE DEFINITE|SADDLE POINT',flat)),'nonconvergence':bool(re.search('NO CONVERGENCE|DID NOT CONVERGE',flat)),'input_error':'*** ERROR in' in text,'TECH3_present':'TECHNICAL 3 OUTPUT' in text,'TECH8_present':'TECHNICAL 8 OUTPUT' in text,'MODINDICES_present':'MODIFICATION INDICES' in text,'interaction_syntax':' | '.join(line.strip() for line in syntax.splitlines() if 'XWITH' in line.upper()),'source_sha256':sha(p),'scientific_adoption':'NOT_AUTOMATIC'})
csvout(ROOT/'model_details.csv',rows)
# 可复用的科学边界证据，独立命名，防同名覆盖。
for label,folder in [('moderation_readback',PROJECT/'reports/cfps_moderation_readback_20261004'),('scientific_boundaries',PROJECT/'reports/cfps_scientific_boundary_audit_20261004'),('table455456',PROJECT/'reports/cfps_table455_456_acceptance_20261005')]:
 target=ROOT/'existing_evidence'/label;target.mkdir(parents=True,exist_ok=True)
 for p in folder.iterdir():
  if p.is_file() and p.suffix in ['.csv','.json','.md']:shutil.copy2(p,target/p.name)
for label,folder in [('summaries',OUT/'summaries'),('source_evidence',OUT/'source_evidence')]:
 target=ROOT/label;target.mkdir(exist_ok=True)
 for p in folder.iterdir():
  if p.is_file() and p.suffix in ['.csv','.json','.md','.pdf','.txt']:shutil.copy2(p,target/p.name)
for p in [OUT/'OPINION_DECISIONS.md',OUT/'opinion_decisions.csv',OUT/'native/environment.txt']:
 shutil.copy2(p,ROOT/p.name)
code=ROOT/'review_scripts';code.mkdir(exist_ok=True)
for p in Path(__file__).parent.glob('*.R'):shutil.copy2(p,code/p.name)
writej(ROOT/'extension_receipt.json',{'added_or_verified_outputs':len(rows),'total_packaged_outputs':len(list((ROOT/'mplus').glob('*/*.out'))),'individual_data_copied':False,'source_mutations':0})
print(readj(ROOT/'extension_receipt.json'))
