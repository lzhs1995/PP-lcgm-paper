"""复用现有完整来源登记，打包本次审阅所需的原始输出与摘要。"""
from review_workspace import PROJECT, PRIOR, Q, OUT, MAIN, APP, readj, writej, csvout, sha, paragraphs
from pathlib import Path
import re
import shutil
import json

def winpath(s):
    return Path('C:/'+s[7:]) if s.lower().startswith('/mnt/c/') else Path(s)

manifest=readj(PROJECT/'reports/cfps_full_docx_provenance_20261005/manifest.json')
modelrows=[];lookup={};selected=set()
for table in manifest['tables']:
    main='Appendix' not in table['document']
    caption=table['caption_context']
    found=re.findall(r'(?:Table|表)\s*(\d+(?:\.\d+)+)',caption)
    tableid=found[-1] if found else f"table_index_{table['table_index']}"
    for field,layer in [('historical_sources','historical'),('current_mplus_assets','replication')]:
        for asset in table[field]:
            path=winpath(asset['path'])
            if path.suffix.lower()!='.out':continue
            ident=sha(path)[:12]
            row={'model_id':ident,'document':table['document'],'table_index':table['table_index'],'table_id_context':tableid,'model':path.name,'source':str(path),'source_sha256':sha(path),'layer':layer,'R_producers':';'.join(table['producer_scripts']),'R_line_min':table['code_line_min'],'R_line_max':table['code_line_max'],'scientific_adoption':'NOT_AUTOMATIC_FROM_REPRODUCTION'}
            modelrows.append(row);lookup[str(path)]=row
            # 主文的基础、直接及四项核心调节；异质性仅保留索引，后续依需读取。
            if main and 1<=table['table_index']<=8 and (layer=='historical' or table['table_index']==4): selected.add(str(path))
for model in readj(Q/'corrected_raw_results_20261002/manifest.json')['models']:
    path=Path(model['output']);row={'model_id':sha(path)[:12],'document':'current_v42_v36','table_index':-1,'table_id_context':'4.2.1/4.2.2','model':model['model'],'source':str(path),'source_sha256':sha(path),'layer':'corrected_measurement_candidate','R_producers':'existing_8_model_receipt','scientific_adoption':'CHECK_FINAL_DIAGNOSTICS'}
    modelrows.append(row);lookup[str(path)]=row;selected.add(str(path))
csvout(OUT/'audit_stage1/model_index.csv',modelrows)
diagnostics=[];copied=[]
for source in sorted(selected):
    p=Path(source);record=lookup[source];root=OUT/'audit_stage1/mplus'/record['model_id'];root.mkdir(parents=True,exist_ok=True)
    raw=p.read_text(encoding='utf-8-sig',errors='replace'); lines=raw.splitlines()
    errors=[{'line':i+1,'text':t.strip()} for i,t in enumerate(lines) if re.search(r'\*\*\* ERROR|DID NOT TERMINATE NORMALLY|NO CONVERGENCE',t,re.I)]
    warns=[{'line':i+1,'text':' '.join(lines[i:min(i+4,len(lines))]).strip()} for i,t in enumerate(lines) if re.search(r'\*\*\* WARNING|NOT POSITIVE DEFINITE|FIXED TO AVOID SINGULARITY',t,re.I)]
    normals='THE MODEL ESTIMATION TERMINATED NORMALLY' in raw
    replicated=re.search(r'Number of replications\s+Requested\s+(\d+)\s+Completed\s+(\d+)',raw,re.I)
    rep_complete=bool(replicated and replicated[1]==replicated[2])
    auxiliary_only=bool(errors) and all('SAVEDATA' in e['text'] for e in errors)
    results_present='MODEL RESULTS' in raw and 'Ending Time:' in raw
    if auxiliary_only and results_present and (rep_complete or normals):
        status='ESTIMATION_READBACK_AUXILIARY_SAVEDATA_ERROR'
    elif errors:
        status='ERROR_REQUIRES_STAGE_REVIEW'
    elif normals or rep_complete:
        status='ESTIMATION_READBACK_DIAGNOSTICS_OPEN' if warns else 'ESTIMATION_READBACK_PARAMETER_REVIEW'
    else:
        status='TERMINATION_UNVERIFIED'
    n=re.findall(r'Number of observations\s+(\d+)',raw)
    parameter_count=re.findall(r'Number of Free Parameters\s+(\d+)',raw)
    growth=[t.strip() for t in lines if re.search(r'\b[iI]\w*\s+[sS]\w*\s*\|',t) and not t.strip().startswith('!')]
    estimator=re.findall(r'^\s*Estimator\s+(\S+)',raw,re.M)
    version=re.search(r'Mplus VERSION\s+(\S+)',raw)
    row={'model_id':record['model_id'],'model':record['model'],'layer':record['layer'],'N':n[0] if n else '', 'estimator':estimator[0] if estimator else '', 'version':version.group(1) if version else '', 'normal_marker':normals,'replications_complete':rep_complete,'error_count':len(errors),'warning_count':len(warns),'status':status,'n_parameters':parameter_count[0] if parameter_count else '', 'growth_syntax':' | '.join(growth),'source':source,'output_sha256':record['source_sha256']}
    diagnostics.append(row)
    for f in [p,p.with_suffix('.inp')]:
        if f.exists():
            target=root/f.name;shutil.copy2(f,target);copied.append({'source':str(f),'relative_path':str(target.relative_to(OUT/'audit_stage1')),'sha256':sha(f),'bytes':f.stat().st_size})
    writej(root/'diagnostics.json',{'errors':errors,'warnings':warns,'normal_marker':normals,'scope':'raw diagnostic inventory, not scientific acceptance'})
csvout(OUT/'audit_stage1/convergence_inventory.csv',diagnostics)
csvout(OUT/'audit_stage1/copied_files.csv',copied)
sources=[
 Q/'first_stage_time_loading_audit.json',Q/'cesd_five_wave_audit_summary.json',
 Q/'corrected_raw_results_20261002/eight_model_fit.csv',Q/'corrected_raw_results_20261002/eight_model_growth_means.csv',
 Q/'corrected_raw_results_20261002/linear_vs_shape_scaled_LR.json',
 Q/'mortality_roster_linkage_20261002/mortality_linkage_decision.json',
 PRIOR/'scientific_followup/existing_LRT_D2_candidates.csv',
 PROJECT/'reports/cfps_table455_456_acceptance_20261005/REPORT.md',
 PROJECT/'reports/cfps_full_docx_provenance_20261005/validation.json',
]
for p in sources:
    if p.exists():shutil.copy2(p,OUT/'source_evidence'/p.name)
for row in readj(OUT/'baseline_manifest.json')['files']:
    p=Path(row['path'])
    if p.suffix=='.R':
        dest=OUT/'audit_stage1/R_sources'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
writej(OUT/'audit_stage1/build_receipt.json',{'indexed_rows':len(modelrows),'unique_indexed_outputs':len(lookup),'packaged_outputs':len(selected),'copied_files':len(copied),'new_estimations':0,'original_source_hashes_verified':all(sha(Path(x['path']))==x['sha256'] for x in readj(OUT/'baseline_manifest.json')['files'])})
print(json.dumps(readj(OUT/'audit_stage1/build_receipt.json'),ensure_ascii=False))
