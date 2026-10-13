"""白名单整理收尾交付；复用既有隐私扫描，确定性分包并逐载荷验证。"""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,shutil,zipfile
import privacy_scan
import publication_gate
import public_file_selection
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'public_stage';LIMIT=25_000_000
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 publication_gate.check(ROOT)
 assert read(ROOT/'CLOSEOUT_RECEIPT.json')['status']=='SCOPED_CLOSEOUT_COMPLETE'
 assert read(ROOT/'manuscript/delivery/manuscript_validation.json')['status']=='PASS'
 assert read(ROOT/'manuscript/delivery/visual_review.json')['status']=='PASS'
 assert read(ROOT/'reports/EVIDENCE_VERIFICATION.json')['status']=='PASS'
 if STAGE.exists():
  dest=ROOT/'runtime/stage_archives'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f');dest.parent.mkdir(parents=True,exist_ok=True);STAGE.rename(dest)
 STAGE.mkdir();pairs=public_file_selection.selected(ROOT)
 for p in pairs:
  dest=STAGE/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p)
  if dest.suffix=='.out':dest.with_suffix('.out.txt').write_bytes(dest.read_bytes())
 (STAGE/'.gitattributes').write_bytes(b'* -text\n')
 privacy_scan.scan(STAGE)
 records=[dict(path=p.relative_to(STAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(STAGE.rglob('*')) if p.is_file()]
 with (STAGE/'FILE_MANIFEST.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(records)
 payload=[r['path'] for r in records]+['FILE_MANIFEST.csv']
 # 先按未压缩大小20MB分组，保证每包低于25MB；巨大单文件则明确报错。
 groups=[];group=[];size=0
 for name in payload:
  n=(STAGE/name).stat().st_size;assert n<LIMIT,name
  if group and size+n>20_000_000:groups.append(group);group=[];size=0
  group.append(name);size+=n
 if group:groups.append(group)
 packages=[];seen=set()
 for j,names in enumerate(groups,1):
  path=STAGE/f'PP_LGCM_Final_Closeout_Package_{j:02d}.zip'
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for name in names:
    zi=zipfile.ZipInfo(name,(2026,10,12,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;z.writestr(zi,(STAGE/name).read_bytes())
  assert path.stat().st_size<=LIMIT
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None
   for name in z.namelist():
    assert name not in seen;seen.add(name)
    assert hashlib.sha256(z.read(name)).hexdigest()==sha(STAGE/name)
  packages.append(dict(path=path.name,bytes=path.stat().st_size,files=len(names),sha256=sha(path)))
 assert seen==set(payload)
 manifest=dict(release='final_closeout_after_Round2F',max_package_bytes=LIMIT,packages=packages,payload_files=len(payload),manifest_entries=len(records),new_mplus_calls=0)
 dump(STAGE/'PACKAGE_MANIFEST.json',manifest)
 dump(ROOT/'runtime/package_validation.json',dict(status='PASS',stage=str(STAGE),package_manifest_sha256=sha(STAGE/'PACKAGE_MANIFEST.json'),**manifest))
 print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
