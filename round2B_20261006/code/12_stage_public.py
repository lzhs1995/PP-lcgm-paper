"""按允许清单汇集公开证据；不复制任何微观数据或插补对象。"""
from pathlib import Path
import shutil,json,csv,hashlib,sys
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');stage=root/'public_stage';stage.mkdir(exist_ok=True)
build='build03' if '--build03' in sys.argv else 'build02'
if build=='build03':assert (root/'manuscript/build03_visual_review.json').exists()
def copy(src,rel=None):
 dest=stage/(rel or src.relative_to(root));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
for f in (root/'code').iterdir():
 if f.suffix.lower() in {'.r','.py'}:copy(f)
for f in (root/'audit').rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.csv','.json','.md','.pdf'}:
  if f.name in {'mi_chain_means.csv','mi_chain_variances.csv'}:
   policy=json.loads((root/'audit/mi_release_policy.json').read_text(encoding='utf8'))
   with f.open(newline='',encoding='utf-8-sig') as stream:
    reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
   assert fields and 'Freq' in fields
   suppressed=set(policy['suppressed_variables'])
   for row in rows:
    if row[fields[0]] in suppressed:row['Freq']='NA'
   dest=stage/f.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('w',newline='',encoding='utf8') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
   receipt={'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
            'released_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
            'suppressed_variables':sorted(suppressed),'policy':'mi_release_policy.json'}
   dest.with_suffix('.redaction.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
  else:copy(f)
for folder in sorted((root/'models').glob('*/*')):
 if not folder.is_dir():continue
 for name in ['model.inp','model.out','receipt.json','input_contract.json','parameters.csv','fit.csv','parameters_high_precision.csv','parameter_covariance.csv','parameter_binding.json','parameter_covariance_diagnostics.json','parameter_extraction_failure.json']:
  f=folder/name
  if f.exists():
   copy(f)
   if f.suffix in {'.inp','.out'}:copy(f,Path(str(f.relative_to(root))+'.txt'))
for f in (root/'manuscript').iterdir():
 if f.name.endswith(f'_{build}_NOT_RELEASED.docx') or f.name.endswith(f'_{build}_NOT_RELEASED.pdf'):copy(f)
for name in ['main_revision_receipt.json','appendix_revision_receipt.json','appendix_header_corrections.json','appendix_table_status.json','editorial_checked_receipt.json','main_editorial_changes.json','native_word_export_build02.json','pdf_readback_build02.json','final_visual_review.json']:
 f=root/'manuscript'/name
 if f.exists():copy(f)
if build=='build03':
 for name in ['build03_editorial_receipt.json','native_word_export_build03.json','pdf_readback_build03.json','build03_pixel_comparison.json','build03_pdf_text_checks.json','build03_visual_review.json']:
  copy(root/'manuscript'/name)
readable=root/('readable_'+build)
if readable.exists():
 for f in readable.rglob('*.md'):copy(f,Path('readable')/f.relative_to(readable))
for name in ['REPORT.md','MODEL_INDEX.md','FOR_WEB_REVIEWERS.md','SEVEN_ISSUES.csv','EVIDENCE_INDEX.md','README.md','DELIVERY_SCOPE.json']:
 f=root/name
 if f.exists():copy(f)
for name in ['resource_admission_K.json','resource_admission_MI.json','resource_admission_parent.json','python_syntax_validation.json','r_syntax_validation.json','public_privacy_scan.json','public_privacy_scan.csv','tool_limitations.json']:
 f=root/'runtime'/name
 if f.exists():copy(f)
for name in ['nlm_candidate_question.txt','nlm_candidate_review_raw.json','nlm_candidate_binding.json']:
 f=root/'runtime'/name
 if f.exists():copy(f,Path('external_review')/name)
files=sorted(p for p in stage.rglob('*') if p.is_file())
assert not any(p.suffix.lower() in {'.dat','.dta','.rds','.gh5','.rdata'} for p in files)
rows=[{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if p.name!='FILE_MANIFEST.csv']
with (stage/'FILE_MANIFEST.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'stage':str(stage),'status':'STAGED_NOT_PUBLISHED'},ensure_ascii=False))
