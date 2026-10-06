"""汇总最终版本的真实回执；不重估模型，不跨版本继承NLM通过状态。"""
from review_workspace import OUT, PROJECT, readj, writej, sha
from pathlib import Path
from datetime import datetime, timezone
import csv, re, fitz

stamp = datetime.now(timezone.utc).isoformat()
root = OUT / 'reviews'
manifest = readj(root / 'v45_v38/source_manifest.json')
expected = {s['id'] for s in manifest['sources']}
assert len(expected) == 2
assert all(sha(s['path']) == s['sha256'] for s in manifest['sources'])
manual = readj(root / 'v45_v38/adjudication.json')
assert manual['notebook_id'] == manifest['notebook_id']
passes = []
for n in [1, 2, 3]:
    path = root / f'v45_v38/pass{n}_full_concise/result.json'
    result = readj(path)
    attempt = result['attempts'][-1]
    validation = attempt.get('validation', {})
    raw = readj(attempt['raw_path'])
    refs = set((raw.get('citations') or {}).values())
    transport_pass = result['status'] == 'PASS' and attempt['exit_code'] == 0
    source_pass = expected.issubset(set(raw.get('sources_used', []))) and expected.issubset(refs)
    findings = validation.get('new_issues_count')
    items = [x for x in manual['items'] if x['pass'] == n]
    assert findings is not None, (n, 'missing findings count')
    assert len(items) == findings, (n, '每项NLM问题必须有人工裁定')
    resolved = all(x['disposition'] in ['REJECT_WITH_EVIDENCE', 'FIXED_AND_REVIEWED'] for x in items)
    passes.append({'pass': n, 'scope': ['全文结构与数值', '全文方法与解释', '全文格式与一致性'][n-1], 'transport_status': result['status'], 'exit_code': attempt['exit_code'], 'both_sources_verified': source_pass, 'new_issues_count': findings, 'a5_no_new_issues': validation.get('a5_no_new_issues'), 'all_findings_disposed': resolved, 'review_complete': transport_pass and source_pass and resolved, 'result': str(path), 'raw_path': attempt['raw_path'], 'raw_sha256': sha(attempt['raw_path']), 'request_fingerprint': result['request_fingerprint']})
done = all(p['review_complete'] for p in passes)
disposition = {'updated_at_utc': stamp, 'final_source_manifest': manifest, 'passes': passes, 'adjudication': manual, 'historical_dispositions': [str(root / 'v43_disposition.md'), str(root / 'v44_disposition.md')], 'three_pass_review_completed': done, 'exhaustive_page_by_page_accuracy_claimed': False, 'scientific_release': False, 'limitations': ['NLM检索式审阅及本地验证不等于保证全文不存在错误。', 'CESD8五期直接基准不可接受；MI精确配对、合并推断及协方差问题仍开放。', '审阅通过不改变历史复现已完成、CHARLS暂停及禁止据显著性改规格的边界。']}
writej(root / 'review_disposition.json', disposition)

# 复核最终文件和既有修订是否实际进入PDF。
pdf_receipt = readj(OUT / 'manuscript/final_pdf_receipt.json')
norm = lambda s: re.sub(r'\s+', '', s).replace('\u2212', '-').replace('\u2013', '-')
changes = list(csv.DictReader((OUT / 'manuscript/change_log.csv').open(encoding='utf-8-sig')))
pdf_checks = []
for i, row in enumerate(pdf_receipt['records']):
    assert sha(row['docx']) == row['docx_sha256']
    assert sha(row['pdf']) == row['pdf_sha256']
    with fitz.open(row['pdf']) as f:
        text = norm('\n'.join(p.get_text() for p in f))
    if i == 0:
        for c in changes:
            if c['new']:
                pdf_checks.append({'document': i, 'type': 'retained_v43_edit', 'paragraph': c['paragraph_index'], 'pass': norm(c['new']) in text})
        for c in readj(OUT / 'manuscript/v44_pdf_receipt.json')['checks']:
            pdf_checks.append({'document': i, 'type': 'v44_edit', 'text': c['text'], 'pass': norm(c['text']) in text})
    else:
        for marker in ['补表R1', '补表R2', '补表R3', '-0.427', '-0.440', '-0.743']:
            pdf_checks.append({'document': i, 'type': 'retained_supplement', 'text': marker, 'pass': norm(marker) in text})
assert all(r['pass'] for r in pdf_checks)
pdf_checks.extend(pdf_receipt['checks'])
assert all(r['pass'] for r in pdf_checks)
baseline = [{'path': row['path'], 'unchanged': sha(row['path']) == row['sha256']} for row in readj(OUT / 'baseline_manifest.json')['files']]
assert all(r['unchanged'] for r in baseline)
package = OUT / 'LGCM_audit_stage1_20261005.zip'
assert sha(package) == '6f855e2db2bbe4189907385636717a8624e859193a188371896f4cd82f9fa8ea'
skill_rel = Path('skills/mplusautomation-guide/references/cfps-review-scale-and-sensitivity.md')
repo = PROJECT / 'work/clauder-rstudio-workbench_repo_20261004'
shared = Path(r'C:\Users\LZHS\.agents') / skill_rel
assert sha(repo / skill_rel) == sha(shared)
writej(OUT / 'final_delivery_validation.json', {'status': 'PASS', 'updated_at_utc': stamp, 'baseline': baseline, 'pdf_checks': pdf_checks, 'final_documents': pdf_receipt['records'], 'zip_sha256': sha(package), 'skill_reference_sha256': sha(shared), 'skill_local_commits': ['5641f4e', '87b284d'], 'three_pass_review_completed': done, 'scientific_release': False})
state = readj(OUT / 'state.json')
state.update(stage='REVIEW_DELIVERY_COMPLETE_SCIENTIFIC_INFERENCE_OPEN' if done else 'FINAL_PDF_READY_REVIEW_INCOMPLETE', updated_at=stamp, main_version='v45', appendix_version='v38', nlm_three_pass_completed=done, nlm_notebook_id=manifest['notebook_id'], manuscript_release=False, source_files_unchanged=True, continuation_new_mplus=0)
writej(OUT / 'state.json', state)
print('FINAL_DELIVERY_VALIDATION_PASS', 'NLM_THREE_PASS', done, 'BASELINES', len(baseline), 'PDF_CHECKS', len(pdf_checks), flush=True)
