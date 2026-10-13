"""只读本机Clash命名管道状态；不输出凭据或完整配置。"""
from pathlib import Path
import http.client,json,yaml,os
ROOT=Path(__file__).resolve().parents[1]
c=yaml.safe_load(Path('C:/Users/LZHS/AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml').read_text(encoding='utf-8'))
live=[p for p in os.listdir('\\\\.\\pipe\\') if p.startswith('verge-mihomo-production-')]
assert len(live)==1, 'Need one unambiguous live controller pipe'
c['external-controller-pipe']='\\\\.\\pipe\\'+live[0]
class Sock:
 def __init__(self,f):self.f=f
 def makefile(self,*args,**kwargs):return self.f
def get(endpoint):
 with open(c['external-controller-pipe'],'r+b',buffering=0) as f:
  req='GET '+endpoint+' HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\nAuthorization: Bearer '+str(c.get('secret',''))+'\r\n\r\n'
  f.write(req.encode());r=http.client.HTTPResponse(Sock(f));r.begin();data=r.read()
  assert r.status==200, r.status
  return json.loads(data)
proxies=get('/proxies')['proxies'];target=proxies.get('链式代理-Gemini',{})
items=[]
todo=['链式代理-Gemini'];seen=set()
while todo:
 n=todo.pop(0)
 if n in seen:continue
 seen.add(n);v=proxies.get(n,{})
 items.append({k:v[k] for k in ['name','type','now','alive'] if k in v})
 if v.get('now'):todo.append(v['now'])
 if v.get('type')=='Relay':todo+=v.get('all',[])
connections=get('/connections').get('connections',[])
matched=[{'host':r.get('metadata',{}).get('host'),'rule':r.get('rule'),'rulePayload':r.get('rulePayload'),'chains':r.get('chains')} for r in connections if 'notebooklm' in r.get('metadata',{}).get('host','')]
result={'status':'READ_ONLY_PROBE','route':items,'notebooklm_connections':matched,'config_modified':False}
(ROOT/'runtime/nlm/network_diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
