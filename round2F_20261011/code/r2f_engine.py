"""Round2F 单槽监督器：以 Round2E run_engine.py 为底，只改三处。
1) 调用上限、类别上限、引擎与墙钟预算全部读 contracts/RUN_CONTRACT_2F.json，不再写死。
2) 估计期间调用 SetThreadExecutionState 保持系统唤醒（仅 Windows），退出时恢复。
3) 轮询间隙仅作诊断；单次时限与总预算均按完整墙钟计费，绝不把监督器延迟直接当作待机扣减。不终止本调用以外的进程。
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import psutil

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def utc(epoch=None):
    return dt.datetime.fromtimestamp(time.time() if epoch is None else epoch, dt.timezone.utc).isoformat()


class Clock:
    """墙钟；测试钩子 R2F_ENGINE_TEST_CLOCK_JUMP='after:jump' 在启动 after 秒后一次性前跳 jump 秒，
    只用于云端/本机演练挂起检测。钩子生效会写入回执，CFPS 回执带钩子一律被 R 端拒收。"""
    def __init__(self):
        self.hook = os.environ.get('R2F_ENGINE_TEST_CLOCK_JUMP')
        self.t0 = time.time(); self.offset = 0.0
        if self.hook:
            a, b = self.hook.split(':'); self.after, self.jump = float(a), float(b)

    def now(self):
        t = time.time()
        if self.hook and not self.offset and t - self.t0 >= self.after:
            self.offset = self.jump
        return t + self.offset


class KeepAwake:
    """估计期间阻止系统因闲置进入睡眠；不能阻止用户主动休眠或合盖。"""
    def __init__(self):
        self.state = 'NOT_WINDOWS'

    def __enter__(self):
        if os.name == 'nt':
            import ctypes
            prev = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            self.state = 'ON' if prev else 'FAILED'
        return self

    def __exit__(self, *exc):
        if os.name == 'nt' and self.state == 'ON':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.state = 'RELEASED'
        return False


def contract(root):
    c = json.loads((root / 'contracts/RUN_CONTRACT_2F.json').read_text(encoding='utf-8'))
    b = c['budget']
    return b['categories'], int(b['max_calls']), float(b['engine_seconds']), float(b['wall_seconds']), \
        float(b['suspend_gap_seconds']), float(b['resource_wait_seconds'])


def database(root):
    db = sqlite3.connect(root / 'runtime/budget_2f.sqlite', timeout=20)
    db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, category TEXT, state TEXT, seconds REAL, '
               'wall REAL, gaps REAL, reserved REAL, pid INTEGER, create_time REAL, start REAL, finish REAL, dest TEXT)')
    db.commit()
    return db


def verify_frozen(root):
    manifest = root / 'contracts/FROZEN_CODE_2F.json'
    if not manifest.exists():
        raise RuntimeError('FROZEN_CODE_2F.json missing; run setup first')
    cf = root / 'contracts/FROZEN_CONTRACT_SHA256.txt'
    if not cf.exists() or sha(root / 'contracts/RUN_CONTRACT_2F.json') != cf.read_text().strip():
        raise RuntimeError('Frozen execution contract changed')
    for name, digest in json.loads(manifest.read_text(encoding='utf-8')).items():
        if sha(root / 'code' / name) != digest:
            raise RuntimeError('Frozen code changed: ' + name)


def usage(db):
    rows = db.execute('SELECT id,state,seconds FROM calls').fetchall()
    unknown = [r[0] for r in rows if r[2] is None]
    if unknown:
        raise RuntimeError('Unknown or still-running duration; no new admission: ' + ','.join(unknown))
    return sum(r[2] for r in rows)


def recover(db):
    for ident, dest in db.execute('SELECT id,dest FROM calls WHERE seconds IS NULL').fetchall():
        f = Path(dest) / 'engine_receipt.json'
        if f.exists():
            r = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(r.get('seconds'), (int, float)):
                db.execute('UPDATE calls SET state=?,seconds=?,wall=?,gaps=?,finish=? WHERE id=?',
                           (r['status'], r['seconds'], r.get('wall_seconds'), r.get('gap_seconds'), r['finished_epoch'], ident))
    db.commit()


def write_status(root, db, batch_start, clock):
    rows = db.execute('SELECT id,category,state,seconds,wall,gaps,reserved,start,finish FROM calls ORDER BY start').fetchall()
    keys = ['id', 'category', 'state', 'seconds', 'wall', 'gaps', 'reserved', 'start', 'finish']
    write_json(root / 'runtime/budget_status.json', {'calls': len(rows), 'engine_seconds': usage(db),
               'wall_seconds': clock.now() - batch_start, 'updated_utc': utc(), 'rows': [dict(zip(keys, r)) for r in rows]})


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    root, dest = Path(job['root']), Path(job['dest'])
    receipt = dest / 'engine_receipt.json'
    if receipt.exists():
        return
    caps, max_calls, engine_cap, wall_cap, gap_threshold, wait_cap = contract(root)
    verify_frozen(root)
    assert sha(dest / 'model.inp') == job['input_sha256']
    assert sha(dest / 'data.dat') == job['data_sha256']
    clock = Clock()
    db = database(root)
    recover(db)
    bw = json.loads((root / 'runtime/batch_window.json').read_text())
    db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('batch_start', bw['start_epoch']))
    db.commit()
    batch_start = db.execute("SELECT value FROM meta WHERE key='batch_start'").fetchone()[0]
    gaps = []
    with KeepAwake() as awake:
        resource_wait_start = prev = clock.now()
        while True:
            engine_left = engine_cap - usage(db)
            wall_left = wall_cap - (clock.now() - batch_start)
            if min(engine_left, wall_left) <= 5:
                raise RuntimeError('BUDGET_EXHAUSTED before launch')
            other = [p.info for p in psutil.process_iter(['pid', 'name', 'create_time'])
                     if 'mplus' in (p.info['name'] or '').lower()]
            available = psutil.virtual_memory().available / 2**30
            cpu = psutil.cpu_percent(interval=0.5)
            paused = (root / 'runtime/PAUSE').exists()
            snapshot = {'utc': utc(), 'available_gib': available, 'cpu_percent': cpu, 'other_mplus': other,
                        'paused': paused, 'keep_awake': awake.state}
            write_json(dest / 'resource_before.json', snapshot)
            if not other and not paused and available >= .5 and cpu < 85:
                break
            write_json(dest / 'engine_progress.json', {'stage': 'resource_wait', 'utc': utc(),
                       'message': f'waiting {clock.now()-resource_wait_start:.0f}s; available={available:.2f}GiB; other_mplus={len(other)}'})
            if clock.now() - resource_wait_start > wait_cap:
                raise RuntimeError('RESOURCE_WAIT_LIMIT; no Mplus launched')
            time.sleep(min(10, max(1, wall_left)))
        db.execute('BEGIN IMMEDIATE')
        try:
            used = usage(db)
            total = db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
            category = db.execute('SELECT COUNT(*) FROM calls WHERE category=?', (job['category'],)).fetchone()[0]
            if job['category'] not in caps or total >= max_calls or category >= caps[job['category']]:
                raise RuntimeError('CALL_CAP before launch')
            limit = min(job['cap_seconds'], engine_cap - used - 2, wall_cap - (clock.now() - batch_start) - 2)
            if limit <= 0:
                raise RuntimeError('BUDGET_EXHAUSTED before launch')
            db.execute('INSERT INTO calls (id,category,state,seconds,reserved,dest) VALUES (?,?,?,?,?,?)',
                       (job['id'], job['category'], 'CLAIMED', None, limit, str(dest)))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        if clock.hook:
            clock.t0, clock.offset = time.time(), 0.0  # 测试间隙从真实子进程准入后计时
        start = prev = clock.now()
        status, exitcode, proc, cpu_seconds, max_rss = 'START_FAILED', None, None, 0.0, 0
        try:
            with (dest / 'mplus_console.log').open('wb') as log:
                proc = subprocess.Popen([job['mplus'], 'model.inp'], cwd=dest, stdout=log, stderr=subprocess.STDOUT)
                ps = psutil.Process(proc.pid)
                born = ps.create_time()
                db.execute('UPDATE calls SET pid=?,create_time=?,start=?,state=? WHERE id=?', (proc.pid, born, start, 'RUNNING', job['id']))
                db.commit()
                write_json(dest / 'process.json', {'pid': proc.pid, 'create_time': born, 'exe': job['mplus'], 'cwd': str(dest),
                           'input_sha256': job['input_sha256'], 'started_epoch': start, 'limit_seconds': limit, 'keep_awake': awake.state})
                last, slept = 0, 0.0
                while proc.poll() is None:
                    now = clock.now()
                    if now - prev > gap_threshold:
                        # 仅记录轮询延迟，不判断为睡眠，不扣预算。
                        gaps.append({'from_utc': utc(prev), 'to_utc': utc(now), 'seconds': max(0.0, now - prev - slept)})
                        write_json(dest / 'suspend_gaps.json', gaps)
                    prev = now
                    active = now - start
                    try:
                        cpu_seconds = sum(ps.cpu_times()[:2])
                        max_rss = max(max_rss, ps.memory_info().rss)
                    except psutil.Error:
                        pass
                    if active - last >= 10:
                        write_json(dest / 'engine_progress.json', {'stage': 'estimating', 'utc': utc(), 'seconds': active,
                                   'message': f'{active:.0f}/{limit:.0f}s active; CPU={cpu_seconds:.1f}s; gaps={len(gaps)}'})
                        last = active
                    if active >= limit or now - batch_start >= wall_cap:
                        if ps.is_running() and abs(ps.create_time() - born) < .001:
                            for child in ps.children(recursive=True):
                                child.kill()
                            ps.kill()
                        proc.wait(timeout=20)
                        status, exitcode = 'TIMEOUT', 124
                        break
                    slept = min(1, max(.05, limit - active))
                    time.sleep(slept)
                else:
                    exitcode = proc.returncode
                    status = 'EXITED'
        except BaseException as exc:
            status = 'ENGINE_ERROR'
            write_json(dest / 'engine_error.json', {'error': repr(exc), 'utc': utc()})
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=20)
        finally:
            finish = clock.now()
            gap_seconds = sum(g['seconds'] for g in gaps)
            seconds = finish - start
            result = {'id': job['id'], 'round': 'Round2F', 'status': status, 'seconds': seconds, 'wall_seconds': finish - start,
                      'gap_seconds': gap_seconds, 'suspend_gaps': gaps, 'suspend_affected': None, 'polling_gap_affected': bool(gaps), 'accounting': 'gross engine wall; no suspension deduction',
                      'cpu_seconds': cpu_seconds, 'max_rss': max_rss, 'limit_seconds': limit, 'exitcode': exitcode,
                      'keep_awake': awake.state, 'test_hook': clock.hook, 'started_epoch': start,
                      'finished_epoch': finish, 'finished_utc': utc(finish)}
            write_json(receipt, result)
            db.execute('UPDATE calls SET state=?,seconds=?,wall=?,gaps=?,start=?,finish=? WHERE id=?',
                       (status, seconds, finish - start, gap_seconds, start, finish, job['id']))
            db.commit()
            write_status(root, db, batch_start, clock)
            print(json.dumps({k: result[k] for k in ('id', 'status', 'seconds', 'gap_seconds', 'keep_awake')}))
    write_json(dest / 'keep_awake_release.json', {'state': awake.state, 'utc': utc()})


if __name__ == '__main__':
    main()
