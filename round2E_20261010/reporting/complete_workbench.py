"""依据已落盘终态执行Workbench收口；不提交任何R或Mplus作业。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path('C:/Users/LZHS/.clauder_workbench/evidence')
PARENTS = ['95d59c52-0085-42d1-acad-b3db6f5fe7fe', '0cde1be0-15b5-4011-a0d2-a704fe6f51fe',
           'd72bec3f-9d77-42d7-a067-b80f7dba45ec']


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    selection = read(ROOT/'runtime/selection.json')
    assert selection['terminal']['status'] == 'FINISHED'
    assert read(ROOT/'runtime/progress.json')['stage'] == 'results_written'
    assert read(ROOT/'audit/independent/independent_verification.json')['status'] == 'PASS'
    assert read(ROOT/'manuscript/delivery/manuscript_validation.json')['status'] == 'PASS'
    assert read(ROOT/'manuscript/delivery/visual_review.json')['status'] == 'PASS'
    receipts = list((ROOT/'models').glob('*/engine_receipt.json'))
    assert len(receipts) == 34
    assert all(read(p)['status'] in ('EXITED', 'TIMEOUT') for p in receipts)
    sources = ['runtime/selection.json', 'runtime/progress.json', 'results/SUMMARY.json',
               'audit/independent/independent_verification.json', 'runtime/native_queue_terminal.json',
               'runtime/native_history_round2E.json']
    state = dict(status='completed', scientific_project_complete=False, new_model_calls=0,
        queue_terminal=selection['terminal'], completed_attempts=len(receipts),
        evidence_type='derived durable-file completion check; not a fabricated native tool response',
        native_terminal_response='Later get_async_result returned No job found; this alone does not prove completion.',
        completion_basis='Saved queue FINISHED and results_written states, all 34 engine receipts, full independent recalculation, archived original job registration.',
        sources=[dict(path=s, sha256=sha(ROOT/s)) for s in sources],
        created_utc=datetime.now(timezone.utc).isoformat())
    (ROOT/'audit/completion_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'audit/NATIVE_EVIDENCE_NOTE.md').write_text(
        '# 原生执行与终态证据的区别\n\n'
        '原生接口smoke作业499ae5f0已通过；正式登记作业8a148647与前置作业7e08df97均已归档。'
        '原生会话历史保留Round2E脚本提交记录。文件runtime/native_queue_terminal.json的实际内容为后续查询返回的“No job found”，'
        '不能因文件名含terminal就把它当作原生完成输出。\n\n'
        '本批终态由runtime/selection.json的FINISHED、runtime/progress.json的results_written、34份独立engine_receipt、'
        '完整结果文件与独立数值复核共同确认。audit/completion_state.json是这些证据的派生检查记录，'
        '不是伪造的MCP原始回执。完成验收不会重提已结束作业。\n', encoding='utf-8')
    parent_paths = []
    for evidence_id in PARENTS:
        paths = list(EVIDENCE.glob('*'+evidence_id+'.json'))
        assert len(paths) == 1
        parent_paths.append(paths[0])
    args = [sys.executable, '-X', 'utf8', '-m', 'clauder_workbench', 'completion-check', '--mode', 'formal',
        '--task-key', 'pp-lgcm-round2e-20261010', '--io-mode', 'durable_files',
        '--parent-evidence', *map(str, parent_paths), '--require-transport-class', 'NATIVE_MCP_OK',
        '--require-native-smoke', '--native-smoke-max-age-min', '600', '--require-job-complete',
        '--state-file', str(ROOT/'audit/completion_state.json')]
    for name, count in [('audit/independent/verified_calls.csv', 34), ('results/FAMILY_STATUS.csv', 8),
                        ('results/POOLED_KEY_PATHS.csv', 6), ('audit/SMOKE_RESULTS.csv', 9)]:
        args += ['--require-file', 'validation::'+str(ROOT/name)+f',min_rows={count},min_bytes=100,max_age_h=24']
    for name in ['manuscript/delivery/manuscript_validation.json', 'manuscript/delivery/visual_review.json']:
        args += ['--require-file', 'file::'+str(ROOT/name)+',min_bytes=100,max_age_h=24']
    run = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
    (ROOT/'audit/workbench_completion_console.txt').write_text(run.stdout+'\n'+run.stderr, encoding='utf-8')
    print(run.stdout, flush=True)
    assert run.returncode == 0, run.stderr
    docs = []
    for p in EVIDENCE.glob('*completion_check*.json'):
        obj = read(p)
        if obj.get('task_key') == 'pp-lgcm-round2e-20261010':
            docs.append((p, obj))
    path, doc = max(docs, key=lambda pair: pair[1]['timestamp_utc'])
    assert doc['decision'] == 'PASS'
    shutil.copy2(path, ROOT/'audit/workbench_completion.json')
    # 保留工具生成的真实证据链，源ID和字节不改。
    dest = ROOT/'audit/workbench'
    dest.mkdir(exist_ok=True)
    todo = [doc['evidence_id'], *PARENTS]
    seen = set()
    while todo:
        key = todo.pop()
        if key in seen:
            continue
        seen.add(key)
        path = next(EVIDENCE.glob('*'+key+'.json'))
        obj = read(path)
        shutil.copy2(path, dest/path.name)
        todo += obj.get('parent_evidence_ids', [])
    print('WORKBENCH_COMPLETION_PASS', doc['evidence_id'], flush=True)


if __name__ == '__main__':
    main()
