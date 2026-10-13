"""保存逐轮实际计数与人工裁定，旧版/误报不伪装成当前版零问题。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
path=ROOT/'reports/NLM_ADJUDICATION.json'
old=read(path)
notes={
 5:'全文已读；表4、A22及两稿原生来源齐全。未提出可定位新问题。NLM的全表一致评价不替代本地2016单元格验证。',
 6:'全文已读；共同八题、X/Y时间含义、MI与H4状态和本地稿一致。作者补入书目已经出版社记录核查。',
 7:'误报已排除：答复称Raudenbush条目串用Zhang DOI，但它自身第15条原生引用包含正确10.1177/0022427892029004001；第16条另为Zhang文献。补充PDF第31页文本/渲染及Word XML均正确。保留原始1/NO，不改稿、不改计数。',
 8:'全文已读；原文确认两条DOI各自正确，撤销上轮误报。首条路径先写-0.034又自行注正0.034；本地表4及原生引用为正0.034，这是回答转述瑕疵，不是PDF缺陷。保留原回答。',
 9:'全文已读；表4及A22引用、作者格式和两条DOI一致，无可定位新问题。回答有将调节/H4合并概括之处，稿件本身仍分别写完整MI未形成与H4未执行，不采用回答概括替换稿件。'
}
entries=[]
for n in range(5,10):
 rd=ROOT/'runtime/nlm'/f'round_{n:02d}'
 raw=read(rd/'query/attempt-01.raw.txt')
 count=int(re.search(r'NEW_ISSUES_COUNT\s*:\s*(\d+)',raw['answer']).group(1))
 marker=re.search(r'A5_NO_NEW_ISSUES\s*:\s*(YES|NO)',raw['answer']).group(1)
 assert (count,marker)==((1,'NO') if n==7 else (0,'YES'))
 entries.append(dict(round=n,status='ACCEPTED',new_issues_count=count,a5_no_new_issues=marker,
  issue_keys=['supplement_reference_Raudenbush_DOI'] if n==7 else [],adjudication=notes[n],
  disposition='FALSE_POSITIVE_NO_CHANGE' if n==7 else 'NO_ACTIONABLE_NEW_ISSUES'))
history=[]
for n in range(1,5):
 src=ROOT/'runtime/nlm'/f'round_{n:02d}'
 dst=ROOT/'reports/nlm_history'/f'round_{n:02d}';dst.mkdir(parents=True,exist_ok=True)
 for source,target in [('query/attempt-01.raw.txt','raw_response.json'),('sources.json','sources.json'),('prompt.txt','prompt.txt'),('result.json','result.json')]:
  shutil.copy2(src/source,dst/target)
 history.append(dict(round=n,raw_path=(dst/'raw_response.json').relative_to(ROOT).as_posix(),raw_sha256=sha(dst/'raw_response.json'),
  disposition='INVALID_MISSING_NATIVE_SOURCE_EVIDENCE' if n==1 else ('TWO_CONFIRMED_CITATION_REPAIRS' if n==4 else 'OLDER_PDF_VERSION_NOT_CURRENT_ACCEPTANCE')))
result=dict(status='RESOLVED',accepted_rounds=entries,previous_version_rounds=history,
 excluded_attempts=[dict(round=1,reason=old['excluded_attempts'][0]['reason'],raw_path=history[0]['raw_path'])],
 confirmed_repairs='Round4: Davey & Eggebeen双作者显示；补充Raudenbush & Chan 1992准确书目。核实缺陷与核实建议改值分开；不采纳NLM错误标题。见FINAL_CITATION_REPAIR.json。',
 network_disposition=old['network_disposition'],authority=old['authority'],updated_utc=datetime.now(timezone.utc).isoformat())
path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('ADJUDICATED current rounds 5-9; old 1-4 preserved; false positive 7 retained; A5 8-9')
