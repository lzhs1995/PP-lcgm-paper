"""公开证据允许清单与本机已知标识扫描；只生成本批新发布目录。"""
from pathlib import Path
import json,csv,hashlib,shutil,zipfile,re
from lxml import etree as E
import fitz
R=Path('C:/Users/LZHS/pp_lgcm_review/round2C_20261007');B=R.parent/'round2B_20261006';S=R/'public_stage'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,rel=None):
 dest=S/(rel or p.relative_to(R));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
def main():
 assert json.loads((R/'DELIVERY_SCOPE.json').read_text())['ready_for_publication']
 visual=json.loads((R/'manuscript/visual_review.json').read_text());assert visual['status']=='PASS'
 exported=json.loads((R/'manuscript/native_word_export.json').read_text())
 assert len(exported)==2
 vmap={x['pdf']:x for x in visual['files']}
 assert set(vmap)=={x['pdf'] for x in exported}
 for x in exported:
  assert sha(R/'manuscript'/x['document'])==x['docx_sha256']
  assert sha(R/'manuscript'/x['pdf'])==x['pdf_sha256']==vmap[x['pdf']]['sha256']
  assert vmap[x['pdf']]['reviewed_pages']==x['pages']
 assert not S.exists(),'Stage already exists: review and use a new build directory rather than silently mixing files'
 S.mkdir()
 for folder in ['code','vendor','audit','evidence','results','figures']:
  for p in (R/folder).rglob('*'):
   if p.is_file() and p.suffix.lower() in {'.r','.py','.csv','.json','.md','.pdf'}:copy(p)
 for folder in (R/'models').glob('*/*'):
  if not folder.is_dir():continue
  for p in folder.iterdir():
   if p.is_file() and p.suffix.lower() in {'.inp','.out','.csv','.json','.log'}:
    copy(p)
    if p.suffix in {'.inp','.out'}:copy(p,Path(str(p.relative_to(R))+'.txt'))
  # 仅这两个SAVEDATA文件是参数级聚合结果；data.dat等逐人数据绝不复制或改名。
  for name in ['estimates.dat','tech3.dat']:
   p=folder/name
   if p.exists():copy(p,Path(str(p.relative_to(R))+'.txt'))
 for p in (R/'manuscript').rglob('*'):
  if p.is_file() and p.suffix in {'.docx','.pdf','.json','.md','.csv'}:copy(p)
 for p in (R/'readable').rglob('*.md'):copy(p)
 for name in ['REPORT.md','README.md','FOR_WEB_REVIEWERS.md','MODEL_INDEX.md','SEVEN_ISSUES.csv','DELIVERY_SCOPE.json','RUN_CONTRACT.json']:copy(R/name)
 provenance=[]
 for rel in ['audit/observed_longitudinal_descriptives.csv','audit/main_controls.csv','audit/mi_engineering_acceptance.json','audit/mi_member_manifest.json','audit/source_contract.json','audit/clustered_shape_comparison.csv','audit/target_parent_contract.json','code/04_hierarchical_mi.R','code/mi_validation.R','code/05_target_parent.R']:
  p=B/rel;copy(p,Path('provenance_round2B')/rel);provenance.append({'source_commit':'a666e0ea8a610159709bb504d3d275f6f582efb9','path':rel,'sha256':sha(p)})
 (S/'provenance_round2B/binding.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf8')
 # 此私有文件仅在本机用于匹配，绝不复制到公开目录。
 ids=set(json.loads((B/'private/identifier_tokens.json').read_text(encoding='utf8')))
 checks=[]
 for p in sorted(x for x in S.rglob('*') if x.is_file()):
  ext=p.suffix.lower();assert ext not in {'.dat','.dta','.rds','.rdata','.gh5'}
  if ext=='.docx':
   with zipfile.ZipFile(p) as z:text='\n'.join(''.join(E.fromstring(z.read(n)).itertext()) for n in z.namelist() if n.endswith('.xml'))
  elif ext=='.pdf':
   with fitz.open(p) as doc:text='\n'.join(pg.get_text() for pg in doc)
  else:text=p.read_text(encoding='utf-8-sig')
  tokens=set(re.findall(r'(?<![\w.])[0-9]{5,14}(?![\w.])',text))
  checks.append({'path':p.relative_to(S).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size,'potential_identifier_matches':len(tokens&ids)})
 bad=[x for x in checks if x['potential_identifier_matches']]
 result={'status':'PASS' if not bad else 'REQUIRES_LOCAL_REVIEW','files':len(checks),'matching_files':len(bad),'forbidden_extensions':0,'limitations':'Known exact numeric identifier scan and explicit file allowlist; no claim of arbitrary microdata deidentification; document images require provenance and visual review'}
 (R/'runtime/public_privacy_scan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 with (R/'runtime/public_scan_file_hashes.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
 assert not bad,[(x['path'],x['potential_identifier_matches']) for x in bad]
 copy(R/'runtime/public_privacy_scan.json');copy(R/'runtime/public_scan_file_hashes.csv')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
