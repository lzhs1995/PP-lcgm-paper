"""只读核对审稿意见点名的DOI元数据；不更新Zotero或伪称阅读全文。"""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import json
import requests

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
DEST = ROOT/"audit/citation_metadata_checks"
DEST.mkdir(exist_ok=True)
DOIS = ["10.1017/S0144686X24000795", "10.1093/sf/soaf214", "10.1017/S0144686X21000283",
        "10.18637/jss.v045.i03", "10.1177/0962280214521348"]

def fetch(doi):
    file = DEST/(doi.rsplit("/", 1)[1]+".json")
    if file.exists():
        return json.loads(file.read_text(encoding="utf-8"))
    url = "https://api.crossref.org/works/"+quote(doi, safe="")
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=(15, 40))
    response.raise_for_status()
    data = response.json()["message"]
    result = dict(doi=doi, retrieved_at=datetime.now(timezone.utc).isoformat(), url=url,
        scope="Publisher-deposited metadata only; no full-text verification", metadata=data)
    file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        for item in pool.map(fetch, DOIS):
            d = item["metadata"]
            print(json.dumps(dict(doi=item["doi"], title=d.get("title"), author=d.get("author"),
                published=d.get("published"), abstract=d.get("abstract")), ensure_ascii=False))
