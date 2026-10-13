"""白名单整理终态聚合证据，并扫描真实队列标识和凭据；不发布微观数据。"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,hashlib,re,shutil,zipfile
import fitz

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'.md','.json','.csv','.txt','.r','.py','.ps1','.inp','.out','.dat','.log','.pdf','.docx'}
MODEL_NAMES={'model.inp','model.out','estimates.dat','tech3.dat','receipt.json','engine_receipt.json','engine_console.log',
 'input_contract.json','key_paths.csv','parameters_high_precision.csv','parameter_covariance.csv','start_mapping.csv',
 'tech1_parameter_map.csv','matrix_values.csv','gate.json','process.json','resource_before.json','engine_progress.json','not_run.json',
 'keep_awake_release.json','suspend_gaps.json','mplus_console.log'}
TOKEN=re.compile(r'(?<![\w.+\-])\d{5,12}(?![\w.])')
SECRET=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sources():
 pairs=[]
 def add(p,target=None):
  assert p.is_file() and p.name.lower()!='data.dat'
  assert p.suffix.lower()!='.dat' or p.name in {'estimates.dat','tech3.dat'}
  pairs.append((p,target or p.relative_to(ROOT).as_posix()))
 for p in (ROOT/'reports').iterdir():
  if p.is_file() and p.suffix.lower() in ALLOWED:add(p,p.name)
 for folder in ['code','contracts','results','upstream','baseline','sources']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and p.suffix.lower() in ALLOWED and not any(x in ['__pycache__','private','literature_private'] for x in p.parts):add(p)
 for p in (ROOT/'audit').rglob('*'):
  if p.is_file() and p.suffix.lower() in ALLOWED and '__pycache__' not in p.parts:add(p)
 for p in (ROOT/'reporting').iterdir():
  if p.is_file() and p.suffix.lower() in {'.py','.ps1'}:add(p)
 # 只发布开发测试源码；假引擎生成的模型目录不是实证调用。
 for name in ['test_consensus.R','test_engine.py','freeze.R','implement_consensus.py','README.md']:
  add(ROOT/'development'/name)
 for p in (ROOT/'manuscript/delivery').iterdir():
  if p.is_file() and p.suffix.lower() in ALLOWED:add(p,'manuscripts/'+p.name)
 for name in ['edits_static.json','edits_applied.json']:
  add(ROOT/'manuscript'/name,'manuscript_sources/'+name)
 add(ROOT/'manuscript/working/main/paragraph_024.xml','manuscript_sources/paragraph_024.xml.txt')
 for d in (ROOT/'models').iterdir():
  if not d.is_dir():continue
  for p in d.iterdir():
   if p.is_file() and p.name in MODEL_NAMES:add(p)
 for p in (ROOT/'runtime').glob('native_*.json'):add(p)
 for name in ['selection_2f.json','progress.json','budget_status.json','batch_window.json']:
  add(ROOT/'runtime'/name)
 assert len(pairs)==len({t for _,t in pairs})
 return pairs
def parts(p):
 if p.suffix.lower()=='.docx':
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   assert not any('/embeddings/' in n or 'vbaProject' in n for n in z.namelist())
   for n in z.namelist():
    if n.endswith(('.xml','.rels')):yield n,z.read(n).decode('utf-8',errors='replace')
 elif p.suffix.lower()=='.pdf':
  with fitz.open(p) as pdf:
   assert pdf.embfile_count()==0
   for i,page in enumerate(pdf):yield f'page_{i+1}',page.get_text()
 else:yield 'text',p.read_text(encoding='utf-8-sig',errors='replace')
def scan(stage):
 # 先核验逐文件授权，再运行补充标识/凭据扫描；黑名单不是微观数据分类器。
 import public_file_selection
 public_file_selection.verify_stage(stage)
 identity=ROOT.parent/'round2D_20261008/private/privacy_scan_identifiers.json'
 identifiers=set(read(identity)['identifiers']);hits=[];bad=[];inventory=[]
 for p in sorted(stage.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(stage).as_posix()
  if p.name!='.gitattributes' and p.suffix.lower() not in ALLOWED:bad.append(rel)
  if any(x in ['private','__pycache__','literature_private'] for x in p.relative_to(stage).parts):bad.append(rel)
  if p.suffix.lower()=='.dat' and p.name not in ['estimates.dat','tech3.dat']:bad.append(rel)
  if p.suffix.lower()=='.csv':
   with p.open(encoding='utf-8-sig',newline='') as f:header=next(csv.reader(f),[])
   if set(x.strip().lower() for x in header)&{'pid','fid','person_id','household_id'}:bad.append(rel)
  for part,txt in parts(p):
   values=set(TOKEN.findall(txt))&identifiers;keys=SECRET.findall(txt)
   if values or keys:hits.append(dict(path=rel,part=part,identifier_values=sorted(values),credential_hits=keys))
  inventory.append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p)))
 dump(ROOT/'private/public_scan_hits.json',hits)
 result=dict(status='PASS' if not hits and not bad else 'FAIL',files_scanned=len(inventory),
  exact_identifier_hit_parts=len(hits),prohibited_file_or_column_hits=len(bad),identifier_tokens_checked=len(identifiers),
  identifier_source_sha256=sha(identity),public_microdata=False,preview=False,
  exclusions=['participant records','raw data.dat','MI and score objects','article fulltexts','runtime databases','Office embedded objects'],
  procedure='Aggregate whitelist + exact cohort identifiers + credential signatures; DOCX XML/relationships and PDF text/attachments scanned.',
  created_utc=datetime.now(timezone.utc).isoformat())
 dump(ROOT/'runtime/public_privacy_scan.json',result);print(json.dumps(result),flush=True)
 assert not hits and not bad,'Publication scan failed; details remain private'
 dump(stage/'audit/public_privacy_scan.json',result)
 with (ROOT/'runtime/public_scan_file_hashes.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(inventory)
def main():
 assert read(ROOT/'runtime/selection_2f.json')['terminal']['status'] in ['FINISHED','STOPPED_WITH_REASON']
 assert read(ROOT/'audit/independent/independent_verification.json')['status']=='PASS'
 assert read(ROOT/'audit/workbench_completion.json')['decision']=='PASS'
 assert read(ROOT/'manuscript/delivery/manuscript_validation.json')['status']=='PASS'
 assert read(ROOT/'manuscript/delivery/visual_review.json')['status']=='PASS'
 assert read(ROOT/'reports/DELIVERY_SCOPE.json')['ready_for_publication']
 for f,h in read(ROOT/'contracts/FROZEN_CODE_2F.json').items():assert sha(ROOT/'code'/f)==h
 stage=ROOT/'public_stage'
 if stage.exists():
  archive=ROOT/'runtime/stage_archives'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
  archive.parent.mkdir(parents=True,exist_ok=True);stage.rename(archive)
 stage.mkdir()
 for p,name in sources():
  target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);assert sha(p)==sha(target)
  if target.suffix in ['.inp','.out']:target.with_suffix(target.suffix+'.txt').write_bytes(target.read_bytes())
 (stage/'.gitattributes').write_bytes(b'* -text\n')
 scan(stage);print('PUBLIC_STAGE_READY',stage,flush=True)
if __name__=='__main__':main()
