"""打包只接收逐文件批准清单；目录名和扩展名不构成发布授权。"""
from pathlib import Path
import hashlib,json
NAME='PUBLIC_FILE_SELECTION.json'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def selected(root):
 root=Path(root);j=json.loads((root/NAME).read_text(encoding='utf-8-sig'))
 assert j['status']=='APPROVED_AGGREGATE_ONLY'
 entries=j['files'];names=[r['path'] for r in entries]
 assert len(names)==len(set(names)) and NAME not in names
 paths=[]
 for row in entries:
  name=row['path'];assert not name.startswith(('/','\\')) and '\\' not in name and ':' not in name and '..' not in name.split('/')
  p=root/name;assert p.is_file() and not p.is_symlink()
  assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name
  assert row['classification'] in {'manuscript','aggregate_evidence','review_receipt','reproduction_code','handoff_report'}
  paths.append(p)
 return paths+[root/NAME]
def verify_stage(stage):
 stage=Path(stage);paths=selected(stage)
 expected={p.relative_to(stage).as_posix() for p in paths}|{'.gitattributes'}
 for p in paths:
  if p.suffix=='.out':
   alias=p.with_suffix('.out.txt');assert alias.read_bytes()==p.read_bytes()
   expected.add(alias.relative_to(stage).as_posix())
 actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
 assert actual==expected, {'unexpected':sorted(actual-expected),'missing':sorted(expected-actual)}
 return len(expected)
