"""下载公开Mplus方法页面至非公开runtime；只保存来源索引到审计包。"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import argparse
import hashlib
import json
import re
import requests
from bs4 import BeautifulSoup

ROOT = Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008')
DEST = ROOT/'runtime/performance_sources_20261009'
INDEX = ROOT/'audit/performance_review_20261009/web_sources.json'

def fetch(item):
    key, url = item
    record = dict(key=key,requested_url=url,retrieved_at=datetime.now(timezone.utc).isoformat())
    try:
        r=requests.get(url,timeout=(8,22),headers={'User-Agent':'Mozilla/5.0 (compatible; Academic-methods-review/1.0)'})
        record.update(url=r.url,status_code=r.status_code,bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest())
        (DEST/(key+'.html')).write_bytes(r.content)
        is_xml=r.content.lstrip().startswith(b'<?xml')
        soup=BeautifulSoup(r.content,'xml' if is_xml else 'html.parser')
        for tag in soup(['script','style','noscript']):
            tag.decompose()
        text=re.sub(r'[ \t]+',' ',soup.get_text('\n',strip=True))
        (DEST/(key+'.txt')).write_text(text,encoding='utf-8')
        record['title']=soup.title.get_text(' ',strip=True) if soup.title else ''
        links=[dict(text=a.get_text(' ',strip=True),href=urljoin(r.url,a.get('href'))) for a in soup.find_all('a',href=True)
            if a.get_text(' ',strip=True)]
        if is_xml:
            links.extend(dict(text=x.title.get_text(),href=x.link.get_text()) for x in soup.find_all('item') if x.title and x.link)
        (DEST/(key+'_links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
        record['links_count']=len(links)
        selected=[x for x in links if re.search('integrat|slow|process|parallel|speed|comput|algorithm|EM\\b|start',x['text'],re.I)]
        print(json.dumps(dict(**record,selected_links=selected[:35]),ensure_ascii=False),flush=True)
    except Exception as e:
        record['error']=str(e)
        print(json.dumps(record,ensure_ascii=False),flush=True)
    return record

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('sources',nargs='+',help='name=https://...')
    args=parser.parse_args()
    sources=[x.split('=',1) for x in args.sources]
    assert all(re.fullmatch(r'[a-zA-Z0-9_-]+',k) and urlparse(u).scheme=='https' for k,u in sources)
    DEST.mkdir(exist_ok=True,parents=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        records=list(ex.map(fetch,sources))
    old=json.loads(INDEX.read_text(encoding='utf-8')) if INDEX.exists() else []
    old.extend({k:v for k,v in r.items() if k!='links'} for r in records)
    INDEX.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
