"""独立核对公开文件、独立压缩包和相对链接；不读取微观数据。"""
from pathlib import Path
import csv, hashlib, json, re, zipfile
from urllib.parse import unquote, urlsplit

ROOT = Path(r'C:\Users\LZHS\pp_lgcm_review\round2_20261006')
REPO = Path(r'C:\Users\LZHS\Desktop\cnm\tasks\01_R_analysis\work\cfps_review_20261005\github_publish')
PUB = REPO / 'round2_20261006'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    manifest = list(csv.DictReader((PUB / 'PUBLICATION_MANIFEST.csv').open(encoding='utf-8')))
    for row in manifest:
        data = (PUB / row['path']).read_bytes()
        assert len(data) == int(row['bytes']), row['path']
        assert sha(data) == row['sha256'], row['path']
    actual = {p.relative_to(PUB).as_posix() for p in PUB.rglob('*') if p.is_file()}
    assert actual == {r['path'] for r in manifest} | {'PUBLICATION_MANIFEST.csv'}
    pkgs = json.loads((PUB / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['packages']
    archived = set()
    for p in pkgs:
        path = PUB / p['path']
        assert path.stat().st_size == p['bytes'] <= 25_000_000
        assert sha(path.read_bytes()) == p['sha256']
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            assert len(z.namelist()) == p['files']
            for name in z.namelist():
                assert not name.startswith('/') and '..' not in Path(name).parts
                assert name not in archived, name
                assert z.read(name) == (PUB / name).read_bytes(), name
                archived.add(name)
    excluded = {'PACKAGE_MANIFEST.json', 'PUBLICATION_MANIFEST.csv'} | {p['path'] for p in pkgs}
    assert archived == actual - excluded
    banned = {'.dat', '.rds', '.dta', '.sav', '.rdata', '.gh5', '.fscores'}
    assert not [p for p in actual if Path(p).suffix.lower() in banned]
    checked_links = 0
    # 可读页面原文可能包含文献括号；只检查我们生成的导航与索引。
    docs = [PUB / f for f in ['README.md','REPORT.md','EVIDENCE_INDEX.md','MODEL_INDEX.md','FOR_CHATGPT.md']]
    docs += list((PUB / 'models').rglob('KEY_OUTPUT.md'))
    for p in docs:
        for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            u = urlsplit(ref)
            if u.scheme or ref.startswith('#'):
                continue
            target = (p.parent / unquote(u.path)).resolve()
            assert target.is_relative_to(REPO.resolve()) and target.exists(), (p, ref)
            checked_links += 1
    result = {'status':'PASS','public_files':len(actual),'manifest_verified':len(manifest),
              'zip_content_files_verified':len(archived),'relative_links_checked':checked_links,
              'packages':pkgs,'scientific_release':False}
    (ROOT / 'runtime/publication_local_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
