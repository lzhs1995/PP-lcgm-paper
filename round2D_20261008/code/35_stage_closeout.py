"""Round2D阶段收口：接管下一模型准入；不启动Mplus，不改估计合同。"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil

import psutil

ROOT = Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008')
AUDIT = ROOT / 'audit/stage_closeout_20261009'
RUNTIME = ROOT / 'runtime/stage_closeout_20261009'
HOLD = ROOT / 'runtime/PAUSE_FOR_CODE_UPDATE'
CURRENT = ROOT / 'models/SONGAP/D1_Z0_MI01/repair_start'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.stage-tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def identity(pid, created):
    try:
        process = psutil.Process(int(pid))
        if abs(process.create_time() - created) > 0.1:
            return None
        return process
    except psutil.NoSuchProcess:
        return None


def describe(process):
    return dict(pid=process.pid, created=process.create_time(), parent=process.ppid(),
                name=process.name(), children=[dict(pid=p.pid, created=p.create_time(),
                name=p.name()) for p in process.children(recursive=True)])


def prepare():
    target = AUDIT / 'closeout_contract.json'
    if target.exists():
        contract = read(target)
        assert read(HOLD)['purpose'] == contract['purpose'], 'Do not overwrite another hold'
        print('ALREADY_PREPARED; hold remains active')
        return
    AUDIT.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    binding = read(ROOT / 'runtime/postqueue_launch_contract.json')
    old_hold = read(HOLD)
    assert old_hold['purpose'] == 'six_registered_short_performance_probes'
    original = identity(binding['upstream_worker_pid'], binding['upstream_worker_created'])
    calibration = identity(old_hold['pid'], old_hold['created'])
    post_state = read(ROOT / 'runtime/postqueue/state.json')
    post = psutil.Process(post_state['pid'])
    assert original and calibration
    assert post_state['stage'] == 'waiting_original_queue'
    assert all(p.ppid() == original.ppid() for p in (calibration, post))
    for p in (calibration, post):
        assert not any('mplus' in c.name().lower() for c in p.children(recursive=True))
    assert not list((ROOT / 'audit/performance_review_20261009/calibration').glob('**/*receipt*'))
    source_checks = []
    for item in binding['sources']:
        source = ROOT / item['path']
        assert sha(source) == item['sha256'], item['path']
        dest = AUDIT / 'original_sources' / item['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        source_checks.append(item)
    mp_saved = read(CURRENT / 'process.json')
    mp = psutil.Process(mp_saved['pid'])
    assert mp.ppid() == original.pid and 'mplus' in mp.name().lower()
    assert not (CURRENT / 'receipt.json').exists()
    contract = dict(
        schema_version=1, purpose='round2D_stage_release_no_further_models',
        adopted_at=now(), authorization='User approved the bounded stage-closeout plan and requested implementation',
        current_attempt='SONGAP_D1_Z0_1_repair_start',
        current_attempt_directory=str(CURRENT.relative_to(ROOT)),
        original_job='cc074578', original_process=describe(original),
        current_mplus_process=describe(mp),
        waiting_jobs={'calibration': dict(job='da892b02', process=describe(calibration)),
                      'postqueue': dict(job='36cd3ab7', process=describe(post))},
        single_attempt_limit_seconds=21600,
        latest_expected_terminal_utc=dt.datetime.fromtimestamp(mp.create_time()+21600,dt.timezone.utc).isoformat(),
        new_formal_model_calls_allowed=0, new_performance_probe_calls_allowed=0,
        deferred=['remaining latent MI and numerical checks','observed2012 E0/E1 branches',
                  'three H4 resource comparisons','complete-case latent diagnostic',
                  'window, scale, Y-shape and MI-compatibility sensitivity','six performance probes'],
        unchanged_bound_sources=source_checks,
        initial_call_register_sha256=sha(ROOT / 'audit/CALL_REGISTER.csv'),
        inference_rule='No incomplete or inadmissible MI family is pooled; an operational stop is not a null finding',
        release_type='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW')
    shutil.copy2(HOLD, RUNTIME / 'original_calibration_hold.json')
    for rel in ('runtime/postqueue/state.json','runtime/performance_calibration_20261009/state.json',
                'runtime/progress.json','audit/CALL_REGISTER.csv'):
        source = ROOT / rel
        dest = RUNTIME / 'before_takeover' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    write(target, contract)
    # 原诊断的on.exit只有内容仍等于自己的标记才会删除；原子换属避免取消时解除准入。
    assert read(HOLD) == old_hold
    write(HOLD, dict(purpose=contract['purpose'], owner='stage_closeout_20261009',
                     upstream_job_id='cc074578', adopted_at=contract['adopted_at'],
                     contract_sha256=sha(target), persistent_until_queue_exit=True))
    write(RUNTIME / 'hold_takeover_receipt.json', dict(status='HOLD_TRANSFERRED',time=now(),
          prior_owner=old_hold, current_owner=read(HOLD), current_mplus_untouched=True,
          new_Mplus_calls=0, old_bound_sources_unchanged=True))
    print(json.dumps(dict(status='HOLD_TRANSFERRED',current_mplus_untouched=True,
                         deadline_utc=contract['latest_expected_terminal_utc']),ensure_ascii=False))


def verify_waiters():
    contract = read(AUDIT / 'closeout_contract.json')
    assert read(HOLD)['purpose'] == contract['purpose']
    states = {}
    for label, value in contract['waiting_jobs'].items():
        proc = value['process']
        states[label] = dict(job=value['job'], alive=identity(proc['pid'],proc['created']) is not None)
    assert not any(x['alive'] for x in states.values()), states
    assert sha(ROOT / 'audit/CALL_REGISTER.csv') == contract['initial_call_register_sha256']
    assert not list((ROOT / 'audit/performance_review_20261009/calibration').glob('**/*receipt*'))
    write(AUDIT / 'waiting_jobs_stopped.json',dict(status='PASS',time=now(),jobs=states,
          calibration_status='DEFERRED_BEFORE_FIRST_PROBE',new_Mplus_calls=0,
          original_current_attempt_preserved=True,admission_hold_active=True))
    print(json.dumps(states))


def status():
    contract = read(AUDIT / 'closeout_contract.json')
    current = contract['current_mplus_process']
    original = contract['original_process']
    saved = read(ROOT / 'runtime/progress.json')
    result = dict(time=now(),current_attempt_terminal=(CURRENT/'receipt.json').exists(),
                  current_mplus_alive=identity(current['pid'],current['created']) is not None,
                  original_worker_alive=identity(original['pid'],original['created']) is not None,
                  original_progress=saved,hold_active=read(HOLD)['purpose']==contract['purpose'])
    result['ready_to_cancel_original_worker'] = (result['current_attempt_terminal'] and
        not result['current_mplus_alive'] and saved['stage']=='resource_wait' and result['hold_active'])
    write(RUNTIME/'latest_observation.json',result)
    print(json.dumps(result,ensure_ascii=False))


def finalize():
    contract = read(AUDIT/'closeout_contract.json')
    assert read(HOLD)['purpose']==contract['purpose']
    for saved in [contract['original_process'],contract['current_mplus_process']]+[
            v['process'] for v in contract['waiting_jobs'].values()]:
        assert identity(saved['pid'],saved['created']) is None, ('Owned process is still live',saved['pid'])
    assert (CURRENT/'receipt.json').exists(), 'Original attempt lacks a genuine terminal receipt'
    boundary = read(RUNTIME/'latest_observation.json')
    assert boundary['ready_to_cancel_original_worker'], 'Safe boundary was not verified before cancellation'
    assert (RUNTIME/'native_original_cancellation.json').exists()
    assert sha(ROOT/'audit/CALL_REGISTER.csv')==contract['initial_call_register_sha256'], 'New call was admitted'
    critical = {'RUN_CONTRACT.json','code/00_upstream_math.R','code/01_tools.R','code/03_engine.R','code/06_queue.R'}
    for item in contract['unchanged_bound_sources']:
        if item['path'] in critical:
            assert sha(ROOT/item['path'])==item['sha256'], item['path']
    with (ROOT/'audit/CALL_REGISTER.csv').open(encoding='utf-8-sig',newline='') as handle:
        calls = list(csv.DictReader(handle))
    receipts = {read(p)['id']: (p,read(p)) for p in (ROOT/'models').glob('*/*/*/receipt.json')}
    assert len(calls)==len({x['id'] for x in calls})==len(receipts)
    assert {x['id'] for x in calls}==set(receipts)
    for call in calls:
        path,receipt = receipts[call['id']]
        assert receipt['status'] not in {'RUNNING','REGISTERED'}
        assert sha(path.parent/'model.inp')==call['input_sha256']
        assert sha(path.parent/'data.dat')==call['data_sha256']
        if 'output_sha256' in receipt:
            assert sha(path.parent/'model.out')==receipt['output_sha256']
    # 当前尝试若单份通过，原队列会等待下一数值检查，尚未生成family；如实记录不完整家族。
    family_path = ROOT/'results/SONGAP_D1_family.json'
    if not family_path.exists():
        receipt = read(CURRENT/'receipt.json')
        members = [dict(member=1,status=receipt['status'],attempt=receipt['attempt'],
                        usable=receipt['usable'],output_sha256=receipt.get('output_sha256'))]
        members.extend(dict(member=k,status='NOT_RUN',attempt=None,usable=False) for k in range(2,11))
        write(family_path,dict(z='SONGAP',spec='D1',eligible=False,members=members,numeric=None,
              reason='USER_APPROVED_STAGE_BUDGET_STOP: current MI01 terminal saved; further numerical checks and MI members deferred',
              updated_at=now(),inference='Single-member status is not complete MI inference',
              generated_by='35_stage_closeout.py from actual receipts after verified queue exit'))
    families = [read(p) for p in (ROOT/'results').glob('*_family.json')]
    terminal = dict(status='QUEUE_TERMINAL',reason='USER_APPROVED_STAGE_BUDGET_STOP',
        message='按用户批准的阶段计算预算，在最后一个在途尝试终态后停止追加；原完整队列未全部执行。',
        families=len(families),eligible=sum(bool(f['eligible']) for f in families),call_count=len(calls),
        created=now(),original_registered_queue_completed=False,all_registered_calls_terminal=True,
        new_calls_since_stage_plan=0,release_type=contract['release_type'],
        model_specifications_unchanged=True,original_168_hour_budget_exhausted=False,
        note='Operational stage closure; remaining scientific questions are explicitly deferred, not null effects',
        closeout_contract_sha256=sha(AUDIT/'closeout_contract.json'))
    target = ROOT/'runtime/queue_terminal.json'
    assert not target.exists(), 'Existing terminal must be audited rather than overwritten'
    write(target,terminal)
    write(ROOT/'runtime/execution_limit.json',dict(reason=terminal['reason'],message=terminal['message'],time=now(),
          original_budget_exhausted=False,user_approved_scope_reduction=True))
    write(AUDIT/'terminal_process_validation.json',dict(status='PASS',time=now(),
        owned_processes_exited=True,all_registered_receipts_verified=True,registered_calls=len(calls),
        new_calls=0,original_estimation_code_unchanged=True,current_receipt=read(CURRENT/'receipt.json'),
        admission_hold_retained=True,terminal_sha256=sha(target)))
    print(json.dumps(terminal,ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare','verify-waiters','status','finalize'])
    args = parser.parse_args()
    {'prepare':prepare,'verify-waiters':verify_waiters,'status':status,'finalize':finalize}[args.action]()
