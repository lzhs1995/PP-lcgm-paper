"""独立核对阶段收口、真实调用、延期位置与耗时；无需个人数据。"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.DictReader(handle))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_source(root,value):
    # 原Windows控制合同保留原字节；云端按相同相对路径读取，不依赖宿主分隔符。
    path=PurePosixPath(str(value).replace('\\','/'))
    assert not path.is_absolute() and '..' not in path.parts and ':' not in str(path)
    return root.joinpath(*path.parts)


def verify(root):
    audit=root/'audit/stage_closeout_20261009'
    reports=root if (root/'MODEL_EXECUTION.csv').exists() else root/'reports_final'
    closure=read(audit/'closeout_contract.json')
    terminal=read(root/'runtime/queue_terminal.json')
    evidence=read(audit/'stage_evidence.json')
    processes=read(audit/'terminal_process_validation.json')
    waiting=read(audit/'waiting_jobs_stopped.json')
    assert terminal['status']=='QUEUE_TERMINAL'
    assert terminal['reason']=='USER_APPROVED_STAGE_BUDGET_STOP'
    assert terminal['original_registered_queue_completed'] is False
    assert terminal['original_168_hour_budget_exhausted'] is False
    assert terminal['all_registered_calls_terminal'] is True
    assert closure['new_formal_model_calls_allowed']==closure['new_performance_probe_calls_allowed']==0
    assert processes['status']==waiting['status']=='PASS'
    assert all(not v['alive'] for v in waiting['jobs'].values())
    assert processes['owned_processes_exited'] and processes['all_registered_receipts_verified']
    assert sha(root/'audit/CALL_REGISTER.csv')==closure['initial_call_register_sha256']
    assert sha(audit/'closeout_contract.json')==terminal['closeout_contract_sha256']
    assert sha(root/'runtime/queue_terminal.json')==evidence['queue_terminal_sha256']==processes['terminal_sha256']
    assert sha(root/'evidence/independent_verification.json')==evidence['independent_evidence_sha256']
    calls=rows(root/'audit/CALL_REGISTER.csv')
    report=rows(reports/'MODEL_EXECUTION.csv')
    timings=rows(reports/'PERFORMANCE_FINAL.csv')
    assert {r['id'] for r in calls}=={r['id'] for r in report}=={r['id'] for r in timings}
    assert len(calls)==len(report)==len(timings)==terminal['call_count']==evidence['actual_calls']
    original_inputs=[]
    for c in calls:
        rec=next(r for r in report if r['id']==c['id'])
        timing=next(r for r in timings if r['id']==c['id'])
        folder=root/rec['directory']
        receipt=read(folder/'receipt.json')
        assert receipt['id']==c['id']
        assert receipt['status']==rec['status']==timing['status']
        assert sha(folder/'model.inp')==c['input_sha256']
        assert sha(folder/'model.out')==receipt['output_sha256']==rec['output_sha256']
        assert math.isclose(float(receipt['seconds']),float(timing['elapsed_seconds']),rel_tol=1e-12)
        if c['category']!='SYNTHETIC':
            assert c['spec'] in {'D0','D1'} and c['attempt']!='completecase'
        original_inputs.append((c,receipt))
    assert sha(relative_source(root,closure['current_attempt_directory'])/'receipt.json')==evidence['final_receipt_sha256']
    for item in closure['unchanged_bound_sources']:
        assert sha(audit/'original_sources'/item['path'])==item['sha256']
        if item['path'] in {'RUN_CONTRACT.json','code/00_upstream_math.R','code/01_tools.R','code/03_engine.R','code/06_queue.R'}:
            assert sha(root/item['path'])==item['sha256']
    real=[(c,r) for c,r in original_inputs if c['category']!='SYNTHETIC']
    latent=[r for c,r in real if c['spec']=='D1']
    assert len(real)==evidence['real_calls'] and len(latent)==evidence['real_latent_calls']
    assert len(real)-len(latent)==evidence['real_linear_calls']
    diagnostic=rows(audit/'D0_VARIANCE_DIAGNOSTICS.csv')
    assert len(diagnostic)==6*evidence['real_linear_calls']
    assert len({(d['id'],d['factor']) for d in diagnostic})==len(diagnostic)
    for item in diagnostic:
        model=next(r for r in report if r['id']==item['id'])
        assert model['spec']=='D0' and item['output_sha256']==model['output_sha256']
        match=[p for p in rows(root/model['directory']/'parameters_high_precision.csv')
               if p['matrix'].upper()=='PSI' and p['row']==p['column']==item['factor']]
        assert len(match)==1 and match[0]['estimate']==item['estimate'] and match[0]['se']==item['se']
        assert (item['negative'].lower()=='true')==(float(item['estimate'])<0)
    assert math.isclose(sum(float(r['seconds']) for r in latent),evidence['real_latent_seconds'],rel_tol=1e-12)
    assert math.isclose(sum(float(r['seconds']) for c,r in original_inputs),evidence['all_engine_seconds'],rel_tol=1e-12)
    targets=rows(reports/'TARGET_DISPOSITIONS.csv')
    expected={(z,sp,k) for z in ('SD','SEXGAP','OLDEST','SONGAP') for sp in ('D0','D1','E0','E1') for k in range(1,11)}
    expected|={('SD','H4_'+g,k) for g in ('EDU','URBAN','INC') for k in range(1,11)}
    keys=[(t['z'],t['spec'],int(t['member'])) for t in targets]
    assert len(targets)==len(set(keys))==190 and set(keys)==expected
    for t in targets:
        matched=[c for c,r in real if c['z']==t['z'] and c['spec']==t['spec'] and c['member']==t['member']]
        assert int(t['actual_calls'])==len(matched)
        assert set(filter(None,t['attempts'].split(';')))=={c['id'] for c in matched}
        assert t['family_reportable'].lower()=='false'
        assert (t['execution_status']=='ATTEMPTED_NOT_POOLABLE')==bool(matched)
        if t['spec'].startswith(('E','H4')):
            assert t['execution_status']=='NOT_STARTED_STAGE_DEFERRED'
    summary=read(root/'results/SUMMARY.json')
    assert summary['eligible']==summary['pooled_parameter_rows']==0
    for name in ('pooled_paths.csv','conditional_slopes.csv','H4_contrasts.csv'):
        assert not rows(root/'results'/name), name
    state=rows(root/'results/family_status.csv')
    assert len(state)==19 and all(s['eligible'].upper()=='FALSE' for s in state)
    for family in state:
        if family['spec'].startswith(('E','H4')):
            assert family['status']=='NOT_RUN_BUDGET', 'Synthetic interface tests are not actual CFPS family attempts'
    assert not list((root/'audit/performance_review_20261009/calibration').glob('**/probe*receipt*'))
    assert evidence['performance_probe_calls']==evidence['observed_route_calls']==evidence['H4_calls']==0
    scope=read(reports/'DELIVERY_SCOPE.json')
    assert scope['release_type']=='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW'
    assert scope['scientific_project_complete'] is False and scope['public_microdata'] is False
    return dict(status='PASS',checked_at=datetime.now(timezone.utc).isoformat(),
                actual_calls=len(calls),real_calls=len(real),target_positions=len(targets),
                complete_interaction_MI_families=0,observed_and_H4_calls=0,performance_probe_calls=0,
                D0_variance_rows_checked=len(diagnostic),
                original_estimation_sources_unchanged=True,all_attempted_outputs_bound=True,
                scientific_project_complete=False,
                scope='Public saved artifacts and arithmetic; no microdata refit or live-process check on the reviewing host',
                verifier_sha256=sha(Path(__file__)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--evidence-output',type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.root)
    args.evidence_output.mkdir(parents=True,exist_ok=True)
    (args.evidence_output/'stage_release_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
