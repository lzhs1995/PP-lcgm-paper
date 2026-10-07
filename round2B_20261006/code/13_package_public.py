"""生成小于25,000,000字节的可独立解压资料包，逐包CRC与SHA核验。"""
from pathlib import Path
import json,zipfile,hashlib,csv
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006');stage=root/'public_stage'
privacy=json.loads((root/'runtime/public_privacy_scan.json').read_text(encoding='utf8'));assert privacy['status']=='PASS'
scope=json.loads((stage/'DELIVERY_SCOPE.json').read_text(encoding='utf8'));assert scope['ready_for_publication'] is True
files=sorted(p for p in stage.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='PACKAGE_MANIFEST.json')
bound=list(csv.DictReader((root/'runtime/public_scan_file_hashes.csv').open(encoding='utf-8-sig')))
exempt={'FILE_MANIFEST.csv','runtime/public_privacy_scan.csv','runtime/public_privacy_scan.json'}
assert {p.relative_to(stage).as_posix() for p in files}-exempt=={r['path'] for r in bound},'Stage changed after privacy scan'
for r in bound:assert hashlib.sha256((stage/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
with (stage/'FILE_MANIFEST.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
 for p in files:
  if p.name!='FILE_MANIFEST.csv':w.writerow({'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
groups={'01_reports_manuscripts':[],'02_models_code':[]}
for p in files:
 rel=p.relative_to(stage)
 groups['02_models_code' if rel.parts[0] in {'models','code'} else '01_reports_manuscripts'].append(p)
manifest=[]
def pack(group,items,part):
 name=f'{group}_{part:02}.zip';p=stage/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
  for f in items:z.write(f,f.relative_to(stage).as_posix())
 if p.stat().st_size>25_000_000:
  # 只移除本脚本刚产生的超限临时包，原始文件与旧发布包不动。
  p.unlink();assert len(items)>1,'An individual evidence file exceeds the package limit'
  mid=len(items)//2;nextpart=pack(group,items[:mid],part);return pack(group,items[mid:],nextpart)
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  names=z.namelist();assert len(names)==len(set(names))==len(items)
  for f in items:assert hashlib.sha256(z.read(f.relative_to(stage).as_posix())).digest()==hashlib.sha256(f.read_bytes()).digest()
 manifest.append({'path':name,'bytes':p.stat().st_size,'files':len(items),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'CRC':'PASS','extraction_hashes':'PASS'})
 return part+1
for name,items in groups.items():
 if items:pack(name,items,1)
out={'limit_bytes':25_000_000,'packages':manifest,'microdata_included':False}
(stage/'PACKAGE_MANIFEST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
(root/'runtime/package_validation.json').write_text(json.dumps({'status':'PASS',**out},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False))
