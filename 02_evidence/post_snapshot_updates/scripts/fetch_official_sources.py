"""下载用户指定的三份 CFPS 官方说明，保留 URL、哈希和页码文本。"""
from review_workspace import OUT, sha, writej
import requests
import fitz

sources={
 "cfps2012_cesd": "https://www.isss.pku.edu.cn/cfps/docs/20201028165326806875.pdf",
 "cfps2016_cesd": "https://www.isss.pku.edu.cn/cfps/docs/20201201085335172101.pdf",
 "cfps2018_cesd": "https://www.isss.pku.edu.cn/cfps/docs/2026-01/647fe42a94784c5cb5746b6dfb64042d.pdf",
}
rows=[]
for name,url in sources.items():
 try:
  dest=OUT/'source_evidence'/f'{name}.pdf'
  if not dest.exists():
   r=requests.get(url,timeout=25);r.raise_for_status()
   if not r.content.startswith(b'%PDF'):raise ValueError('response is not PDF')
   dest.write_bytes(r.content)
  with fitz.open(dest) as pdf:
   text='\n'.join(f'\nPAGE {i+1}\n'+p.get_text() for i,p in enumerate(pdf))
  dest.with_suffix('.txt').write_text(text,encoding='utf-8')
  rows.append({'name':name,'url':url,'status':'DOWNLOADED','sha256':sha(dest),'pdf':str(dest)})
 except Exception as exc:
  rows.append({'name':name,'url':url,'status':'FAILED','reason':str(exc)})
writej(OUT/'source_evidence/official_sources.json',rows)
print(rows)
