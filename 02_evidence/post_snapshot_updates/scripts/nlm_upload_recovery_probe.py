"""上传TLS失败后的只读诊断；不输出代理凭证或登录数据。"""
from review_workspace import OUT, writej, sha
from pathlib import Path
from datetime import datetime, timezone
import requests, yaml, sys
sys.path.insert(0,r'C:\Users\LZHS\.agents\skills\mplusautomation-guide\scripts')
from nlm_reliability import run_list

path=Path(r'C:\Users\LZHS\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml')
config=yaml.safe_load(path.read_text(encoding='utf-8'))
rule='DOMAIN-SUFFIX,notebooklm.google.com,链式代理-Gemini'
port=config.get('mixed-port',7897)
result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'profile_sha256':sha(path),'rule_count':config.get('rules',[]).count(rule),'group_count':sum(g.get('name')=='链式代理-Gemini' for g in config.get('proxy-groups',[]))}
try:
    r=requests.get('https://notebooklm.google.com/',proxies={'http':f'http://127.0.0.1:{port}','https':f'http://127.0.0.1:{port}'},timeout=30)
    result['tls_http_status']=r.status_code
except requests.RequestException as e:
    result['tls_error_class']=type(e).__name__
result['auth']=run_list(r'C:\Users\LZHS\.local\bin\nlm.exe',profile='default')
writej(OUT/'reviews/v45_v38/upload_recovery_preflight.json',result)
print(result,flush=True)
