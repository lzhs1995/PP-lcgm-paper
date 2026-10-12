"""云端演练 r2f_engine.py（Linux，假 Mplus）：正常结束、按有效秒超时、挂起间隙登记与扣除、类别上限、
引擎预算、冻结代码与输入哈希核对、回执幂等。用法：python3 r2f_engine_mock_test.py <code_dir> <work_dir>"""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

code, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
results = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_root(name, categories=None, engine=10800):
    root = work / name
    if root.exists():
        shutil.rmtree(root)
    for d in ('code', 'contracts', 'runtime', 'models'):
        (root / d).mkdir(parents=True)
    shutil.copy(code / 'r2f_engine.py', root / 'code')
    c = json.loads((code.parent / 'contracts/RUN_CONTRACT_2F.json').read_text(encoding='utf-8'))
    if categories:
        c['budget']['categories'] = categories
    c['budget']['engine_seconds'] = engine
    (root / 'contracts/RUN_CONTRACT_2F.json').write_text(json.dumps(c), encoding='utf-8')
    (root / 'contracts/FROZEN_CODE_2F.json').write_text(json.dumps({'r2f_engine.py': sha(root / 'code/r2f_engine.py')}), encoding='utf-8')
    fake = root / 'fakeengine.py'
    fake.write_text('#!' + sys.executable + '\nimport os, time\n'
                    'time.sleep(float(os.environ.get("FAKE_SLEEP", "1")))\n'
                    'open("model.out", "w").write("THE MODEL ESTIMATION TERMINATED NORMALLY\\n")\n', encoding='utf-8')
    fake.chmod(0o755)
    return root


def job(root, ident, category='SMOKE', cap=20):
    dest = root / 'models' / ident
    dest.mkdir(parents=True)
    (dest / 'model.inp').write_text('TITLE: mock\n', encoding='utf-8')
    (dest / 'data.dat').write_text('1 2 3\n', encoding='utf-8')
    j = {'id': ident, 'category': category, 'cap_seconds': cap, 'root': str(root), 'dest': str(dest),
         'input_sha256': sha(dest / 'model.inp'), 'data_sha256': sha(dest / 'data.dat'), 'mplus': str(root / 'fakeengine.py')}
    (dest / 'input_contract.json').write_text(json.dumps(j), encoding='utf-8')
    return dest


def run(dest, env=None):
    e = dict(os.environ); e.update(env or {})
    t = time.time()
    p = subprocess.run([sys.executable, str(code / 'r2f_engine.py'), str(dest / 'input_contract.json')], env=e, capture_output=True, text=True)
    rec = dest / 'engine_receipt.json'
    return p, (json.loads(rec.read_text(encoding='utf-8')) if rec.exists() else None), time.time() - t


def check(name, ok, detail=''):
    results.append({'test': name, 'result': 'PASS' if ok else 'FAIL', 'detail': str(detail)[:300]})


# 1 正常结束
r = make_root('t1'); d = job(r, 'A'); p, rec, el = run(d, {'FAKE_SLEEP': '1'})
st = json.loads((r / 'runtime/budget_status.json').read_text())
check('normal_exit', rec and rec['status'] == 'EXITED' and rec['gap_seconds'] == 0 and rec['keep_awake'] == 'NOT_WINDOWS' and rec['test_hook'] is None, rec)
check('budget_status_written', st['calls'] == 1 and abs(st['engine_seconds'] - rec['seconds']) < 1e-9, st['calls'])
# 2 幂等：已有回执不再记账
p2, rec2, _ = run(d); st2 = json.loads((r / 'runtime/budget_status.json').read_text())
check('idempotent_receipt', rec2 == rec and st2['calls'] == 1)
# 3 按有效秒超时
d = job(r, 'B', cap=3); p, rec, el = run(d, {'FAKE_SLEEP': '30'})
check('timeout_active_cap', rec['status'] == 'TIMEOUT' and 2.5 < rec['seconds'] < 6 and el < 20, (rec['status'], rec['seconds'], el))
# 4 挂起间隙：墙钟前跳 100 秒，被登记并从有效秒中扣除
d = job(r, 'C', cap=10); p, rec, el = run(d, {'FAKE_SLEEP': '3', 'R2F_ENGINE_TEST_CLOCK_JUMP': '1.5:100'})
check('gap_recorded_and_excluded', rec['status'] == 'EXITED' and 99.5 < rec['gap_seconds'] < 100.5 and rec['seconds'] < 6 and rec['wall_seconds'] > 100
      and rec['suspend_affected'] and rec['test_hook'] == '1.5:100', (rec['seconds'], rec['gap_seconds'], rec['wall_seconds']))
# 5 有间隙时仍按有效秒执行时限（不因跳钟立即误杀）
d = job(r, 'D', cap=4); p, rec, el = run(d, {'FAKE_SLEEP': '30', 'R2F_ENGINE_TEST_CLOCK_JUMP': '1:100'})
check('gap_does_not_trigger_timeout', rec['status'] == 'TIMEOUT' and 3.5 < rec['seconds'] < 7 and el > 3.5, (rec['seconds'], el))
# 6 类别上限
r = make_root('t6', categories={'SMOKE': 1, 'NUMERIC': 5, 'TARGET': 18, 'DIAG': 8, 'REPAIR': 3})
run(job(r, 'A'), {'FAKE_SLEEP': '0.2'}); p, rec, _ = run(job(r, 'B'), {'FAKE_SLEEP': '0.2'})
check('category_cap', rec is None and 'CALL_CAP' in p.stderr, p.stderr[-200:])
# 7 引擎预算
r = make_root('t7', engine=8)
run(job(r, 'A'), {'FAKE_SLEEP': '3.5'}); p, rec, _ = run(job(r, 'B'), {'FAKE_SLEEP': '0.2'})
check('engine_budget', rec is None and 'BUDGET_EXHAUSTED' in p.stderr, p.stderr[-200:])
# 8 冻结代码被改
r = make_root('t8'); (r / 'code/r2f_engine.py').write_text((r / 'code/r2f_engine.py').read_text() + '\n# changed\n')
p, rec, _ = run(job(r, 'A'))
check('frozen_code_changed', rec is None and 'Frozen code changed' in p.stderr, p.stderr[-200:])
# 9 输入哈希不符
r = make_root('t9'); d = job(r, 'A'); (d / 'model.inp').write_text('TITLE: altered\n')
p, rec, _ = run(d)
check('input_hash_mismatch', rec is None and 'AssertionError' in p.stderr, p.stderr[-200:])
# 10 保持唤醒脚本：非 Windows 下记录 NOT_WINDOWS，停止标志生效
r = make_root('t10'); shutil.copy(code / 'r2f_keep_awake.py', r / 'code')
ka = subprocess.Popen([sys.executable, str(code / 'r2f_keep_awake.py'), str(r)], stdout=subprocess.PIPE, text=True)
time.sleep(2); (r / 'runtime/KEEP_AWAKE_STOP').write_text('stop'); out, _ = ka.communicate(timeout=20)
k = json.loads((r / 'runtime/keep_awake_2f.json').read_text())
check('keep_awake_stop_flag', ka.returncode == 0 and k['end_reason'] == 'stop_flag' and k['state'] == 'NOT_WINDOWS', out.strip())

(work / 'engine_mock_results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
for x in results:
    print(f"{x['test']:36s} {x['result']}")
print('ENGINE_MOCK', 'PASSED' if all(x['result'] == 'PASS' for x in results) else 'FAILED', len(results))
