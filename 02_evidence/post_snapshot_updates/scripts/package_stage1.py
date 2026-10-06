"""按明确目录白名单生成无个体记录的审计包并逐文件核验。"""
from review_workspace import OUT, readj, writej, csvout, sha
from pathlib import Path
from datetime import datetime,timezone
import zipfile,hashlib,re,shutil
root=OUT/'audit_stage1'
for name in ['sensitivity_performance_summary.json','environment.txt']:
 src=OUT/'native'/name
 if src.exists():shutil.copy2(src,root/name)
files=[p for p in sorted(root.rglob('*')) if p.is_file() and p.name!='manifest.csv']
for p in files:
 assert p.suffix.lower() not in ['.dat','.rds','.rdata','.msi','.exe','.sav','.dta']
 assert not re.search(r'(?i)(api[_-]?key|password|access[_-]?token)\s*[:=]\s*[\x22\x27][^\x22\x27\s]{8,}',p.read_text(encoding='utf-8-sig',errors='ignore')) if p.suffix.lower() in ['.r','.json','.inp','.out'] else True
rows=[{'relative_path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'source_or_copy_mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'category':p.relative_to(root).parts[0] if len(p.relative_to(root).parts)>1 else 'register','model_id':p.parent.name if p.parent.parent.name=='mplus' else ''} for p in files]
csvout(root/'manifest.csv',rows)
archive=OUT/'LGCM_audit_stage1_20261005.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files+[root/'manifest.csv']:z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for row in rows:
  with z.open(row['relative_path']) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256']
baseline=readj(OUT/'baseline_manifest.json');assert all(sha(r['path'])==r['sha256'] for r in baseline['files'])
receipt={'status':'PASS','zip':str(archive),'zip_bytes':archive.stat().st_size,'zip_sha256':sha(archive),'files':len(files)+1,'mplus_outputs':len(list((root/'mplus').glob('*/*.out'))),'all_entry_hashes_verified':True,'all_baseline_hashes_unchanged':True,'individual_data_included':False,'uploaded':False}
writej(OUT/'audit_package_receipt.json',receipt);print(receipt)
