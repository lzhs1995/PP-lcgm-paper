"""公开文件扫描后绑定打包；每包最多25,000,000字节并完整解压核验。"""
from pathlib import Path
import csv,json,zipfile,hashlib,io
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');S=R/'public_stage'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert json.loads((R/'runtime/public_privacy_scan.json').read_text())['status']=='PASS'
 with (R/'runtime/public_scan_file_hashes.csv').open(encoding='utf-8-sig',newline='') as f:bound=list(csv.DictReader(f))
 exempt={'runtime/public_privacy_scan.json','runtime/public_scan_file_hashes.csv'}
 files=sorted(p for p in S.rglob('*') if p.is_file())
 assert {p.relative_to(S).as_posix() for p in files}=={r['path'] for r in bound}|exempt
 for r in bound:assert sha(S/r['path'])==r['sha256'],r['path']
 manifest=[{'path':p.relative_to(S).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
 with (S/'FILE_MANIFEST.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(manifest)
 files.append(S/'FILE_MANIFEST.csv')
 groups={'01_reports_manuscripts':[],'02_models_code':[]}
 for p in files:groups['02_models_code' if p.relative_to(S).parts[0] in {'models','code','vendor'} else '01_reports_manuscripts'].append(p)
 packages=[]
 def pack(group,items,part):
  # 先在内存形成包，超限时分拆，避免发布超限包。
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
   for p in items:z.write(p,p.relative_to(S).as_posix())
  b=stream.getvalue()
  if len(b)>25_000_000:
   assert len(items)>1,'Single file cannot meet size cap';mid=len(items)//2
   return pack(group,items[mid:],pack(group,items[:mid],part))
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==len(items)
   for p in items:assert hashlib.sha256(z.read(p.relative_to(S).as_posix())).hexdigest()==sha(p)
  name=f'{group}_{part:02}.zip';(S/name).write_bytes(b)
  packages.append({'path':name,'bytes':len(b),'files':len(items),'sha256':hashlib.sha256(b).hexdigest(),'CRC':'PASS','extraction_hashes':'PASS'})
  return part+1
 for group,items in groups.items():pack(group,items,1)
 result={'limit_bytes':25_000_000,'packages':packages,'microdata_included':False}
 (S/'PACKAGE_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 (R/'runtime/package_validation.json').write_text(json.dumps({'status':'PASS',**result},ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
