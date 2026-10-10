"""白名单整理Round2E聚合证据；逐人数据留在本机，源文件只读。"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import shutil
import zipfile
import fitz

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.md', '.json', '.csv', '.txt', '.r', '.py', '.ps1', '.inp', '.out', '.dat', '.log', '.pdf', '.docx'}
MODEL_NAMES = {
    'engine_console.log', 'engine_receipt.json', 'input_contract.json', 'model.inp', 'model.out',
    'mplus_console.log', 'process.json', 'receipt.json', 'resource_before.json', 'start_mapping.csv',
    'tech3.dat', 'estimates.dat', 'gate.json', 'key_paths.csv', 'matrix_values.csv',
    'parameters_high_precision.csv', 'parameter_covariance.csv', 'tech1_parameter_map.csv', 'engine_progress.json',
}
TOKEN = re.compile(r'(?<![\w.+\-])\d{5,12}(?![\w.])')
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def sources():
    pairs = []
    def add(p, target=None):
        assert p.is_file(), p
        pairs.append((p, target or p.relative_to(ROOT).as_posix()))
    for p in (ROOT/'reports').iterdir():
        if p.is_file() and p.suffix.lower() in ALLOWED:
            add(p, p.name)
    for directory in ('code', 'contracts', 'results', 'upstream', 'source_review'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and p.suffix.lower() in ALLOWED and '__pycache__' not in p.parts:
                assert p.suffix.lower() != '.dat' or p.name in {'estimates.dat', 'tech3.dat'}
                add(p)
    # 不把中间验证快照、全文文献或旧排版预览混入当前验收。
    for p in (ROOT/'audit').rglob('*'):
        rel = p.relative_to(ROOT/'audit')
        if p.is_file() and p.suffix.lower() in ALLOWED and not any(x.startswith('verification_snapshot') for x in rel.parts):
            if '__pycache__' not in rel.parts:
                add(p)
    for p in (ROOT/'reporting').iterdir():
        if p.is_file() and p.suffix.lower() in {'.py', '.ps1'}:
            add(p)
    for p in (ROOT/'reporting/context_evidence').rglob('*'):
        if p.is_file() and p.suffix.lower() in ALLOWED:
            add(p)
    for p in (ROOT/'manuscript/delivery').iterdir():
        if p.is_file() and p.suffix.lower() in ALLOWED:
            add(p, 'manuscripts/'+p.name)
    models = sorted((ROOT/'models').glob('*/receipt.json'))
    assert len(models) == 34
    for receipt in models:
        for p in receipt.parent.iterdir():
            if p.is_file() and p.name in MODEL_NAMES:
                add(p)
    for p in (ROOT/'runtime').glob('native_*.json'):
        add(p)
    for name in ('selection.json', 'budget_status.json', 'progress.json'):
        add(ROOT/'runtime'/name)
    assert len(pairs) == len({target for _, target in pairs}), 'Duplicate staging target'
    return pairs


def text_parts(p):
    if p.suffix.lower() == '.docx':
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            assert not any('/embeddings/' in n or 'vbaProject' in n for n in z.namelist()), 'Unreviewed embedded object'
            for n in z.namelist():
                if n.endswith(('.xml', '.rels')):
                    yield n, z.read(n).decode('utf-8', errors='replace')
    elif p.suffix.lower() == '.pdf':
        with fitz.open(p) as pdf:
            assert pdf.embfile_count() == 0, 'Unreviewed PDF attachment'
            for i, page in enumerate(pdf):
                yield f'page_{i+1}', page.get_text()
    else:
        yield 'text', p.read_text(encoding='utf-8-sig', errors='replace')


def scan(stage):
    # 上轮全体队列标识集合覆盖本轮复用的40份数据；数值不会写到公开报告。
    id_source = ROOT.parent/'round2D_20261008/private/privacy_scan_identifiers.json'
    identifiers = set(read(id_source)['identifiers'])
    hits, prohibited, inventory = [], [], []
    for p in sorted(stage.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(stage).as_posix()
        if any(x in {'private', 'literature_private', '__pycache__'} for x in p.relative_to(stage).parts):
            prohibited.append(rel)
        if p.name != '.gitattributes' and p.suffix.lower() not in ALLOWED:
            prohibited.append(rel)
        if p.suffix.lower() == '.dat' and p.name not in {'estimates.dat', 'tech3.dat'}:
            prohibited.append(rel)
        if p.suffix.lower() == '.csv':
            with p.open(encoding='utf-8-sig', newline='') as f:
                head = next(csv.reader(f), [])
            if set(h.lower().strip() for h in head) & {'pid', 'fid', 'person_id', 'household_id'}:
                prohibited.append(rel)
        for part, txt in text_parts(p):
            found = set(TOKEN.findall(txt)) & identifiers
            secrets = SECRET.findall(txt)
            if found or secrets:
                hits.append(dict(path=rel, part=part, identifier_values=sorted(found), credential_hits=secrets))
        inventory.append(dict(path=rel, bytes=p.stat().st_size, sha256=sha(p)))
    dump(ROOT/'private/public_scan_hits.json', hits)
    result = dict(status='PASS' if not hits and not prohibited else 'FAIL', files_scanned=len(inventory),
        exact_identifier_hit_parts=len(hits), prohibited_file_or_column_hits=len(prohibited),
        identifier_tokens_checked=len(identifiers), identifier_source_sha256=sha(id_source),
        exclusions=['participant records', 'data.dat', 'MI and score objects', 'article fulltexts', 'SQLite runtime', 'embedded office objects'],
        procedure='Explicit aggregate whitelist; exact cohort identifiers and credential signatures; DOCX XML/relationships and PDF text/attachments checked; all ZIP contents subsequently hash-bound.',
        public_microdata=False, preview=False, created_utc=datetime.now(timezone.utc).isoformat())
    dump(ROOT/'runtime/public_privacy_scan.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    assert not hits and not prohibited, 'Publication scan failed; inspect local private report'
    dump(stage/'audit/public_privacy_scan.json', result)
    with (ROOT/'runtime/public_scan_file_hashes.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['path', 'bytes', 'sha256'])
        w.writeheader(); w.writerows(inventory)


def main():
    assert read(ROOT/'runtime/selection.json')['terminal']['status'] == 'FINISHED'
    assert read(ROOT/'audit/independent/independent_verification.json')['status'] == 'PASS'
    assert read(ROOT/'audit/workbench_completion.json')['decision'] == 'PASS'
    for name, digest in read(ROOT/'contracts/FROZEN_CODE.json').items():
        assert sha(ROOT/'code'/name) == digest
    validation = read(ROOT/'manuscript/delivery/manuscript_validation.json')
    visual = read(ROOT/'manuscript/delivery/visual_review.json')
    assert validation['status'] == visual['status'] == 'PASS'
    for doc in visual['documents']:
        assert sha(ROOT/'manuscript/delivery'/doc['pdf']) == doc['pdf_sha256']
    scope = read(ROOT/'reports/DELIVERY_SCOPE.json')
    assert scope['ready_for_publication'] and not scope['preview'] and not scope['public_microdata']
    stage = ROOT/'public_stage'
    if stage.exists():
        archive = ROOT/'runtime/stage_archives'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        archive.parent.mkdir(parents=True, exist_ok=True)
        stage.rename(archive)
    stage.mkdir()
    for source, relative in sources():
        target = stage/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert sha(source) == sha(target)
        if target.suffix in {'.inp', '.out'}:
            target.with_suffix(target.suffix+'.txt').write_bytes(target.read_bytes())
    (stage/'.gitattributes').write_bytes(b'* -text\n')
    (stage/'source_review/README.md').write_text(
        '# 网页端原建议存档\n\n本目录为用户转交的原件，包括未在本机直接运行的Claude代码与云端测试。'
        '本轮实际执行版本仅见根目录code/及contracts/FROZEN_CODE.json；原建议与本机裁定见REPORT.md。'
        '云端模拟成功不计为本机Mplus成功或CFPS结论。\n', encoding='utf-8')
    scan(stage)
    print('PUBLIC_STAGE_READY', stage, flush=True)


if __name__ == '__main__':
    main()
